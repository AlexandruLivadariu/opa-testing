"""Extended OPA client tests covering retry strategy (issue #2 fix)."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from urllib3.util.retry import Retry

from src.opa_test_framework.client import OPAClient
from src.opa_test_framework.exceptions import OPAConnectionError


class TestRetryStrategy:
    """Tests for the split 429 / 5xx retry configuration (issue #2)."""

    def test_server_error_retry_excludes_429(self):
        """The server-error adapter must NOT retry on 429."""
        client = OPAClient(base_url="http://localhost:8181", max_retries=3)
        adapter = client.session.get_adapter("http://localhost:8181")
        retry: Retry = adapter.max_retries
        assert 429 not in retry.status_forcelist
        client.close()

    def test_server_error_retry_includes_5xx(self):
        """The server-error adapter must retry on common 5xx codes."""
        client = OPAClient(base_url="http://localhost:8181", max_retries=3)
        adapter = client.session.get_adapter("http://localhost:8181")
        retry: Retry = adapter.max_retries
        assert 500 in retry.status_forcelist
        assert 502 in retry.status_forcelist
        assert 503 in retry.status_forcelist
        assert 504 in retry.status_forcelist
        client.close()

    def test_rate_limit_retry_config_exists(self):
        """Client must carry a separate rate-limit retry configuration."""
        client = OPAClient(base_url="http://localhost:8181", max_retries=3)
        assert hasattr(client, "_rate_limit_retry")
        rl: Retry = client._rate_limit_retry
        assert 429 in rl.status_forcelist
        client.close()

    def test_rate_limit_retry_backoff_greater_than_server_error(self):
        """Rate-limit backoff must be more conservative than server-error backoff."""
        client = OPAClient(base_url="http://localhost:8181", max_retries=3)
        adapter = client.session.get_adapter("http://localhost:8181")
        server_retry: Retry = adapter.max_retries
        rl_retry: Retry = client._rate_limit_retry
        assert rl_retry.backoff_factor > server_retry.backoff_factor
        client.close()

    def test_rate_limit_fewer_retries_than_server_error(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=4)
        adapter = client.session.get_adapter("http://localhost:8181")
        server_retry: Retry = adapter.max_retries
        rl_retry: Retry = client._rate_limit_retry
        assert rl_retry.total <= server_retry.total
        client.close()

    def test_zero_max_retries_does_not_crash(self):
        client = OPAClient(base_url="http://localhost:8181", max_retries=0)
        assert hasattr(client, "_rate_limit_retry")
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
