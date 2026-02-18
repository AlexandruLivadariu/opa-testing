"""
Bundle status tests for OPA instances.
"""

import time
from typing import List

from ..client import OPAClient
from ..config import TestConfig
from ..exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError
from ..models import TestResult, TestStatus
from .base import Test, TestCategory


class BundleStatusTest(Test):
    """Test that at least one bundle is loaded."""

    def __init__(self) -> None:
        super().__init__(
            name="bundle_status",
            description="Verify at least one bundle is loaded in OPA",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()
        try:
            bundles = client.get_bundle_status()
            duration_ms = (time.time() - start_time) * 1000

            if not bundles:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message="No bundles loaded in OPA",
                )

            bundle_names = list(bundles.keys())
            return self._create_result(
                status=TestStatus.PASS,
                duration_ms=duration_ms,
                message=f"Found {len(bundles)} bundle(s) loaded",
                details={"bundle_count": len(bundles), "bundle_names": bundle_names},
            )

        except (OPAConnectionError, OPATimeoutError, OPAHTTPError) as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Failed to get bundle status: {str(e)}",
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


class BundleRevisionTest(Test):
    """Test that bundle revision matches expected version."""

    def __init__(self) -> None:
        super().__init__(
            name="bundle_revision",
            description="Verify bundle revision matches expected version",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()
        try:
            # Skip if no expected revision configured
            if not config.expected_bundle_revision:
                duration_ms = (time.time() - start_time) * 1000
                return self._create_result(
                    status=TestStatus.SKIP,
                    duration_ms=duration_ms,
                    message="No expected bundle revision configured",
                )

            bundles = client.get_bundle_status()
            duration_ms = (time.time() - start_time) * 1000

            if not bundles:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message="No bundles loaded to check revision",
                )

            # Check each bundle's revision
            mismatches = []
            for bundle_name, bundle in bundles.items():
                if bundle.active_revision != config.expected_bundle_revision:
                    mismatches.append(
                        f"{bundle_name}: {bundle.active_revision} "
                        f"(expected {config.expected_bundle_revision})"
                    )

            if mismatches:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message=f"Bundle revision mismatch: {', '.join(mismatches)}",
                    details={"mismatches": mismatches},
                )

            return self._create_result(
                status=TestStatus.PASS,
                duration_ms=duration_ms,
                message=f"All bundles have expected revision: {config.expected_bundle_revision}",
                details={"expected_revision": config.expected_bundle_revision},
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Error checking bundle revision: {str(e)}",
                details={"error": str(e)},
            )


class BundleEvaluabilityTest(Test):
    """Test that loaded bundle policies are actually evaluable by OPA.

    A bundle can be *present* (the status endpoint lists it) yet still be in a
    broken state where OPA cannot evaluate any of its rules — e.g. a parse
    error that was accepted during activation but causes runtime failures.

    This test issues a minimal ``data`` query and confirms that OPA returns a
    non-error response, proving the runtime policy graph is intact.
    """

    def __init__(self) -> None:
        super().__init__(
            name="bundle_evaluability",
            description="Verify that bundle policies are evaluable at runtime",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()
        try:
            # Query the top-level data document — this touches the compiled
            # policy graph and will surface any compilation/activation errors.
            result = client.get_data("")
            duration_ms = (time.time() - start_time) * 1000

            # A None result means OPA returned an empty data document which
            # is perfectly valid (e.g. no data loaded yet).  The important
            # thing is that the call did not raise an exception.
            return self._create_result(
                status=TestStatus.PASS,
                duration_ms=duration_ms,
                message="Bundle policies are evaluable",
                details={"data_keys": list(result.keys()) if isinstance(result, dict) else []},
            )

        except (OPAConnectionError, OPATimeoutError) as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Could not reach OPA to verify evaluability: {str(e)}",
                details={"error": str(e)},
            )
        except OPAHTTPError as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.FAIL,
                duration_ms=duration_ms,
                message=(
                    f"OPA returned HTTP {e.status_code} when querying the data "
                    f"document — bundle policies may be broken"
                ),
                details={"status_code": e.status_code, "error": str(e)},
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Unexpected error during evaluability check: {str(e)}",
                details={"error": str(e)},
            )


class BundleTests(TestCategory):
    """Category for bundle status tests."""

    def __init__(self) -> None:
        super().__init__("bundle")

    def get_tests(self) -> List[Test]:
        return [
            BundleStatusTest(),
            BundleRevisionTest(),
            BundleEvaluabilityTest(),
        ]

    def is_smoke_test(self) -> bool:
        return True  # Bundle status is critical

    def get_priority(self) -> int:
        return 1  # High priority, after health
