"""Tests for authentication enforcement test category."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.opa_test_framework.categories.auth import (
    AuthRequiredTest,
    AuthTests,
    AuthTokenValidTest,
)
from src.opa_test_framework.config import TestConfig
from src.opa_test_framework.exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError
from src.opa_test_framework.models import TestStatus


def _make_config(**kwargs):
    defaults = {"opa_url": "http://localhost:8181", "timeout_seconds": 10}
    defaults.update(kwargs)
    return TestConfig(**defaults)


def _make_client(base_url="http://localhost:8181", auth_token=None):
    client = MagicMock()
    client.base_url = base_url
    client.timeout = 10
    client.auth_token = auth_token
    return client


class TestAuthRequiredTest:
    """Tests for AuthRequiredTest."""

    def test_skipped_when_no_auth_token(self):
        config = _make_config()  # no auth_token
        client = _make_client()
        test = AuthRequiredTest()
        result = test.execute(client, config)
        assert result.status == TestStatus.SKIP
        assert "no auth_token" in result.message.lower()

    def test_passes_when_opa_returns_401(self):
        config = _make_config(auth_token="secret")
        client = _make_client(auth_token="secret")
        test = AuthRequiredTest()

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("src.opa_test_framework.categories.auth.requests.Session") as MockSession:
            MockSession.return_value.get.return_value = mock_response
            result = test.execute(client, config)

        assert result.status == TestStatus.PASS
        assert "401" in result.message

    def test_fails_when_opa_returns_200_without_auth(self):
        """OPA should reject unauthenticated requests; 200 means auth is not enforced."""
        config = _make_config(auth_token="secret")
        client = _make_client(auth_token="secret")
        test = AuthRequiredTest()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("src.opa_test_framework.categories.auth.requests.Session") as MockSession:
            MockSession.return_value.get.return_value = mock_response
            result = test.execute(client, config)

        assert result.status == TestStatus.FAIL
        assert "200" in result.message

    def test_error_on_timeout(self):
        config = _make_config(auth_token="secret")
        client = _make_client(auth_token="secret")
        test = AuthRequiredTest()

        with patch("src.opa_test_framework.categories.auth.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = requests.Timeout()
            result = test.execute(client, config)

        assert result.status == TestStatus.ERROR
        assert "timed out" in result.message.lower()

    def test_error_on_connection_error(self):
        config = _make_config(auth_token="secret")
        client = _make_client(auth_token="secret")
        test = AuthRequiredTest()

        with patch("src.opa_test_framework.categories.auth.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = requests.ConnectionError("refused")
            result = test.execute(client, config)

        assert result.status == TestStatus.ERROR


class TestAuthTokenValidTest:
    """Tests for AuthTokenValidTest."""

    def test_skipped_when_no_auth_token(self):
        config = _make_config()
        client = _make_client()
        test = AuthTokenValidTest()
        result = test.execute(client, config)
        assert result.status == TestStatus.SKIP

    def test_passes_when_health_succeeds(self):
        config = _make_config(auth_token="good-token")
        client = _make_client(auth_token="good-token")
        client.health.return_value = MagicMock(status="ok")
        test = AuthTokenValidTest()
        result = test.execute(client, config)
        assert result.status == TestStatus.PASS
        assert "accepted" in result.message.lower()

    def test_fails_when_token_rejected_with_401(self):
        config = _make_config(auth_token="bad-token")
        client = _make_client(auth_token="bad-token")
        client.health.side_effect = OPAHTTPError(401, "http://localhost:8181", "unauthorized")
        test = AuthTokenValidTest()
        result = test.execute(client, config)
        assert result.status == TestStatus.FAIL
        assert "401" in result.message

    def test_error_on_unexpected_http_error(self):
        config = _make_config(auth_token="token")
        client = _make_client(auth_token="token")
        client.health.side_effect = OPAHTTPError(500, "http://localhost:8181", "server error")
        test = AuthTokenValidTest()
        result = test.execute(client, config)
        assert result.status == TestStatus.ERROR

    def test_error_on_unexpected_exception(self):
        config = _make_config(auth_token="token")
        client = _make_client(auth_token="token")
        client.health.side_effect = RuntimeError("unexpected")
        test = AuthTokenValidTest()
        result = test.execute(client, config)
        assert result.status == TestStatus.ERROR


class TestAuthTestsCategory:
    """Tests for the AuthTests category."""

    def test_name(self):
        assert AuthTests().name == "auth"

    def test_is_smoke_test(self):
        assert AuthTests().is_smoke_test() is True

    def test_priority_at_most_one(self):
        # Auth must run before bundle (priority 1)
        assert AuthTests().get_priority() <= 1

    def test_returns_two_tests(self):
        tests = AuthTests().get_tests()
        assert len(tests) == 2
        names = [t.name for t in tests]
        assert "auth_required" in names
        assert "auth_token_valid" in names

    def test_execute_all_without_auth_skips_all(self):
        config = _make_config()
        client = _make_client()
        results = AuthTests().execute_all(client, config)
        assert all(r.status == TestStatus.SKIP for r in results)
