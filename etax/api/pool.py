# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false

"""
eTax Connection Pool

HTTP connection pooling for improved API performance.
Reuses TCP connections to reduce latency.

Features:
- Connection pooling with requests.Session
- Automatic retry with exponential backoff
- Connection timeout management
- Keep-alive support
"""

import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Global session pool
_session_pool = threading.local()


def get_session(
    pool_connections: int = 10,
    pool_maxsize: int = 20,
    max_retries: int = 3,
    backoff_factor: float = 0.3
) -> requests.Session:
    """
    Get or create a pooled HTTP session.

    Uses thread-local storage for thread safety.

    Args:
        pool_connections: Number of connection pools
        pool_maxsize: Max connections per pool
        max_retries: Max retry attempts
        backoff_factor: Retry backoff factor

    Returns:
        requests.Session: Pooled session
    """
    if not hasattr(_session_pool, 'session') or _session_pool.session is None:
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"],
            raise_on_status=False
        )

        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )

        # Mount for both HTTP and HTTPS
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set default headers
        session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        })

        _session_pool.session = session

    return _session_pool.session


def close_session():
    """Close the current thread's session"""
    if hasattr(_session_pool, 'session') and _session_pool.session:
        _session_pool.session.close()
        _session_pool.session = None


class PooledHTTPClient:
    """
    HTTP client with connection pooling.

    Usage:
        client = PooledHTTPClient()
        response = client.get("https://api.example.com/data")
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._session: requests.Session | None = None

    @property
    def session(self) -> requests.Session:
        """Get pooled session"""
        if self._session is None:
            self._session = get_session()
        return self._session

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET request with pooled connection"""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.get(url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """POST request with pooled connection"""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.post(url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT request with pooled connection"""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.put(url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE request with pooled connection"""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.delete(url, **kwargs)

    def close(self):
        """Close session"""
        if self._session:
            self._session.close()
            self._session = None


# Utility for one-off requests with pooling
def pooled_request(method: str, url: str, **kwargs) -> requests.Response:
    """
    Make a pooled HTTP request.

    Args:
        method: HTTP method (get, post, etc.)
        url: Request URL
        **kwargs: Additional request arguments

    Returns:
        requests.Response
    """
    session = get_session()
    return getattr(session, method.lower())(url, **kwargs)
