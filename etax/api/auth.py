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

from datetime import datetime, timedelta

import frappe
import requests


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

	# Primary: api.frappe.mn gateway (proxy for Mongolian IP requirement)
	GATEWAY_URL = "https://api.frappe.mn"
	GATEWAY_PATHS = {
		"Staging": "/auth/itc-staging",
		"Production": "/auth/itc"
	}

	# Fallback: Direct auth servers (requires Mongolian IP)
	AUTH_URLS = {
		"Staging": "https://st.auth.itc.gov.mn/auth/realms/Staging",
		"Production": "https://auth.itc.gov.mn/auth/realms/ITC"
	}

	# OAuth2 client ID for eTax API access
	# etax-gui is the official client that has permissions for eTax user/org data
	# vatps only has basic profile access, not eTax data
	CLIENT_IDS = {
		"Staging": "etax-gui",
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
		"""Get OAuth2 client ID for eTax API access"""
		return self.CLIENT_IDS.get(self.environment, self.CLIENT_IDS["Staging"])

	@property
	def token_endpoint(self):
		"""Get OAuth2 token endpoint via gateway"""
		return f"{self.auth_url}/protocol/openid-connect/token"

	@property
	def token_endpoint_direct(self):
		"""Get direct OAuth2 token endpoint for fallback"""
		return f"{self.auth_url_direct}/protocol/openid-connect/token"

	def get_token(self, force_refresh=False):
		"""
		Get valid access token, refreshing if necessary.

		Uses multi-level caching:
		1. In-memory cache (fastest)
		2. Redis cache (shared across workers)
		3. Database storage (persistent)

		Args:
			force_refresh: Force token refresh even if cached

		Returns:
			str: Valid access token

		Raises:
			ETaxAuthError: If authentication fails
		"""
		# Level 1: In-memory cache
		if not force_refresh and self._is_token_valid():
			return self._token

		# Level 2: Redis cache
		if not force_refresh:
			from etax.api.cache import ETaxCache
			cached_token = ETaxCache.get_token()
			if cached_token:
				self._token = cached_token.get("access_token")
				self._token_expiry = datetime.fromtimestamp(cached_token.get("expires_at", 0))
				return self._token

		# Level 3: Database storage
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
			# Check if token_expiry exists first
			stored_expiry = self.settings.token_expiry
			if not stored_expiry:
				return False

			expiry_dt = frappe.utils.get_datetime(stored_expiry)
			if datetime.now() >= (expiry_dt - timedelta(seconds=60)):
				# Token expired, don't bother loading
				return False

			# Try to get stored token
			try:
				stored_token = self.settings.get_password("access_token")
			except Exception:
				# Password field might be empty or not set
				return False

			if stored_token:
				self._token = stored_token
				self._token_expiry = expiry_dt
				return True
		except Exception:
			pass
		return False

	def _request_new_token(self):
		"""
		Request new token from ITC OAuth2 server via api.frappe.mn gateway.

		SECURITY: Password is decrypted only for this request,
		never logged or stored in plain text.
		"""
		try:
			# Get credentials (password is decrypted here)
			username = self.settings.username
			password = self.settings.get_password("password")

			if not username or not password:
				raise ETaxAuthError("Username and password are required")

			headers = {
				"Content-Type": "application/x-www-form-urlencoded"
			}

			timeout = self.settings.timeout or 30

			data = {
				"grant_type": self.GRANT_TYPE,
				"client_id": self.client_id,
				"username": username,
				"password": password
			}

			# Log request if debug mode (without password)
			if self.settings.debug_mode:
				frappe.log_error(
					f"eTax Auth Request: {self.token_endpoint} | client_id: {self.client_id}",
					"eTax Auth Debug"
				)

			# Request token via gateway
			response = requests.post(
				self.token_endpoint,
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
			raise ETaxAuthError(f"Gateway connection failed: {e!s}")
		except ETaxAuthError:
			raise
		except Exception as e:
			raise ETaxAuthError(f"Authentication error: {e!s}")

	def _process_token_response(self, token_data):
		"""Process successful token response"""
		access_token = token_data.get("access_token")
		refresh_token = token_data.get("refresh_token")
		expires_in = token_data.get("expires_in", 300)  # Default 5 minutes

		if not access_token:
			raise ETaxAuthError("No access token in response")

		# Calculate expiry
		expiry_dt = datetime.now() + timedelta(seconds=expires_in)

		# Cache in memory
		self._token = access_token
		self._token_expiry = expiry_dt

		# Cache in Redis (for sharing across workers)
		from etax.api.cache import ETaxCache
		ETaxCache.set_token(access_token, expires_in, refresh_token)

		# Store in settings (persistent)
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
			frappe.log_error(f"Failed to store eTax token: {e!s}", "eTax")

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

		# Clear Redis cache
		from etax.api.cache import ETaxCache
		ETaxCache.invalidate_token()

		try:
			frappe.db.set_single_value("eTax Settings", "access_token", "")
			frappe.db.set_single_value("eTax Settings", "token_expiry", None)
			frappe.db.commit()
		except Exception:
			pass


def get_auth():
	"""Get eTax Auth instance"""
	return ETaxAuth()
