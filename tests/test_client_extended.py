"""Extended OPA client tests covering retry strategy (issue #2 fix)."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from urllib3.util.retry import Retry

from src.opa_test_framework.client import OPAClient
from src.opa_test_framework.exceptions import OPAConnectionError


class TestRetryStrategy:
    """Tests for the unified retry configuration."""

    def test_retry_includes_429(self):
        """Retry adapter must handle 429 rate-limit responses."""
        client = OPAClient(base_url="http://localhost:8181", max_retries=3)
        adapter = client.session.get_adapter("http://localhost:8181")
        retry: Retry = adapter.max_retries
        assert 429 in retry.status_forcelist
        client.close()

    def test_retry_includes_5xx(self):
        """Retry adapter must handle common 5xx server errors."""
        client = OPAClient(base_url="http://localhost:8181", max_retries=3)
        adapter = client.session.get_adapter("http://localhost:8181")
        retry: Retry = adapter.max_retries
        assert 500 in retry.status_forcelist
        assert 502 in retry.status_forcelist
        assert 503 in retry.status_forcelist
        assert 504 in retry.status_forcelist
        client.close()

    def test_retry_respects_retry_after_header(self):
        """429 handling must respect the Retry-After header."""
        client = OPAClient(base_url="http://localhost:8181", max_retries=3)
        adapter = client.session.get_adapter("http://localhost:8181")
        retry: Retry = adapter.max_retries
        assert retry.respect_retry_after_header is True
        client.close()

    def test_zero_max_retries_does_not_crash(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        adapter = client.session.get_adapter("http://localhost:8181")
        assert adapter is not None
        client.close()


class TestOPAClientQueryMethod:
    """Tests for OPAClient.query with input_data."""

    def test_query_with_input(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [{"x": True}]}
        with patch.object(client.session, "request", return_value=mock_response) as mock_req:
            result = client.query("data.example.allow == true", input_data={"role": "admin"})
            assert result == [{"x": True}]
            call_kwargs = mock_req.call_args[1]
            assert call_kwargs["json"]["input"] == {"role": "admin"}
        client.close()

    def test_query_without_input(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        with patch.object(client.session, "request", return_value=mock_response) as mock_req:
            result = client.query("data.example.allow")
            assert result == []
            call_kwargs = mock_req.call_args[1]
            assert "input" not in call_kwargs["json"]
        client.close()


class TestOPAClientPutDelete:
    """Additional tests for put_data and delete_data."""

    def test_put_data_returns_true_on_200(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(client.session, "request", return_value=mock_response):
            assert client.put_data("test/path", {"k": "v"}) is True
        client.close()

    def test_delete_data_returns_true_on_200(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(client.session, "request", return_value=mock_response):
            assert client.delete_data("test/path") is True
        client.close()

    def test_generic_request_exception_raises_connection_error(self):
        """Any non-Timeout/ConnectionError RequestException wraps to OPAConnectionError."""
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        with patch.object(
            client.session,
            "request",
            side_effect=requests.RequestException("generic error"),
        ):
            with pytest.raises(OPAConnectionError):
                client._request("GET", "/health")
        client.close()


class TestOPAClientHTTPS:
    """Tests for HTTPS adapter mounting."""

    def test_https_adapter_mounted(self):
        client = OPAClient(base_url="https://opa.example.com:8181")
        adapter = client.session.get_adapter("https://opa.example.com:8181")
        assert adapter is not None
        client.close()
