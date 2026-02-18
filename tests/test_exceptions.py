"""Tests for custom exceptions."""

from src.opa_test_framework.exceptions import (
    OPAConnectionError,
    OPAHTTPError,
    OPAPolicyError,
    OPATestError,
    OPATimeoutError,
)


class TestOPATestError:
    """Tests for base exception."""

    def test_is_exception(self):
        assert issubclass(OPATestError, Exception)

    def test_message(self):
        err = OPATestError("test error")
        assert str(err) == "test error"


class TestOPAConnectionError:
    """Tests for connection error."""

    def test_inherits_from_base(self):
        assert issubclass(OPAConnectionError, OPATestError)

    def test_attributes(self):
        orig = ConnectionError("refused")
        err = OPAConnectionError("http://localhost:8181", orig)
        assert err.url == "http://localhost:8181"
        assert err.original_error is orig
        assert "localhost:8181" in str(err)


class TestOPATimeoutError:
    """Tests for timeout error."""

    def test_inherits_from_base(self):
        assert issubclass(OPATimeoutError, OPATestError)

    def test_attributes(self):
        err = OPATimeoutError("http://localhost:8181", 30)
        assert err.url == "http://localhost:8181"
        assert err.timeout == 30
        assert "30 seconds" in str(err)


class TestOPAHTTPError:
    """Tests for HTTP error."""

    def test_inherits_from_base(self):
        assert issubclass(OPAHTTPError, OPATestError)

    def test_attributes(self):
        err = OPAHTTPError(404, "http://localhost:8181/v1/data/foo", "not found")
        assert err.status_code == 404
        assert err.url == "http://localhost:8181/v1/data/foo"
        assert "404" in str(err)

    def test_response_body_truncated(self):
        long_body = "x" * 500
        err = OPAHTTPError(500, "http://localhost:8181", long_body)
        assert len(err.response_body) == 200

    def test_response_body_not_in_message(self):
        """Ensure sensitive response body is not leaked in error message."""
        err = OPAHTTPError(500, "http://localhost:8181", "secret-data-here")
        assert "secret-data-here" not in str(err)

    def test_empty_response_body(self):
        err = OPAHTTPError(500, "http://localhost:8181", "")
        assert err.response_body == ""


class TestOPAPolicyError:
    """Tests for policy error."""

    def test_inherits_from_base(self):
        assert issubclass(OPAPolicyError, OPATestError)

    def test_attributes(self):
        err = OPAPolicyError("example/allow", "evaluation failed")
        assert err.policy_path == "example/allow"
        assert err.error_message == "evaluation failed"
        assert "example/allow" in str(err)
