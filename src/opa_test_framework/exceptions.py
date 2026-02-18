"""
Custom exceptions for OPA test framework.
"""


class OPATestError(Exception):
    """Base exception for OPA test framework errors."""

    pass


class OPAConnectionError(OPATestError):
    """Raised when unable to connect to OPA instance."""

    def __init__(self, url: str, original_error: Exception):
        self.url = url
        self.original_error = original_error
        super().__init__(f"Failed to connect to OPA at {url}: {original_error}")


class OPATimeoutError(OPATestError):
    """Raised when OPA request times out."""

    def __init__(self, url: str, timeout: int):
        self.url = url
        self.timeout = timeout
        super().__init__(f"Request to OPA at {url} timed out after {timeout} seconds")


class OPAHTTPError(OPATestError):
    """Raised when OPA returns an HTTP error."""

    def __init__(self, status_code: int, url: str, response_body: str):
        self.status_code = status_code
        self.url = url
        # Truncate and sanitize response body to avoid leaking sensitive data
        self.response_body = response_body[:200] if response_body else ""
        super().__init__(f"OPA returned HTTP {status_code} for {url}")


class OPAPolicyError(OPATestError):
    """Raised when policy evaluation fails."""

    def __init__(self, policy_path: str, error_message: str):
        self.policy_path = policy_path
        self.error_message = error_message
        super().__init__(f"Policy evaluation failed for {policy_path}: {error_message}")
