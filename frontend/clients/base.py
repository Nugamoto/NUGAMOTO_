"""Base HTTP client for NUGAMOTO frontend."""

from __future__ import annotations

import json
from typing import Any

import requests


class APIException(Exception):
    """Generic API exception wrapping HTTP errors."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class BaseClient:
    """Base HTTP client with optional JWT bearer handling and auto-refresh.

    Usage:
        client.set_tokens(access_token, refresh_token)
        client.clear_tokens()
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        # Lazy import to avoid hard dependency loop
        self._auth_client = None

    # ------------------------- token management ------------------------- #
    def set_tokens(self, access_token: str, refresh_token: str | None = None) -> None:
        """Set access/refresh tokens for authenticated requests."""
        self._access_token = access_token
        if refresh_token is not None:
            self._refresh_token = refresh_token

    def clear_tokens(self) -> None:
        """Clear stored tokens."""
        self._access_token = None
        self._refresh_token = None

    # ------------------------- core http methods ------------------------ #
    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        if extra:
            headers.update(extra)
        return headers


    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)


    def post(self, path: str, json_data: dict[str, Any] | None = None, data: Any = None,
             params: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, json_data=json_data, data=data, params=params)


    def patch(self, path: str, json_data: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
        return self._request("PATCH", path, json_data=json_data, params=params)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def _request(
            self,
            method: str,
            path: str,
            *,
            params: dict[str, Any] | None = None,
            json_data: dict[str, Any] | None = None,
            data: Any = None,
            retry_on_401: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        resp = requests.request(
            method=method,
            url=url,
            headers=self._headers(),
            params=params,
            json=json_data,
            data=data,
            timeout=30,
        )

        if resp.status_code == 401 and retry_on_401 and self._refresh_token:
            # Try refresh once
            if self._auth_client is None:
                from .auth_client import AuthClient  # local import to avoid circular
                self._auth_client = AuthClient(base_url=self.base_url)

            try:
                tokens = self._auth_client.refresh(self._refresh_token)
                new_access = tokens.get("access_token")
                new_refresh = tokens.get("refresh_token")
                if new_access:
                    self.set_tokens(new_access, new_refresh)
                    # Retry original request once without another refresh attempt
                    return self._request(
                        method, path, params=params, json_data=json_data, data=data, retry_on_401=False
                    )
            except Exception:
                # Fall through and raise original 401 as APIException
                pass

        if 200 <= resp.status_code < 300:
            if resp.content:
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    return resp.text
            return None

        # Map error to APIException
        try:
            payload = resp.json()
            message = payload.get("detail") or resp.text
        except Exception:
            message = resp.text

        raise APIException(resp.status_code, message)