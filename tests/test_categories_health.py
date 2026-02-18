"""Tests for health check test categories."""

from unittest.mock import MagicMock

import pytest

from src.opa_test_framework.categories.health import (
    HealthCheckTest,
    HealthResponseValidationTest,
    HealthTests,
)
from src.opa_test_framework.config import TestConfig
from src.opa_test_framework.exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError
from src.opa_test_framework.models import HealthResponse, TestStatus


def _make_config(**kwargs):
    defaults = {"opa_url": "http://localhost:8181", "timeout_seconds": 10}
    defaults.update(kwargs)
    return TestConfig(**defaults)


def _make_client():
    return MagicMock()


class TestHealthCheckTest:
    """Tests for HealthCheckTest."""

    def test_passes_when_status_ok(self):
        config = _make_config()
        client = _make_client()
        client.health.return_value = HealthResponse(status="ok")
        result = HealthCheckTest().execute(client, config)
        assert result.status == TestStatus.PASS
        assert "passed" in result.message.lower()

    def test_fails_when_status_not_ok(self):
        config = _make_config()
        client = _make_client()
        client.health.return_value = HealthResponse(status="degraded")
        result = HealthCheckTest().execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "degraded" in result.message

    def test_error_on_connection_error(self):
        config = _make_config()
        client = _make_client()
        client.health.side_effect = OPAConnectionError(
            "http://localhost:8181", Exception("refused")
        )
        result = HealthCheckTest().execute(client, config)
        assert result.status == TestStatus.ERROR
        assert "connect" in result.message.lower()

    def test_error_on_timeout(self):
        config = _make_config()
        client = _make_client()
        client.health.side_effect = OPATimeoutError("http://localhost:8181", 10)
        result = HealthCheckTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_fail_on_http_error(self):
        config = _make_config()
        client = _make_client()
        client.health.side_effect = OPAHTTPError(503, "http://localhost:8181", "unavailable")
        result = HealthCheckTest().execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "503" in result.message

    def test_error_on_unexpected_exception(self):
        config = _make_config()
        client = _make_client()
        client.health.side_effect = RuntimeError("boom")
        result = HealthCheckTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_result_includes_status_detail(self):
        config = _make_config()
        client = _make_client()
        client.health.return_value = HealthResponse(status="ok")
        result = HealthCheckTest().execute(client, config)
        assert result.details.get("status") == "ok"

    def test_result_name(self):
        assert HealthCheckTest().name == "health_check"

    def test_duration_is_non_negative(self):
        config = _make_config()
        client = _make_client()
        client.health.return_value = HealthResponse(status="ok")
        result = HealthCheckTest().execute(client, config)
        assert result.duration_ms >= 0


class TestHealthResponseValidationTest:
    """Tests for HealthResponseValidationTest."""

    def test_passes_when_response_valid(self):
        config = _make_config()
        client = _make_client()
        client.health.return_value = HealthResponse(status="ok", uptime_seconds=3600)
        result = HealthResponseValidationTest().execute(client, config)
        assert result.status == TestStatus.PASS

    def test_passes_without_uptime(self):
        config = _make_config()
        client = _make_client()
        client.health.return_value = HealthResponse(status="ok")
        result = HealthResponseValidationTest().execute(client, config)
        assert result.status == TestStatus.PASS

    def test_error_on_exception(self):
        config = _make_config()
        client = _make_client()
        client.health.side_effect = RuntimeError("unexpected")
        result = HealthResponseValidationTest().execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_result_includes_status_detail(self):
        config = _make_config()
        client = _make_client()
        client.health.return_value = HealthResponse(status="ok", uptime_seconds=100)
        result = HealthResponseValidationTest().execute(client, config)
        assert result.details.get("status") == "ok"
        assert result.details.get("uptime_seconds") == 100

    def test_result_name(self):
        assert HealthResponseValidationTest().name == "health_response_validation"


class TestHealthTestsCategory:
    """Tests for HealthTests category class."""

    def test_name(self):
        assert HealthTests().name == "health"

    def test_is_smoke_test(self):
        assert HealthTests().is_smoke_test() is True

    def test_priority_is_zero(self):
        assert HealthTests().get_priority() == 0

    def test_returns_two_tests(self):
        tests = HealthTests().get_tests()
        assert len(tests) == 2
        names = [t.name for t in tests]
        assert "health_check" in names
        assert "health_response_validation" in names

    def test_execute_all_returns_results(self):
        config = _make_config()
        client = _make_client()
        client.health.return_value = HealthResponse(status="ok")
        results = HealthTests().execute_all(client, config)
        assert len(results) == 2
        assert all(r.status == TestStatus.PASS for r in results)
