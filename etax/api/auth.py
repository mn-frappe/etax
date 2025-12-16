# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

"""
eTax API - Authentication Module

Handles ITC OAuth2 authentication for eTax API.
Same auth server as eBalance (auth.itc.gov.mn)

OAuth2 Configuration:
- Staging: st.auth.itc.gov.mn/auth/realms/Staging
- Production: auth.itc.gov.mn/auth/realms/ITC
- client_id: etax-gui (production), etax-gui-test (staging)
- grant_type: password
"""

import frappe
import requests
from datetime import datetime, timedelta


class ETaxAuthError(Exception):
	"""Authentication error for eTax API"""
	pass


class ETaxAuth:
	"""
	ITC OAuth2 Authentication handler for eTax.
	
	Uses api.frappe.mn gateway for improved reliability:
	- Production: https://api.frappe.mn/auth/itc
	- Staging: https://api.frappe.mn/auth/itc-staging
	
	Direct auth servers (fallback):
	- Staging: https://st.auth.itc.gov.mn/auth/realms/Staging
	- Production: https://auth.itc.gov.mn/auth/realms/ITC
	"""
	
	# Primary: api.frappe.mn gateway (recommended)
	GATEWAY_URL = "https://api.frappe.mn"
	GATEWAY_PATHS = {
		"Staging": "/auth/itc-staging",
		"Production": "/auth/itc"
	}
	
	# Fallback: Direct auth servers
	AUTH_URLS = {
		"Staging": "https://st.auth.itc.gov.mn/auth/realms/Staging",
		"Production": "https://auth.itc.gov.mn/auth/realms/ITC"
	}
	
	# OAuth2 client IDs per environment
	CLIENT_IDS = {
		"Staging": "etax-gui-test",
		"Production": "etax-gui"
	}
	
	# Fixed OAuth2 parameters
	GRANT_TYPE = "password"
	
	def __init__(self, settings=None):
		"""
		Initialize auth handler.
		
		Args:
			settings: eTax Settings doc or None to fetch automatically
		"""
		self.settings = settings or self._get_settings()
		self._token = None
		self._token_expiry = None
	
	def _get_settings(self):
		"""Get eTax Settings singleton"""
		try:
			return frappe.get_single("eTax Settings")
		except Exception:
			frappe.throw(
				"eTax Settings not configured. Please configure in MN Settings > eTax.",
				title="eTax Configuration Required"
			)
	
	@property
	def environment(self):
		"""Get current environment"""
		return self.settings.environment or "Staging"
	
	@property
	def auth_url(self):
		"""Get auth URL - uses api.frappe.mn gateway"""
		gateway_path = self.GATEWAY_PATHS.get(self.environment, self.GATEWAY_PATHS["Staging"])
		return f"{self.GATEWAY_URL}{gateway_path}"
	
	@property
	def auth_url_direct(self):
		"""Get direct auth URL for fallback"""
		return self.AUTH_URLS.get(self.environment, self.AUTH_URLS["Staging"])
	
	@property
	def client_id(self):
		"""Get OAuth2 client ID for current environment"""
		return self.CLIENT_IDS.get(self.environment, self.CLIENT_IDS["Staging"])
	
	@property
	def token_endpoint(self):
		"""Get OAuth2 token endpoint"""
		return f"{self.auth_url}/protocol/openid-connect/token"
	
	def get_token(self, force_refresh=False):
		"""
		Get valid access token, refreshing if necessary.
		
		Args:
			force_refresh: Force token refresh even if cached
			
		Returns:
			str: Valid access token
			
		Raises:
			ETaxAuthError: If authentication fails
		"""
		# Check cached token
		if not force_refresh and self._is_token_valid():
			return self._token
		
		# Check stored token in settings
		if not force_refresh and self._load_stored_token():
			return self._token
		
		# Request new token
		return self._request_new_token()
	
	def _is_token_valid(self):
		"""Check if cached token is still valid"""
		if not self._token or not self._token_expiry:
			return False
		# Add 60 second buffer
		return datetime.now() < (self._token_expiry - timedelta(seconds=60))
	
	def _load_stored_token(self):
		"""Load token from settings if still valid"""
		try:
			stored_token = self.settings.get_password("access_token")
			stored_expiry = self.settings.token_expiry
			
			if stored_token and stored_expiry:
				expiry_dt = frappe.utils.get_datetime(stored_expiry)
				if datetime.now() < (expiry_dt - timedelta(seconds=60)):
					self._token = stored_token
					self._token_expiry = expiry_dt
					return True
		except Exception:
			pass
		return False
	
	def _request_new_token(self):
		"""
		Request new token from ITC OAuth2 server.
		
		SECURITY: Password is decrypted only for this request,
		never logged or stored in plain text.
		"""
		# Initialize variables outside try block to avoid unbound errors
		data = None
		headers = None
		timeout = 30
		
		try:
			# Get credentials (password is decrypted here)
			username = self.settings.username
			password = self.settings.get_password("password")
			
			if not username or not password:
				raise ETaxAuthError("Username and password are required")
			
			# Build token request
			data = {
				"grant_type": self.GRANT_TYPE,
				"client_id": self.client_id,
				"username": username,
				"password": password
			}
			
			headers = {
				"Content-Type": "application/x-www-form-urlencoded"
			}
			
			timeout = self.settings.timeout or 30
			
			# Log request if debug mode (without password)
			if self.settings.debug_mode:
				frappe.log_error(
					f"eTax Auth Request: {self.token_endpoint} | client_id: {self.client_id}",
					"eTax Auth Debug"
				)
			
			# Make token request via gateway
			response = requests.post(
				self.token_endpoint,
				data=data,
				headers=headers,
				timeout=timeout
			)
			
			if response.status_code == 200:
				token_data = response.json()
				return self._process_token_response(token_data)
			
			# Gateway failed, try direct connection
			return self._request_token_direct(data, headers, timeout)
			
		except requests.exceptions.RequestException as e:
			# Try direct connection on network errors
			if hasattr(self, '_direct_attempted'):
				raise ETaxAuthError(f"Authentication failed: {str(e)}")
			self._direct_attempted = True
			return self._request_token_direct(data, headers, timeout)
		except Exception as e:
			raise ETaxAuthError(f"Authentication error: {str(e)}")
	
	def _request_token_direct(self, data, headers, timeout):
		"""Fallback: Request token directly from ITC server"""
		direct_url = f"{self.auth_url_direct}/protocol/openid-connect/token"
		
		try:
			response = requests.post(
				direct_url,
				data=data,
				headers=headers,
				timeout=timeout
			)
			
			if response.status_code == 200:
				token_data = response.json()
				return self._process_token_response(token_data)
			
			# Parse error response
			error_data = response.json() if response.content else {}
			error_msg = error_data.get("error_description", 
				error_data.get("error", f"HTTP {response.status_code}"))
			raise ETaxAuthError(f"Authentication failed: {error_msg}")
			
		except requests.exceptions.RequestException as e:
			raise ETaxAuthError(f"Direct authentication failed: {str(e)}")
	
	def _process_token_response(self, token_data):
		"""Process successful token response"""
		access_token = token_data.get("access_token")
		expires_in = token_data.get("expires_in", 300)  # Default 5 minutes
		
		if not access_token:
			raise ETaxAuthError("No access token in response")
		
		# Calculate expiry
		expiry_dt = datetime.now() + timedelta(seconds=expires_in)
		
		# Cache in memory
		self._token = access_token
		self._token_expiry = expiry_dt
		
		# Store in settings
		self._store_token(access_token, expiry_dt)
		
		return access_token
	
	def _store_token(self, token, expiry):
		"""Store token in settings (encrypted)"""
		try:
			frappe.db.set_single_value("eTax Settings", "access_token", token)
			frappe.db.set_single_value("eTax Settings", "token_expiry", expiry)
			frappe.db.commit()
		except Exception as e:
			# Log but don't fail - token is still cached in memory
			frappe.log_error(f"Failed to store eTax token: {str(e)}", "eTax")
	
	def get_auth_header(self, force_refresh=False):
		"""
		Get Authorization header for API requests.
		
		Args:
			force_refresh: Force token refresh
			
		Returns:
			dict: {"Authorization": "Bearer <token>"}
		"""
		token = self.get_token(force_refresh)
		return {"Authorization": f"Bearer {token}"}
	
	def clear_token(self):
		"""Clear cached and stored token"""
		self._token = None
		self._token_expiry = None
		
		try:
			frappe.db.set_single_value("eTax Settings", "access_token", "")
			frappe.db.set_single_value("eTax Settings", "token_expiry", None)
			frappe.db.commit()
		except Exception:
			pass


def get_auth():
	"""Get eTax Auth instance"""
	return ETaxAuth()
