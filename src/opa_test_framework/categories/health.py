"""
Health check tests for OPA instances.
"""

import time
from typing import List

from ..client import OPAClient
from ..config import TestConfig
from ..exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError
from ..models import TestResult, TestStatus
from .base import Test, TestCategory


class HealthCheckTest(Test):
    """Test that OPA health endpoint returns 200 OK."""

    def __init__(self) -> None:
        super().__init__(
            name="health_check",
            description="Verify OPA health endpoint returns 200 OK",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()
        try:
            health_response = client.health()
            duration_ms = (time.time() - start_time) * 1000

            if health_response.status == "ok":
                return self._create_result(
                    status=TestStatus.PASS,
                    duration_ms=duration_ms,
                    message="Health check passed",
                    details={"status": health_response.status},
                )
            else:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message=f"Health status is not 'ok': {health_response.status}",
                    details={"status": health_response.status},
                )

        except (OPAConnectionError, OPATimeoutError) as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Failed to connect to OPA: {str(e)}",
                details={"error": str(e)},
            )
        except OPAHTTPError as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.FAIL,
                duration_ms=duration_ms,
                message=f"Health endpoint returned HTTP {e.status_code}",
                details={"status_code": e.status_code, "error": str(e)},
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Unexpected error: {str(e)}",
                details={"error": str(e)},
            )


class HealthResponseValidationTest(Test):
    """Test that health response contains valid metrics."""

    def __init__(self) -> None:
        super().__init__(
            name="health_response_validation",
            description="Verify health response contains valid metrics",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()
        try:
            health_response = client.health()
            duration_ms = (time.time() - start_time) * 1000

            # Validate that the status field has a non-empty value
            if not health_response.status:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message="Health response has empty or missing 'status' value",
                )

            return self._create_result(
                status=TestStatus.PASS,
                duration_ms=duration_ms,
                message="Health response validation passed",
                details={
                    "status": health_response.status,
                    "uptime_seconds": health_response.uptime_seconds,
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Error validating health response: {str(e)}",
                details={"error": str(e)},
            )


class HealthTests(TestCategory):
    """Category for health check tests."""

    def __init__(self) -> None:
        super().__init__("health")

    def get_tests(self) -> List[Test]:
        return [
            HealthCheckTest(),
            HealthResponseValidationTest(),
        ]

    def is_smoke_test(self) -> bool:
        return True

    def get_priority(self) -> int:
        return 0  # Highest priority
