"""Tests for policy decision test categories."""

from unittest.mock import MagicMock

from src.opa_test_framework.categories.policy import (
    PolicyDecisionTest,
    PolicyTests,
)
from src.opa_test_framework.config import PolicyTest, TestConfig
from src.opa_test_framework.exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError
from src.opa_test_framework.models import PolicyDecision, TestStatus


def _make_config(**kwargs):
    defaults = {"opa_url": "http://localhost:8181", "timeout_seconds": 10}
    defaults.update(kwargs)
    return TestConfig(**defaults)


def _make_client():
    return MagicMock()


def _policy_test(**kwargs):
    defaults = {
        "name": "test_allow",
        "policy_path": "example/allow",
        "input": {"user": "alice", "role": "admin"},
        "expected_output": True,
    }
    defaults.update(kwargs)
    return PolicyTest(**defaults)


class TestPolicyDecisionTest:
    """Tests for PolicyDecisionTest."""

    def test_passes_when_result_matches_expected(self):
        config = _make_config()
        client = _make_client()
        client.evaluate_policy.return_value = PolicyDecision(result=True)
        pt = _policy_test(expected_output=True)
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.PASS
        assert "matches" in result.message.lower()

    def test_fails_when_result_mismatches(self):
        config = _make_config()
        client = _make_client()
        client.evaluate_policy.return_value = PolicyDecision(result=False)
        pt = _policy_test(expected_output=True)
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "mismatch" in result.message.lower()
        assert result.details["expected"] is True
        assert result.details["actual"] is False

    def test_passes_with_dict_result(self):
        config = _make_config()
        client = _make_client()
        expected = {"allow": True, "reason": "admin"}
        client.evaluate_policy.return_value = PolicyDecision(result=expected)
        pt = _policy_test(expected_output=expected)
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.PASS

    def test_passes_with_list_result(self):
        config = _make_config()
        client = _make_client()
        expected = ["read"]
        client.evaluate_policy.return_value = PolicyDecision(result=expected)
        pt = _policy_test(expected_output=expected)
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.PASS

    def test_expected_allow_passes(self):
        config = _make_config()
        client = _make_client()
        result_data = {"allow": True, "reason": "admin"}
        client.evaluate_policy.return_value = PolicyDecision(result=result_data)
        pt = _policy_test(expected_output=result_data, expected_allow=True)
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.PASS

    def test_expected_allow_fails_on_mismatch(self):
        config = _make_config()
        client = _make_client()
        result_data = {"allow": False, "reason": "denied"}
        client.evaluate_policy.return_value = PolicyDecision(result=result_data)
        pt = _policy_test(expected_output=result_data, expected_allow=True)
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "allow" in result.message.lower()

    def test_expected_allow_non_dict_result(self):
        """When result is not a dict, allow field is None → mismatch."""
        config = _make_config()
        client = _make_client()
        client.evaluate_policy.return_value = PolicyDecision(result=True)
        pt = _policy_test(expected_output=True, expected_allow=True)
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "allow" in result.message.lower()

    def test_error_on_connection_error(self):
        config = _make_config()
        client = _make_client()
        client.evaluate_policy.side_effect = OPAConnectionError(
            "http://localhost:8181", Exception("refused")
        )
        pt = _policy_test()
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.ERROR
        assert "example/allow" in result.details.get("policy_path", "")

    def test_error_on_timeout(self):
        config = _make_config()
        client = _make_client()
        client.evaluate_policy.side_effect = OPATimeoutError("http://localhost:8181", 10)
        pt = _policy_test()
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_error_on_http_error(self):
        config = _make_config()
        client = _make_client()
        client.evaluate_policy.side_effect = OPAHTTPError(404, "http://localhost:8181", "not found")
        pt = _policy_test()
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_error_on_unexpected_exception(self):
        config = _make_config()
        client = _make_client()
        client.evaluate_policy.side_effect = RuntimeError("unexpected")
        pt = _policy_test()
        result = PolicyDecisionTest(pt).execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_name_includes_policy_name(self):
        pt = _policy_test(name="my_test")
        test = PolicyDecisionTest(pt)
        assert test.name == "policy_my_test"

    def test_calls_evaluate_with_correct_args(self):
        config = _make_config()
        client = _make_client()
        client.evaluate_policy.return_value = PolicyDecision(result=True)
        pt = _policy_test(
            policy_path="authz/allow",
            input={"role": "viewer"},
            expected_output=True,
        )
        PolicyDecisionTest(pt).execute(client, config)
        client.evaluate_policy.assert_called_once_with("authz/allow", {"role": "viewer"})


class TestPolicyTestsCategory:
    """Tests for PolicyTests category class."""

    def test_name(self):
        config = _make_config(
            test_policies=[_policy_test()],
        )
        assert PolicyTests(config).name == "policy"

    def test_priority_is_2(self):
        config = _make_config(
            test_policies=[_policy_test()],
        )
        assert PolicyTests(config).get_priority() == 2

    def test_is_smoke_test_default_first(self):
        """When no test has smoke=True, category is still smoke (first test auto-smoke)."""
        config = _make_config(
            test_policies=[_policy_test(), _policy_test(name="second")],
        )
        assert PolicyTests(config).is_smoke_test() is True

    def test_is_smoke_test_explicit(self):
        config = _make_config(
            test_policies=[_policy_test(smoke=True)],
        )
        assert PolicyTests(config).is_smoke_test() is True

    def test_get_tests_returns_correct_count(self):
        config = _make_config(
            test_policies=[
                _policy_test(name="t1"),
                _policy_test(name="t2"),
                _policy_test(name="t3"),
            ],
        )
        tests = PolicyTests(config).get_tests()
        assert len(tests) == 3

    def test_first_test_is_smoke_by_default(self):
        """When no test is explicitly smoke, the first one gets is_smoke=True."""
        config = _make_config(
            test_policies=[_policy_test(name="first"), _policy_test(name="second")],
        )
        tests = PolicyTests(config).get_tests()
        assert tests[0].is_smoke is True
        assert tests[1].is_smoke is False

    def test_explicit_smoke_flag_honoured(self):
        """When a test has smoke=True, only that test is smoke."""
        config = _make_config(
            test_policies=[
                _policy_test(name="first", smoke=False),
                _policy_test(name="second", smoke=True),
            ],
        )
        tests = PolicyTests(config).get_tests()
        assert tests[0].is_smoke is False
        assert tests[1].is_smoke is True

    def test_empty_policies(self):
        config = _make_config(test_policies=[])
        tests = PolicyTests(config).get_tests()
        assert tests == []
