"""Tests for configuration management."""

import os
import tempfile

import pytest
import yaml

from src.opa_test_framework.config import (
    ConfigurationError,
    PerformanceThresholds,
    PolicyTest,
    TestConfig,
    _parse_env_int,
    load_config,
    validate_config,
)


class TestPerformanceThresholds:
    """Tests for PerformanceThresholds dataclass."""

    def test_defaults(self):
        thresholds = PerformanceThresholds()
        assert thresholds.max_response_time_ms == 500
        assert thresholds.warning_threshold_ms == 100

    def test_custom_values(self):
        thresholds = PerformanceThresholds(max_response_time_ms=1000, warning_threshold_ms=200)
        assert thresholds.max_response_time_ms == 1000
        assert thresholds.warning_threshold_ms == 200


class TestPolicyTest:
    """Tests for PolicyTest dataclass."""

    def test_required_fields(self):
        pt = PolicyTest(
            name="test1",
            policy_path="example/allow",
            input={"role": "admin"},
            expected_output={"allow": True},
        )
        assert pt.name == "test1"
        assert pt.expected_allow is None
        assert pt.smoke is False

    def test_optional_fields(self):
        pt = PolicyTest(
            name="test1",
            policy_path="example/allow",
            input={"role": "admin"},
            expected_output={"allow": True},
            expected_allow=True,
            smoke=True,
        )
        assert pt.expected_allow is True
        assert pt.smoke is True


class TestTestConfig:
    """Tests for TestConfig dataclass."""

    def test_defaults(self):
        config = TestConfig()
        assert config.opa_url == "http://localhost:8181"
        assert config.timeout_seconds == 10
        assert config.auth_token is None
        assert config.report_format == "console"

    def test_opa_urls_populated_from_opa_url(self):
        config = TestConfig(opa_url="http://custom:9999")
        assert config.opa_urls == ["http://custom:9999"]

    def test_opa_urls_preserved_if_set(self):
        config = TestConfig(
            opa_url="http://main:8181",
            opa_urls=["http://opa1:8181", "http://opa2:8181"],
        )
        assert len(config.opa_urls) == 2
        assert "http://opa1:8181" in config.opa_urls

    def test_dict_to_performance_thresholds(self):
        config = TestConfig(
            performance_thresholds={"max_response_time_ms": 999, "warning_threshold_ms": 50}
        )
        assert isinstance(config.performance_thresholds, PerformanceThresholds)
        assert config.performance_thresholds.max_response_time_ms == 999

    def test_dict_to_policy_test(self):
        config = TestConfig(
            test_policies=[
                {
                    "name": "test1",
                    "policy_path": "example/allow",
                    "input": {"role": "admin"},
                    "expected_output": {"allow": True},
                }
            ]
        )
        assert len(config.test_policies) == 1
        assert isinstance(config.test_policies[0], PolicyTest)
        assert config.test_policies[0].name == "test1"


