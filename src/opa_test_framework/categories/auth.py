"""
Authentication enforcement tests for OPA instances.

These tests validate that OPA is *requiring* authentication when it should be —
i.e. that unauthenticated requests are correctly rejected with HTTP 401.
They are intentionally kept separate from normal policy tests because they need
to make requests *without* the configured auth token.
"""

import time
from typing import List

import requests

from ..client import OPAClient
from ..config import TestConfig
from ..exceptions import OPAHTTPError
from ..models import TestResult, TestStatus
from .base import Test, TestCategory


class AuthRequiredTest(Test):
    """Verify that OPA rejects unauthenticated requests with HTTP 401.

    This test deliberately calls the OPA health endpoint *without* any
    Authorization header.  If auth is enabled, OPA must return 401.
    If OPA is not configured with authentication this test is skipped.
    """

    def __init__(self) -> None:
        super().__init__(
            name="auth_required",
            description="Verify OPA rejects unauthenticated requests with HTTP 401",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()

        # Skip the test when no auth token is configured — there is nothing
        # to enforce, so we can't make a meaningful assertion.
        if not config.auth_token:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.SKIP,
                duration_ms=duration_ms,
                message="Skipped: no auth_token configured, authentication enforcement not tested",
            )

        try:
            # Build a *bare* session with no auth header so we can probe
            # whether OPA actually enforces authentication.
            session = requests.Session()
            url = f"{client.base_url}/health"
            response = session.get(url, timeout=client.timeout)
            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 401:
                return self._create_result(
                    status=TestStatus.PASS,
                    duration_ms=duration_ms,
                    message="OPA correctly rejects unauthenticated requests (HTTP 401)",
                    details={"status_code": response.status_code},
                )
            else:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message=(
                        f"OPA did not reject unauthenticated request — "
                        f"expected HTTP 401, got {response.status_code}. "
                        f"Authentication may not be enforced."
                    ),
                    details={"status_code": response.status_code},
                )

        except requests.Timeout:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message="Request timed out while testing auth enforcement",
            )
        except requests.ConnectionError as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Connection error while testing auth enforcement: {str(e)}",
                details={"error": str(e)},
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Unexpected error: {str(e)}",
                details={"error": str(e)},
            )


class AuthTokenValidTest(Test):
    """Verify that the configured auth token is accepted by OPA.

    This is a companion to AuthRequiredTest.  After confirming that OPA
    rejects unauthenticated requests we also confirm that the *correct* token
    is accepted, ruling out misconfiguration on the framework side.
    """

    def __init__(self) -> None:
        super().__init__(
            name="auth_token_valid",
            description="Verify the configured auth token is accepted by OPA",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()

        if not config.auth_token:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.SKIP,
                duration_ms=duration_ms,
                message="Skipped: no auth_token configured",
            )

        try:
            # Use the normal authenticated client — health should succeed.
            health = client.health()
            duration_ms = (time.time() - start_time) * 1000

            return self._create_result(
                status=TestStatus.PASS,
                duration_ms=duration_ms,
                message="Configured auth token accepted by OPA",
                details={"health_status": health.status},
            )

        except OPAHTTPError as e:
            duration_ms = (time.time() - start_time) * 1000
            if e.status_code == 401:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message=(
                        "OPA rejected the configured auth token with HTTP 401 — "
                        "check that auth_token matches the OPA server configuration"
                    ),
                    details={"status_code": e.status_code},
                )
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Unexpected HTTP error: {str(e)}",
                details={"status_code": e.status_code},
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Unexpected error: {str(e)}",
                details={"error": str(e)},
            )


class AuthTests(TestCategory):
    """Category for authentication enforcement tests."""

    def __init__(self) -> None:
        super().__init__("auth")

    def get_tests(self) -> List[Test]:
        return [
            AuthRequiredTest(),
            AuthTokenValidTest(),
        ]

    def is_smoke_test(self) -> bool:
        # Auth enforcement is a critical security property — include in smoke
        return True

    def get_priority(self) -> int:
        # Run after health (0) but before bundle (1) so auth failures are
        # surfaced before we spend time on bundle/policy checks.
        return 0
