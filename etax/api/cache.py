# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eTax Caching Layer

High-performance Redis caching for:
- API Tokens (until expiry)
- User Organizations (1 hour)
- Report Lists (5 minutes)
- Form Templates (24 hours - rarely changes)

Cache Strategy:
- Token: Until expiry minus 60 seconds buffer
- Static data (forms): Long TTL (24h)
- Dynamic data (reports): Short TTL (5 min)
"""

import hashlib
import json
from collections.abc import Callable
from functools import wraps

import frappe

# Cache key prefixes
CACHE_PREFIX = "etax"
CACHE_KEYS = {
	"token": f"{CACHE_PREFIX}:token",
	"orgs": f"{CACHE_PREFIX}:orgs",
	"reports": f"{CACHE_PREFIX}:reports",
	"forms": f"{CACHE_PREFIX}:forms",
	"form_detail": f"{CACHE_PREFIX}:form_detail",
	"settings": f"{CACHE_PREFIX}:settings",
}

# TTL in seconds
CACHE_TTL = {
	"token": 3600,        # 1 hour (actual expiry from token)
	"orgs": 3600,         # 1 hour
	"reports": 300,       # 5 minutes
	"forms": 86400,       # 24 hours
	"form_detail": 86400, # 24 hours
	"settings": 300,      # 5 minutes
}


def get_cache_key(*args, **kwargs) -> str:
	"""Generate cache key from arguments"""
	key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
	return hashlib.md5(key_data.encode()).hexdigest()[:16]


def cached(key_prefix: str, ttl: int | None = None):
	"""
	Decorator for caching function results.

	Usage:
		@cached("reports", ttl=300)
		def get_reports(ent_id):
			...
	"""
	def decorator(func: Callable):
		@wraps(func)
		def wrapper(*args, **kwargs):
			# Skip cache if explicitly requested
			skip_cache = kwargs.pop("skip_cache", False)
			if skip_cache:
				return func(*args, **kwargs)

			# Generate cache key
			cache_key = f"{CACHE_KEYS.get(key_prefix, key_prefix)}:{get_cache_key(*args, **kwargs)}"

			# Try to get from cache
			cached_value = frappe.cache.get_value(cache_key)
			if cached_value is not None:
				return json.loads(cached_value) if isinstance(cached_value, str) else cached_value

			# Execute function
			result = func(*args, **kwargs)

			# Cache result
			if result is not None:
				cache_ttl = ttl or CACHE_TTL.get(key_prefix, 300)
				frappe.cache.set_value(
					cache_key,
					json.dumps(result) if not isinstance(result, str) else result,
					expires_in_sec=cache_ttl
				)

			return result
		return wrapper
	return decorator


class ETaxCache:
	"""
	Centralized cache manager for eTax.

	Provides:
	- Token caching with expiry awareness
	- Bulk cache operations
	- Cache invalidation
	- Cache statistics
	"""

	@staticmethod
	def get_token() -> dict | None:
		"""Get cached token if not expired"""
		token_data = frappe.cache.get_value(CACHE_KEYS["token"])
		if token_data:
			data = json.loads(token_data) if isinstance(token_data, str) else token_data
			# Check if token is still valid (with 60s buffer)
			import time
			if data.get("expires_at", 0) > time.time() + 60:
				return data
		return None

	@staticmethod
	def set_token(token: str, expires_in: int, refresh_token: str | None = None):
		"""Cache token with calculated expiry"""
		import time
		token_data = {
			"access_token": token,
			"refresh_token": refresh_token,
			"expires_at": time.time() + expires_in,
			"expires_in": expires_in
		}
		frappe.cache.set_value(
			CACHE_KEYS["token"],
			json.dumps(token_data),
			expires_in_sec=expires_in
		)

	@staticmethod
	def get_settings() -> dict | None:
		"""Get cached settings"""
		cached = frappe.cache.get_value(CACHE_KEYS["settings"])
		if cached:
			return json.loads(cached) if isinstance(cached, str) else cached
		return None

	@staticmethod
	def set_settings(settings_dict: dict):
		"""Cache settings"""
		frappe.cache.set_value(
			CACHE_KEYS["settings"],
			json.dumps(settings_dict),
			expires_in_sec=CACHE_TTL["settings"]
		)

	@staticmethod
	def invalidate_token():
		"""Invalidate token cache"""
		frappe.cache.delete_value(CACHE_KEYS["token"])

	@staticmethod
	def invalidate_reports():
		"""Invalidate report cache"""
		# Delete all report-related cache keys
		frappe.cache.delete_keys(f"{CACHE_KEYS['reports']}:*")

	@staticmethod
	def invalidate_all():
		"""Invalidate all eTax cache"""
		for key in CACHE_KEYS.values():
			frappe.cache.delete_keys(f"{key}*")

	@staticmethod
	def get_stats() -> dict:
		"""Get cache statistics"""
		stats = {}
		for name, key in CACHE_KEYS.items():
			cached = frappe.cache.get_value(key)
			stats[name] = {
				"cached": cached is not None,
				"key": key
			}
		return stats


# Utility functions for direct cache access
def get_cached_orgs(user_key: str) -> list | None:
	"""Get cached organizations"""
	cache_key = f"{CACHE_KEYS['orgs']}:{user_key}"
	cached = frappe.cache.get_value(cache_key)
	if cached:
		return json.loads(cached) if isinstance(cached, str) else cached
	return None


def set_cached_orgs(user_key: str, orgs: list):
	"""Cache organizations"""
	cache_key = f"{CACHE_KEYS['orgs']}:{user_key}"
	frappe.cache.set_value(
		cache_key,
		json.dumps(orgs),
		expires_in_sec=CACHE_TTL["orgs"]
	)


def get_cached_form_detail(form_code: str) -> dict | None:
	"""Get cached form detail (long TTL)"""
	cache_key = f"{CACHE_KEYS['form_detail']}:{form_code}"
	cached = frappe.cache.get_value(cache_key)
	if cached:
		return json.loads(cached) if isinstance(cached, str) else cached
	return None


def set_cached_form_detail(form_code: str, detail: dict):
	"""Cache form detail (long TTL)"""
	cache_key = f"{CACHE_KEYS['form_detail']}:{form_code}"
	frappe.cache.set_value(
		cache_key,
		json.dumps(detail),
		expires_in_sec=CACHE_TTL["form_detail"]
	)


# Cache invalidation hooks
def on_settings_update(doc, method=None):
	"""Called when eTax Settings is updated"""
	ETaxCache.invalidate_token()
	frappe.cache.delete_value(CACHE_KEYS["settings"])


def on_report_sync(doc=None, method=None):
	"""Called after report sync"""
	ETaxCache.invalidate_reports()