class TestParseEnvInt:
    """Tests for _parse_env_int helper."""

    def test_returns_none_when_not_set(self):
        assert _parse_env_int("NONEXISTENT_VAR_12345") is None

    def test_parses_valid_int(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "42")
        assert _parse_env_int("TEST_INT_VAR") == 42

    def test_parses_negative_int(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "-5")
        assert _parse_env_int("TEST_INT_VAR") == -5

    def test_raises_on_invalid_value(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "not_a_number")
        with pytest.raises(ConfigurationError, match="must be a valid integer"):
            _parse_env_int("TEST_INT_VAR")

    def test_raises_on_float_value(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "3.14")
        with pytest.raises(ConfigurationError):
            _parse_env_int("TEST_INT_VAR")


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_defaults_without_file(self):
        config = load_config()
        assert config.opa_url == "http://localhost:8181"
        assert config.timeout_seconds == 10

    def test_load_from_yaml_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"opa_url": "http://custom:9999", "timeout_seconds": 30}))
        config = load_config(str(config_file))
        assert config.opa_url == "http://custom:9999"
        assert config.timeout_seconds == 30

    def test_env_overrides_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"opa_url": "http://from-file:8181"}))
        monkeypatch.setenv("OPA_URL", "http://from-env:8181")

        config = load_config(str(config_file))
        assert config.opa_url == "http://from-env:8181"

    def test_env_timeout_override(self, monkeypatch):
        monkeypatch.setenv("OPA_TIMEOUT", "60")
        config = load_config()
        assert config.timeout_seconds == 60

    def test_invalid_env_timeout_raises(self, monkeypatch):
        monkeypatch.setenv("OPA_TIMEOUT", "abc")
        with pytest.raises(ConfigurationError, match="must be a valid integer"):
            load_config()

    def test_invalid_yaml_raises(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text(":\ninvalid: [yaml: {broken")
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            load_config(str(config_file))

    def test_empty_yaml_file(self, tmp_path):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        config = load_config(str(config_file))
        assert config.opa_url == "http://localhost:8181"

    def test_env_auth_token(self, monkeypatch):
        monkeypatch.setenv("OPA_AUTH_TOKEN", "my-secret-token")
        config = load_config()
        assert config.auth_token == "my-secret-token"

    def test_env_report_format(self, monkeypatch):
        monkeypatch.setenv("OPA_REPORT_FORMAT", "junit")
        config = load_config()
        assert config.report_format == "junit"

    def test_env_performance_thresholds(self, monkeypatch):
        monkeypatch.setenv("OPA_MAX_RESPONSE_TIME_MS", "1000")
        monkeypatch.setenv("OPA_WARNING_THRESHOLD_MS", "200")
        config = load_config()
        assert config.performance_thresholds.max_response_time_ms == 1000
        assert config.performance_thresholds.warning_threshold_ms == 200


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config(self):
        config = TestConfig(opa_url="http://localhost:8181")
        errors = validate_config(config)
        assert errors == []

    def test_missing_url(self):
        config = TestConfig(opa_url="")
        errors = validate_config(config)
        assert any("opa_url is required" in e for e in errors)

    def test_invalid_url_scheme(self):
        config = TestConfig(opa_url="ftp://localhost:8181")
        errors = validate_config(config)
        assert any("must start with http://" in e for e in errors)

    def test_negative_timeout(self):
        config = TestConfig(timeout_seconds=-1)
        errors = validate_config(config)
        assert any("timeout_seconds must be positive" in e for e in errors)

    def test_zero_timeout(self):
        config = TestConfig(timeout_seconds=0)
        errors = validate_config(config)
        assert any("timeout_seconds must be positive" in e for e in errors)

    def test_excessive_timeout(self):
        config = TestConfig(timeout_seconds=999)
        errors = validate_config(config)
        assert any("too large" in e for e in errors)

    def test_invalid_report_format(self):
        config = TestConfig(report_format="xml")
        errors = validate_config(config)
        assert any("report_format" in e for e in errors)

    def test_warning_gte_max_threshold(self):
        config = TestConfig(
            performance_thresholds=PerformanceThresholds(
                max_response_time_ms=100, warning_threshold_ms=200
            )
        )
        errors = validate_config(config)
        assert any("warning_threshold_ms must be less than" in e for e in errors)

    def test_bundle_service_url_validation(self):
        config = TestConfig(bundle_service_url="not-a-url")
        errors = validate_config(config)
        assert any("bundle_service_url" in e for e in errors)

    def test_policy_test_missing_name(self):
        config = TestConfig(
            test_policies=[
                PolicyTest(
                    name="",
                    policy_path="example/allow",
                    input={"role": "admin"},
                    expected_output={"allow": True},
                )
            ]
        )
        errors = validate_config(config)
        assert any("missing name" in e for e in errors)

    def test_policy_test_missing_path(self):
        config = TestConfig(
            test_policies=[
                PolicyTest(
                    name="test1",
                    policy_path="",
                    input={"role": "admin"},
                    expected_output={"allow": True},
                )
            ]
        )
        errors = validate_config(config)
        assert any("missing policy_path" in e for e in errors)
