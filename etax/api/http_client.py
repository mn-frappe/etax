# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
eTax API - HTTP Client Module

Handles all HTTP communication with eTax API.
Includes NE-KEY header support required by all eTax endpoints.
"""

import frappe
import requests
import json
from typing import Optional


class ETaxHTTPError(Exception):
	"""HTTP error for eTax API"""
	
	def __init__(self, message, status_code=None, response_data=None):
		super().__init__(message)
		self.status_code = status_code
		self.response_data = response_data


class ETaxHTTPClient:
	"""
	HTTP client for eTax API with NE-KEY support.
	
	Key features:
	- NE-KEY header automatically added to all requests
	- Authorization header management
	- Error handling and logging
	- Debug mode support
	
	eTax API Response codes:
	- 200: Success
	- 201: Please retry
	- 400: Invalid parameters
	- 500: Internal server error
	"""
	
	def __init__(self, settings=None):
		"""
		Initialize HTTP client.
		
		Args:
			settings: eTax Settings doc or None
		"""
		self.settings = settings or self._get_settings()
	
	def _get_settings(self):
		"""Get eTax Settings singleton"""
		try:
			return frappe.get_single("eTax Settings")
		except Exception:
			return None
	
	@property
	def base_url(self):
		"""Get API base URL"""
		if self.settings:
			return self.settings.api_base_url or "https://st-etax.mta.mn/api/beta"
		return "https://st-etax.mta.mn/api/beta"
	
	@property
	def timeout(self):
		"""Get request timeout"""
		if self.settings:
			return self.settings.timeout or 30
		return 30
	
	@property
	def debug_mode(self):
		"""Check if debug mode is enabled"""
		return self.settings and self.settings.debug_mode
	
	def _get_ne_key(self):
		"""Get NE-KEY from settings"""
		if self.settings:
			return self.settings.get_password("ne_key")
		return None
	
	def _build_url(self, endpoint):
		"""Build full URL from endpoint"""
		if endpoint.startswith("http"):
			return endpoint
		
		# Handle different endpoint formats
		if endpoint.startswith("/"):
			# If endpoint includes /api/beta, use it as-is with base domain
			if "/api/" in endpoint:
				base_domain = self.base_url.rsplit("/api", 1)[0]
				return f"{base_domain}{endpoint}"
			return f"{self.base_url}{endpoint}"
		
		return f"{self.base_url}/{endpoint}"
	
	def _get_headers(self, auth_header=None, extra_headers=None, content_type="application/json"):
		"""
		Build request headers.
		
		Args:
			auth_header: Authorization header dict
			extra_headers: Additional headers
			content_type: Content-Type header value
			
		Returns:
			dict: Complete headers
		"""
		headers = {
			"Content-Type": content_type,
			"Accept": "application/json"
		}
		
		# Add NE-KEY (required for all eTax API calls)
		ne_key = self._get_ne_key()
		if ne_key:
			headers["NE-KEY"] = ne_key
		
		# Add authorization
		if auth_header:
			headers.update(auth_header)
		
		# Add extra headers
		if extra_headers:
			headers.update(extra_headers)
		
		return headers
	
	def _log_request(self, method, url, headers, data=None, params=None):
		"""Log request details in debug mode"""
		if not self.debug_mode:
			return
		
		# Sanitize headers (remove sensitive data)
		safe_headers = {k: v for k, v in headers.items() if k.lower() not in ("authorization", "ne-key")}
		safe_headers["Authorization"] = "Bearer ***" if "Authorization" in headers else None
		safe_headers["NE-KEY"] = "***" if "NE-KEY" in headers else None
		
		log_msg = f"""
eTax API Request:
- Method: {method}
- URL: {url}
- Headers: {json.dumps(safe_headers, indent=2)}
- Params: {json.dumps(params, indent=2) if params else None}
- Body: {json.dumps(data, indent=2, ensure_ascii=False)[:1000] if data else None}
"""
		frappe.log_error(log_msg, "eTax HTTP Debug - Request")
	
	def _log_response(self, response, duration=None):
		"""Log response details in debug mode"""
		if not self.debug_mode:
			return
		
		try:
			response_body = response.json()
			response_str = json.dumps(response_body, indent=2, ensure_ascii=False)[:2000]
		except Exception:
			response_str = response.text[:2000]
		
		log_msg = f"""
eTax API Response:
- Status: {response.status_code}
- Duration: {duration}s
- Body: {response_str}
"""
		frappe.log_error(log_msg, "eTax HTTP Debug - Response")
	
	def _handle_response(self, response):
		"""
		Handle API response.
		
		Args:
			response: requests.Response object
			
		Returns:
			dict: Response data
			
		Raises:
			ETaxHTTPError: On error response
		"""
		try:
			data = response.json()
		except json.JSONDecodeError:
			if response.status_code >= 400:
				raise ETaxHTTPError(
					f"HTTP {response.status_code}: {response.text[:200]}",
					status_code=response.status_code
				)
			return {"raw_response": response.text}
		
		# Check for eTax API error codes
		code = data.get("code")
		if code is not None and code != 0:
			message = data.get("message", f"Error code: {code}")
			raise ETaxHTTPError(message, status_code=code, response_data=data)
		
		# Check HTTP status
		if response.status_code >= 400:
			message = data.get("error_description", 
				data.get("error", 
				data.get("message", f"HTTP {response.status_code}")))
			raise ETaxHTTPError(message, status_code=response.status_code, response_data=data)
		
		return data
	
	def get(self, endpoint, auth_header=None, headers=None, params=None):
		"""
		Make GET request to eTax API.
		
		Args:
			endpoint: API endpoint path
			auth_header: Authorization header
			headers: Additional headers
			params: Query parameters
			
		Returns:
			dict: Response data
		"""
		import time
		
		url = self._build_url(endpoint)
		request_headers = self._get_headers(auth_header, headers)
		
		self._log_request("GET", url, request_headers, params=params)
		
		start_time = time.time()
		try:
			response = requests.get(
				url,
				headers=request_headers,
				params=params,
				timeout=self.timeout
			)
		except requests.exceptions.Timeout:
			raise ETaxHTTPError(f"Request timeout after {self.timeout}s", status_code=408)
		except requests.exceptions.ConnectionError as e:
			raise ETaxHTTPError(f"Connection error: {str(e)}", status_code=503)
		finally:
			duration = round(time.time() - start_time, 2)
		
		self._log_response(response, duration)
		
		return self._handle_response(response)
	
	def post(self, endpoint, data=None, auth_header=None, headers=None, params=None):
		"""
		Make POST request to eTax API.
		
		Args:
			endpoint: API endpoint path
			data: Request body (dict)
			auth_header: Authorization header
			headers: Additional headers
			params: Query parameters
			
		Returns:
			dict: Response data
		"""
		import time
		
		url = self._build_url(endpoint)
		request_headers = self._get_headers(auth_header, headers)
		
		self._log_request("POST", url, request_headers, data=data, params=params)
		
		start_time = time.time()
		try:
			response = requests.post(
				url,
				json=data,
				headers=request_headers,
				params=params,
				timeout=self.timeout
			)
		except requests.exceptions.Timeout:
			raise ETaxHTTPError(f"Request timeout after {self.timeout}s", status_code=408)
		except requests.exceptions.ConnectionError as e:
			raise ETaxHTTPError(f"Connection error: {str(e)}", status_code=503)
		finally:
			duration = round(time.time() - start_time, 2)
		
		self._log_response(response, duration)
		
		return self._handle_response(response)


def get_http_client():
	"""Get eTax HTTP client instance"""
	return ETaxHTTPClient()
