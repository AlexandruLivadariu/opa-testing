"""Tests for bundle test categories including the new evaluability test."""

from unittest.mock import MagicMock


from src.opa_test_framework.categories.bundle import (
    BundleEvaluabilityTest,
    BundleRevisionTest,
    BundleStatusTest,
    BundleTests,
)
from src.opa_test_framework.config import TestConfig
from src.opa_test_framework.exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError
from src.opa_test_framework.models import BundleStatus, TestStatus


def _make_config(**kwargs):
    defaults = {"opa_url": "http://localhost:8181", "timeout_seconds": 10}
    defaults.update(kwargs)
    return TestConfig(**defaults)


def _make_client():
    return MagicMock()


def _bundle(name="main", revision="v1.0.0"):
    return BundleStatus(name=name, active_revision=revision)


class TestBundleStatusTest:
    """Tests for BundleStatusTest."""

    def test_passes_with_bundles(self):
        config = _make_config()
        client = _make_client()
        client.get_bundle_status.return_value = {"main": _bundle()}
        result = BundleStatusTest().execute(client, config)
        assert result.status == TestStatus.PASS
        assert "1" in result.message

    def test_fails_with_no_bundles(self):
        config = _make_config()
        client = _make_client()
        client.get_bundle_status.return_value = {}
        result = BundleStatusTest().execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "No bundles" in result.message

    def test_error_on_connection_error(self):
        config = _make_config()
        client = _make_client()
        client.get_bundle_status.side_effect = OPAConnectionError(
            "http://localhost:8181", Exception("refused")
        )
        result = BundleStatusTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_error_on_timeout(self):
        config = _make_config()
        client = _make_client()
        client.get_bundle_status.side_effect = OPATimeoutError("http://localhost:8181", 10)
        result = BundleStatusTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_error_on_http_error(self):
        config = _make_config()
        client = _make_client()
        client.get_bundle_status.side_effect = OPAHTTPError(
            503, "http://localhost:8181", "service unavailable"
        )
        result = BundleStatusTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_passes_with_multiple_bundles(self):
        config = _make_config()
        client = _make_client()
        client.get_bundle_status.return_value = {
            "main": _bundle("main"),
            "secondary": _bundle("secondary"),
        }
        result = BundleStatusTest().execute(client, config)
        assert result.status == TestStatus.PASS
        assert result.details["bundle_count"] == 2


class TestBundleRevisionTest:
    """Tests for BundleRevisionTest."""

    def test_skipped_when_no_expected_revision(self):
        config = _make_config()  # no expected_bundle_revision
        client = _make_client()
        result = BundleRevisionTest().execute(client, config)
        assert result.status == TestStatus.SKIP

    def test_passes_when_revision_matches(self):
        config = _make_config(expected_bundle_revision="v2.0.0")
        client = _make_client()
        client.get_bundle_status.return_value = {"main": _bundle(revision="v2.0.0")}
        result = BundleRevisionTest().execute(client, config)
        assert result.status == TestStatus.PASS

    def test_fails_when_revision_mismatches(self):
        config = _make_config(expected_bundle_revision="v2.0.0")
        client = _make_client()
        client.get_bundle_status.return_value = {"main": _bundle(revision="v1.0.0")}
        result = BundleRevisionTest().execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "mismatch" in result.message.lower()

    def test_fails_when_no_bundles_loaded(self):
        config = _make_config(expected_bundle_revision="v2.0.0")
        client = _make_client()
        client.get_bundle_status.return_value = {}
        result = BundleRevisionTest().execute(client, config)
        assert result.status == TestStatus.FAIL

    def test_partial_mismatch_fails(self):
        """All bundles must match the expected revision."""
        config = _make_config(expected_bundle_revision="v2.0.0")
        client = _make_client()
        client.get_bundle_status.return_value = {
            "main": _bundle("main", "v2.0.0"),
            "extra": _bundle("extra", "v1.0.0"),
        }
        result = BundleRevisionTest().execute(client, config)
        assert result.status == TestStatus.FAIL
        assert len(result.details["mismatches"]) == 1

    def test_error_on_exception(self):
        config = _make_config(expected_bundle_revision="v1.0.0")
        client = _make_client()
        client.get_bundle_status.side_effect = RuntimeError("unexpected")
        result = BundleRevisionTest().execute(client, config)
        assert result.status == TestStatus.ERROR


class TestBundleEvaluabilityTest:
    """Tests for BundleEvaluabilityTest (issue #3 fix)."""

    def test_passes_when_data_returns_dict(self):
        config = _make_config()
        client = _make_client()
        client.get_data.return_value = {"example": {}}
        result = BundleEvaluabilityTest().execute(client, config)
        assert result.status == TestStatus.PASS
        assert "evaluable" in result.message.lower()
        assert "example" in result.details["data_keys"]

    def test_passes_when_data_returns_none(self):
        """Empty data document is valid — OPA just has no data loaded."""
        config = _make_config()
        client = _make_client()
        client.get_data.return_value = None
        result = BundleEvaluabilityTest().execute(client, config)
        assert result.status == TestStatus.PASS

    def test_passes_when_data_returns_empty_dict(self):
        config = _make_config()
        client = _make_client()
        client.get_data.return_value = {}
        result = BundleEvaluabilityTest().execute(client, config)
        assert result.status == TestStatus.PASS
        assert result.details["data_keys"] == []

    def test_fails_on_http_error(self):
        """HTTP error from OPA data endpoint means bundle may be broken."""
        config = _make_config()
        client = _make_client()
        client.get_data.side_effect = OPAHTTPError(500, "http://localhost:8181", "server error")
        result = BundleEvaluabilityTest().execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "500" in result.message

    def test_error_on_connection_error(self):
        config = _make_config()
        client = _make_client()
        client.get_data.side_effect = OPAConnectionError(
            "http://localhost:8181", Exception("refused")
        )
        result = BundleEvaluabilityTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_error_on_timeout(self):
        config = _make_config()
        client = _make_client()
        client.get_data.side_effect = OPATimeoutError("http://localhost:8181", 10)
        result = BundleEvaluabilityTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_error_on_unexpected_exception(self):
        config = _make_config()
        client = _make_client()
        client.get_data.side_effect = RuntimeError("unexpected")
        result = BundleEvaluabilityTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_calls_get_data_with_empty_path(self):
        """Must query the top-level data document (empty path)."""
        config = _make_config()
        client = _make_client()
        client.get_data.return_value = {}
        BundleEvaluabilityTest().execute(client, config)
        client.get_data.assert_called_once_with("")


class TestBundleTestsCategory:
    """Tests for BundleTests category class."""

    def test_name(self):
        assert BundleTests().name == "bundle"

    def test_is_smoke_test(self):
        assert BundleTests().is_smoke_test() is True

    def test_priority_is_1(self):
        assert BundleTests().get_priority() == 1

    def test_returns_three_tests(self):
        tests = BundleTests().get_tests()
        assert len(tests) == 3
        names = [t.name for t in tests]
        assert "bundle_status" in names
        assert "bundle_revision" in names
        assert "bundle_evaluability" in names
