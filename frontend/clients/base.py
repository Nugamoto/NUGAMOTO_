# frontend/clients/base.py
import requests
from typing import Any
from abc import ABC
import logging

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Custom API exception."""


    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class BaseClient(ABC):
    """Base API client with common functionality."""


    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })


    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            if response.content:
                return response.json()
            return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
            raise APIException(
                f"API request failed: {e.response.status_code}",
                e.response.status_code
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise APIException(f"Connection error: {str(e)}")


    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make GET request."""
        return self._make_request('GET', endpoint, params=params)


    def post(self, endpoint: str, json_data: dict[str, Any]) -> Any:
        """Make POST request."""
        return self._make_request('POST', endpoint, json=json_data)


    def patch(self, endpoint: str, json_data: dict[str, Any]) -> Any:
        """Make PATCH request."""
        return self._make_request('PATCH', endpoint, json=json_data)


    def delete(self, endpoint: str) -> Any:
        """Make DELETE request."""
        return self._make_request('DELETE', endpoint)