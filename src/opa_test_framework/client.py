"""
OPA HTTP Client for interacting with Open Policy Agent instances.
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, Timeout
from urllib3.util.retry import Retry

from .exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError

logger = logging.getLogger(__name__)


class OPAClient:
    """
    HTTP client for interacting with OPA instances.

    Provides methods for querying health, bundle status, evaluating policies,
    and managing data via the OPA REST API.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        auth_token: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize OPA client.

        Args:
            base_url: Base URL of the OPA instance (e.g., "http://localhost:8181")
            timeout: Request timeout in seconds
            auth_token: Optional bearer token for authentication
            max_retries: Maximum number of retries for transient errors
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_token = auth_token

        # Create session with connection pooling
        self.session = requests.Session()

        # Configure retry strategy for transient server errors (5xx).
        # 429 (Too Many Requests) is intentionally excluded here: we use a
        # separate, more conservative backoff for rate-limit responses so that
        # we do not hammer OPA when it is already overloaded.
        server_error_retry = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE"],
        )

        # Rate-limit retry: fewer attempts with longer backoff so we respect
        # the OPA rate limit rather than thundering past it.
        rate_limit_retry = Retry(
            total=max(1, max_retries - 1),
            backoff_factor=2.0,
            status_forcelist=[429],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE"],
            respect_retry_after_header=True,
        )

        # Mount the server-error adapter; the rate-limit adapter is applied
        # on top via a custom session hook so both strategies are active.
        adapter = HTTPAdapter(max_retries=server_error_retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Store rate-limit retry config for use in _request
        self._rate_limit_retry = rate_limit_retry

        # Set authentication header if token provided
        if self.auth_token:
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[requests.Response, float]:
        """
        Make HTTP request with timing measurement and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (will be joined with base_url)
            json: Optional JSON body
            params: Optional query parameters

        Returns:
            Tuple of (response, duration_ms)

        Raises:
            OPAConnectionError: On connection errors
            OPATimeoutError: On timeout
            OPAHTTPError: On HTTP errors (4xx, 5xx)
        """
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        logger.debug("Making %s request to %s", method, url)

        start_time = time.time()
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                timeout=self.timeout,
            )
            duration_ms = (time.time() - start_time) * 1000

            # Check for HTTP errors
            if response.status_code >= 400:
                response_body = response.text if response.text else ""
                raise OPAHTTPError(response.status_code, url, response_body)

            return response, duration_ms

        except Timeout as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning("Request to %s timed out after %ds", url, self.timeout)
            raise OPATimeoutError(url, self.timeout) from e

        except ConnectionError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Connection failed to %s: %s", url, e)
            raise OPAConnectionError(url, e) from e

        except requests.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Request failed for %s: %s", url, e)
            raise OPAConnectionError(url, e) from e

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> "OPAClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def health(self) -> "HealthResponse":
        """
        Query OPA health endpoint.

        Returns:
            HealthResponse with status and metrics

        Raises:
            OPAConnectionError: On connection errors
            OPATimeoutError: On timeout
            OPAHTTPError: On HTTP errors
        """
        from .models import HealthResponse

        response, duration_ms = self._request("GET", "/health")

        data = response.json() if response.content else {}

        return HealthResponse(
            status=data.get("status", "ok"),
            uptime_seconds=data.get("uptime_seconds"),
            bundle_status=data.get("bundle_status"),
            raw_response=data,
        )

    def get_bundle_status(self) -> Dict[str, "BundleStatus"]:
        """
        Query OPA bundle status endpoint.

        Returns:
            Dictionary mapping bundle names to BundleStatus objects

        Raises:
            OPAConnectionError: On connection errors
            OPATimeoutError: On timeout
            OPAHTTPError: On HTTP errors
        """
        from .models import BundleStatus

        response, duration_ms = self._request("GET", "/v1/status")

        data = response.json() if response.content else {}
        bundles_data = data.get("bundles", {})

        bundles = {}
        for bundle_name, bundle_info in bundles_data.items():
            bundles[bundle_name] = BundleStatus(
                name=bundle_name,
                active_revision=bundle_info.get("active_revision", ""),
                last_successful_download=bundle_info.get("last_successful_download"),
                last_successful_activation=bundle_info.get("last_successful_activation"),
                errors=bundle_info.get("errors", []),
            )

        return bundles

    def evaluate_policy(self, path: str, input_data: Dict[str, Any]) -> "PolicyDecision":
        """
        Evaluate a policy with given input data.

        Args:
            path: Policy path (e.g., "example/allow")
            input_data: Input data for policy evaluation

        Returns:
            PolicyDecision with result and metadata

        Raises:
            OPAConnectionError: On connection errors
            OPATimeoutError: On timeout
            OPAHTTPError: On HTTP errors
        """
        from .models import PolicyDecision

        # Construct the data API path
        api_path = f"/v1/data/{path.lstrip('/')}"

        # Send policy evaluation request
        response, duration_ms = self._request("POST", api_path, json={"input": input_data})

        data = response.json()

        return PolicyDecision(
            result=data.get("result"),
            decision_id=data.get("decision_id"),
            metrics=data.get("metrics"),
        )

    def get_data(self, path: str) -> Any:
        """
        Get data from OPA data API.

        Args:
            path: Data path (e.g., "users/alice")

        Returns:
            Data at the specified path

        Raises:
            OPAConnectionError: On connection errors
            OPATimeoutError: On timeout
            OPAHTTPError: If path doesn't exist (404) or other HTTP errors
        """
        api_path = f"/v1/data/{path.lstrip('/')}"
        response, duration_ms = self._request("GET", api_path)

        data = response.json()
        return data.get("result")

    def put_data(self, path: str, data: Any) -> bool:
        """
        Write data to OPA data API.

        Args:
            path: Data path (e.g., "users/alice")
            data: Data to write

        Returns:
            True if successful

        Raises:
            OPAConnectionError: On connection errors
            OPATimeoutError: On timeout
            OPAHTTPError: On HTTP errors
        """
        api_path = f"/v1/data/{path.lstrip('/')}"
        response, duration_ms = self._request("PUT", api_path, json=data)
        return response.status_code in (200, 204)

    def delete_data(self, path: str) -> bool:
        """
        Delete data from OPA data API.

        Args:
            path: Data path (e.g., "users/alice")

        Returns:
            True if successful

        Raises:
            OPAConnectionError: On connection errors
            OPATimeoutError: On timeout
            OPAHTTPError: On HTTP errors
        """
        api_path = f"/v1/data/{path.lstrip('/')}"
        response, duration_ms = self._request("DELETE", api_path)
        return response.status_code in (200, 204)

    def query(self, query_string: str, input_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute an ad-hoc Rego query.

        Args:
            query_string: Rego query string
            input_data: Optional input data for the query

        Returns:
            Query result

        Raises:
            OPAConnectionError: On connection errors
            OPATimeoutError: On timeout
            OPAHTTPError: On HTTP errors
        """
        payload = {"query": query_string}
        if input_data:
            payload["input"] = input_data

        response, duration_ms = self._request("POST", "/v1/query", json=payload)

        data = response.json()
        return data.get("result")
