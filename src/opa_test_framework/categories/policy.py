"""
Policy decision tests for OPA instances.
"""

import time
from typing import List

from ..client import OPAClient
from ..config import PolicyTest, TestConfig
from ..exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError
from ..models import TestResult, TestStatus
from .base import Test, TestCategory


class PolicyDecisionTest(Test):
    """Test that a policy returns the expected decision."""

    def __init__(self, policy_test: PolicyTest, is_smoke: bool = False):
        super().__init__(
            name=f"policy_{policy_test.name}",
            description=f"Test policy {policy_test.policy_path} with {policy_test.name}",
        )
        self.policy_test = policy_test
        self.is_smoke = is_smoke

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()
        try:
            decision = client.evaluate_policy(self.policy_test.policy_path, self.policy_test.input)
            duration_ms = (time.time() - start_time) * 1000

            # Compare result with expected output
            if decision.result != self.policy_test.expected_output:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message=f"Policy decision mismatch",
                    details={
                        "expected": self.policy_test.expected_output,
                        "actual": decision.result,
                        "policy_path": self.policy_test.policy_path,
                        "input": self.policy_test.input,
                    },
                )

            # If expected_allow is specified, verify it
            if self.policy_test.expected_allow is not None:
                actual_allow = (
                    decision.result.get("allow") if isinstance(decision.result, dict) else None
                )
                if actual_allow != self.policy_test.expected_allow:
                    return self._create_result(
                        status=TestStatus.FAIL,
                        duration_ms=duration_ms,
                        message=f"Allow field mismatch: expected {self.policy_test.expected_allow}, got {actual_allow}",
                        details={
                            "expected_allow": self.policy_test.expected_allow,
                            "actual_allow": actual_allow,
                            "result": decision.result,
                        },
                    )

            return self._create_result(
                status=TestStatus.PASS,
                duration_ms=duration_ms,
                message=f"Policy decision matches expected output",
                details={
                    "result": decision.result,
                    "policy_path": self.policy_test.policy_path,
                },
            )

        except (OPAConnectionError, OPATimeoutError, OPAHTTPError) as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Failed to evaluate policy: {str(e)}",
                details={"error": str(e), "policy_path": self.policy_test.policy_path},
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Unexpected error: {str(e)}",
                details={"error": str(e)},
            )


class PolicyTests(TestCategory):
    """Category for policy decision tests."""

    def __init__(self, config: TestConfig):
        super().__init__("policy")
        self.config = config

    def get_tests(self) -> List[Test]:
        tests = []
        for i, policy_test in enumerate(self.config.test_policies):
            # Use the smoke flag from config; default first test to smoke if none are marked
            is_smoke = policy_test.smoke if policy_test.smoke else (i == 0)
            tests.append(PolicyDecisionTest(policy_test, is_smoke=is_smoke))
        return tests

    def is_smoke_test(self) -> bool:
        # Category is a smoke test if any policy test is marked as smoke
        return any(pt.smoke or i == 0 for i, pt in enumerate(self.config.test_policies))

    def get_priority(self) -> int:
        return 2  # After health and bundle
