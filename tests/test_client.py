"""Tests for OPA HTTP client."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.opa_test_framework.client import OPAClient
from src.opa_test_framework.exceptions import (
    OPAConnectionError,
    OPAHTTPError,
    OPATimeoutError,
)


class TestOPAClientInit:
    """Tests for OPAClient initialization."""

    def test_base_url_stripped(self):
        client = OPAClient(base_url="http://localhost:8181/")
        assert client.base_url == "http://localhost:8181"

    def test_default_timeout(self):
        client = OPAClient(base_url="http://localhost:8181")
        assert client.timeout == 10

    def test_custom_timeout(self):
        client = OPAClient(base_url="http://localhost:8181", timeout=30)
        assert client.timeout == 30

    def test_auth_header_set(self):
        client = OPAClient(base_url="http://localhost:8181", auth_token="my-token")
        assert client.session.headers.get("Authorization") == "Bearer my-token"

    def test_no_auth_header_without_token(self):
        client = OPAClient(base_url="http://localhost:8181")
        assert "Authorization" not in client.session.headers

    def test_context_manager(self):
        with OPAClient(base_url="http://localhost:8181") as client:
            assert client is not None

    def test_close(self):
        client = OPAClient(base_url="http://localhost:8181")
        with patch.object(client.session, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()

    def test_context_manager_calls_close(self):
        """Exiting the context manager must close the session."""
        client = OPAClient(base_url="http://localhost:8181")
        with patch.object(client.session, "close") as mock_session_close:
            with client:
                pass  # __exit__ fires after this block
            mock_session_close.assert_called_once()


class TestOPAClientRequest:
    """Tests for OPAClient._request method using mocked session."""

    def test_connection_error_raises(self):
        client = OPAClient(base_url="http://nonexistent:9999", max_retries=0)
        with pytest.raises(OPAConnectionError):
            client._request("GET", "/health")
        client.close()

    def test_timeout_error_raises(self):
        client = OPAClient(base_url="http://localhost:8181", timeout=0.001, max_retries=0)
        with patch.object(client.session, "request", side_effect=requests.Timeout()):
            with pytest.raises(OPATimeoutError):
                client._request("GET", "/health")
        client.close()

    def test_http_error_raises(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "not found"
        with patch.object(client.session, "request", return_value=mock_response):
            with pytest.raises(OPAHTTPError) as exc_info:
                client._request("GET", "/v1/data/missing")
            assert exc_info.value.status_code == 404
        client.close()

    def test_successful_request(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "ok"}'
        with patch.object(client.session, "request", return_value=mock_response):
            response, duration_ms = client._request("GET", "/health")
            assert response.status_code == 200
            assert duration_ms >= 0
        client.close()

    def test_request_returns_timing(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(client.session, "request", return_value=mock_response):
            _, duration_ms = client._request("GET", "/health")
            assert isinstance(duration_ms, float)
            assert duration_ms >= 0
        client.close()


class TestOPAClientHealth:
    """Tests for OPAClient.health method."""

    def test_health_ok(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"status": "ok", "uptime_seconds": 3600}'
        mock_response.json.return_value = {"status": "ok", "uptime_seconds": 3600}
        with patch.object(client.session, "request", return_value=mock_response):
            health = client.health()
            assert health.status == "ok"
            assert health.uptime_seconds == 3600
        client.close()

    def test_health_empty_response(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        with patch.object(client.session, "request", return_value=mock_response):
            health = client.health()
            assert health.status == "ok"  # Default when empty
        client.close()


class TestOPAClientEvaluatePolicy:
    """Tests for OPAClient.evaluate_policy method."""

    def test_evaluate_policy(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {"allow": True},
            "decision_id": "abc-123",
        }
        with patch.object(client.session, "request", return_value=mock_response):
            decision = client.evaluate_policy("example/allow", {"role": "admin", "action": "read"})
            assert decision.result == {"allow": True}
            assert decision.decision_id == "abc-123"
        client.close()


class TestOPAClientBundleStatus:
    """Tests for OPAClient.get_bundle_status method."""

    def test_bundle_status(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"bundles": {}}'
        mock_response.json.return_value = {
            "bundles": {
                "example": {
                    "active_revision": "v1.0.0",
                    "last_successful_download": "2024-01-01T00:00:00Z",
                }
            }
        }
        with patch.object(client.session, "request", return_value=mock_response):
            bundles = client.get_bundle_status()
            assert "example" in bundles
            assert bundles["example"].active_revision == "v1.0.0"
        client.close()

    def test_bundle_status_empty(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"bundles": {}}'
        mock_response.json.return_value = {"bundles": {}}
        with patch.object(client.session, "request", return_value=mock_response):
            bundles = client.get_bundle_status()
            assert bundles == {}
        client.close()

    def test_bundle_status_empty_content(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        with patch.object(client.session, "request", return_value=mock_response):
            bundles = client.get_bundle_status()
            assert bundles == {}
        client.close()


class TestOPAClientDataAPI:
    """Tests for OPAClient data API methods."""

    def test_get_data(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"key": "value"}}
        with patch.object(client.session, "request", return_value=mock_response):
            data = client.get_data("test/path")
            assert data == {"key": "value"}
        client.close()

    def test_put_data_success(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 204
        with patch.object(client.session, "request", return_value=mock_response):
            result = client.put_data("test/path", {"key": "value"})
            assert result is True
        client.close()

    def test_delete_data_success(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 204
        with patch.object(client.session, "request", return_value=mock_response):
            result = client.delete_data("test/path")
            assert result is True
        client.close()

    def test_query(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [{"x": 1}]}
        with patch.object(client.session, "request", return_value=mock_response):
            result = client.query("data.example.allow == true")
            assert result == [{"x": 1}]
        client.close()


class TestSafeJson:
    """Tests for OPAClient._safe_json helper."""

    def test_valid_json(self):
        response = MagicMock()
        response.json.return_value = {"key": "value"}
        assert OPAClient._safe_json(response) == {"key": "value"}

    def test_invalid_json_returns_fallback(self):
        import json

        response = MagicMock()
        response.json.side_effect = json.JSONDecodeError("err", "", 0)
        response.url = "http://localhost:8181/test"
        response.content = b"not-json"
        assert OPAClient._safe_json(response, fallback={}) == {}

    def test_invalid_json_default_fallback_is_none(self):
        import json

        response = MagicMock()
        response.json.side_effect = json.JSONDecodeError("err", "", 0)
        response.url = "http://localhost:8181/test"
        response.content = b""
        assert OPAClient._safe_json(response) is None

    def test_evaluate_policy_with_malformed_json(self):
        """evaluate_policy should not crash on malformed JSON."""
        import json as json_mod

        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json_mod.JSONDecodeError("err", "", 0)
        mock_response.url = "http://localhost:8181/v1/data/test"
        mock_response.content = b"broken"
        with patch.object(client.session, "request", return_value=mock_response):
            decision = client.evaluate_policy("test", {"role": "admin"})
            assert decision.result is None
        client.close()
