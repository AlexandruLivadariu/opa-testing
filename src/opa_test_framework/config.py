"""
Configuration management for OPA test framework.
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)

# Module-level lock for thread-safe config loading
_config_lock = threading.Lock()


class ConfigurationError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""

    pass


@dataclass
class PerformanceThresholds:
    """Performance threshold configuration.

    Global thresholds apply to all test categories unless a category-specific
    override is provided via ``category_thresholds``.  Health checks are
    typically much faster than complex policy evaluations so per-category
    values allow accurate alerting without false positives.

    Example config YAML::

        performance_thresholds:
          max_response_time_ms: 500
          warning_threshold_ms: 100
          category_thresholds:
            health:
              max_response_time_ms: 50
              warning_threshold_ms: 20
            policy:
              max_response_time_ms: 1000
              warning_threshold_ms: 300
    """

    max_response_time_ms: int = 500
    warning_threshold_ms: int = 100
    # Per-category overrides: mapping of category name → (warning_ms, max_ms)
    category_thresholds: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def for_category(self, category_name: str) -> "PerformanceThresholds":
        """Return a thresholds object with category-specific values applied.

        Args:
            category_name: Name of the test category (e.g. "health", "policy")

        Returns:
            A new PerformanceThresholds with overridden values for the category,
            or ``self`` unchanged when no override is configured.
        """
        override = self.category_thresholds.get(category_name)
        if not override:
            return self
        return PerformanceThresholds(
            max_response_time_ms=override.get("max_response_time_ms", self.max_response_time_ms),
            warning_threshold_ms=override.get("warning_threshold_ms", self.warning_threshold_ms),
            # Do not propagate nested category_thresholds into the override
            category_thresholds={},
        )


@dataclass
class PolicyTest:
    """Definition of a policy test case."""

    name: str
    policy_path: str
    input: Dict[str, Any]
    expected_output: Dict[str, Any]
    expected_allow: Optional[bool] = None
    smoke: bool = False


@dataclass
class TestConfig:
    """Main configuration for OPA test framework."""

    # OPA instance configuration
    opa_url: str = "http://localhost:8181"
    auth_token: Optional[str] = None
    timeout_seconds: int = 10

    # Bundle configuration
    bundle_service_url: Optional[str] = None
    expected_bundle_revision: Optional[str] = None

    # Test configuration
    test_policies: List[PolicyTest] = field(default_factory=list)
    performance_thresholds: PerformanceThresholds = field(default_factory=PerformanceThresholds)

    # Reporting configuration
    report_format: str = "console"  # console, junit, json

    # Rego test configuration
    rego_test_paths: List[str] = field(default_factory=lambda: ["policies"])
    rego_coverage_enabled: bool = False

    def __post_init__(self) -> None:
        """Post-initialization validation and setup."""
        # Ensure performance_thresholds is an instance
        if isinstance(self.performance_thresholds, dict):
            thresholds_dict = dict(self.performance_thresholds)
            # category_thresholds is optional in YAML; default to empty dict
            thresholds_dict.setdefault("category_thresholds", {})
            self.performance_thresholds = PerformanceThresholds(**thresholds_dict)

        # Convert policy test dicts to PolicyTest objects
        converted_tests = []
        for test in self.test_policies:
            if isinstance(test, dict):
                converted_tests.append(PolicyTest(**test))
            else:
                converted_tests.append(test)
        self.test_policies = converted_tests


def _parse_env_int(var_name: str) -> Optional[int]:
    """
    Safely parse an integer from an environment variable.

    Args:
        var_name: Name of the environment variable

    Returns:
        Parsed integer value, or None if the variable is not set

    Raises:
        ConfigurationError: If the value cannot be parsed as an integer
    """
    value = os.environ.get(var_name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        raise ConfigurationError(
            f"Environment variable {var_name} must be a valid integer, got: '{value}'"
        )


def load_config(config_file: Optional[str] = None) -> TestConfig:
    """
    Load configuration from file and environment variables.

    Configuration precedence (highest to lowest):
    1. Environment variables
    2. Configuration file
    3. Default values

    Args:
        config_file: Path to YAML configuration file (optional)

    Returns:
        TestConfig object with merged configuration

    Raises:
        FileNotFoundError: If config_file is specified but doesn't exist
        ConfigurationError: If config file has invalid YAML or env vars are invalid
    """
    with _config_lock:
        # Start with empty config dict
        config_data: Dict[str, Any] = {}

        # Load from file if provided
        if config_file:
            logger.info("Loading configuration from %s", config_file)
            try:
                with open(config_file, "r") as f:
                    file_config = yaml.safe_load(f) or {}
                    config_data.update(file_config)
            except yaml.YAMLError as e:
                raise ConfigurationError(f"Invalid YAML in config file '{config_file}': {e}")
            except FileNotFoundError:
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
            except PermissionError:
                raise ConfigurationError(f"Permission denied reading config file '{config_file}'")
            except OSError as e:
                raise ConfigurationError(f"Unable to read config file '{config_file}': {e}")

        # Override with environment variables
        env_overrides = _load_from_env()
        config_data.update(env_overrides)
        if env_overrides:
            logger.debug("Applied environment variable overrides: %s", list(env_overrides.keys()))

        # Create TestConfig with merged data
        try:
            return TestConfig(**config_data)
        except TypeError as e:
            raise ConfigurationError(f"Invalid configuration: {e}")


def _load_from_env() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Supported environment variables:
    - OPA_URL: Base URL of OPA instance
    - OPA_AUTH_TOKEN: Bearer token for authentication
    - OPA_TIMEOUT: Request timeout in seconds
    - OPA_BUNDLE_SERVICE_URL: URL of bundle service
    - OPA_EXPECTED_BUNDLE_REVISION: Expected bundle revision
    - OPA_REPORT_FORMAT: Report format (console, junit, json)
    - OPA_MAX_RESPONSE_TIME_MS: Max response time threshold in ms
    - OPA_WARNING_THRESHOLD_MS: Warning threshold in ms

    Returns:
        Dictionary of configuration values from environment

    Raises:
        ConfigurationError: If environment variable values are invalid
    """
    env_config: Dict[str, Any] = {}

    if "OPA_URL" in os.environ:
        env_config["opa_url"] = os.environ["OPA_URL"]

    if "OPA_AUTH_TOKEN" in os.environ:
        env_config["auth_token"] = os.environ["OPA_AUTH_TOKEN"]

    timeout = _parse_env_int("OPA_TIMEOUT")
    if timeout is not None:
        if timeout <= 0:
            raise ConfigurationError(
                f"Environment variable OPA_TIMEOUT must be a positive integer, got: {timeout}"
            )
        env_config["timeout_seconds"] = timeout

    if "OPA_BUNDLE_SERVICE_URL" in os.environ:
        env_config["bundle_service_url"] = os.environ["OPA_BUNDLE_SERVICE_URL"]

    if "OPA_EXPECTED_BUNDLE_REVISION" in os.environ:
        env_config["expected_bundle_revision"] = os.environ["OPA_EXPECTED_BUNDLE_REVISION"]

    if "OPA_REPORT_FORMAT" in os.environ:
        env_config["report_format"] = os.environ["OPA_REPORT_FORMAT"]

    # Performance thresholds
    max_response = _parse_env_int("OPA_MAX_RESPONSE_TIME_MS")
    warning_threshold = _parse_env_int("OPA_WARNING_THRESHOLD_MS")
    if max_response is not None or warning_threshold is not None:
        thresholds: Dict[str, int] = {}
        if max_response is not None:
            thresholds["max_response_time_ms"] = max_response
        if warning_threshold is not None:
            thresholds["warning_threshold_ms"] = warning_threshold
        env_config["performance_thresholds"] = thresholds

    return env_config


def _validate_url(url: str, field_name: str) -> List[str]:
    """Validate a URL and return any errors."""
    errors: List[str] = []
    if not url:
        errors.append(f"{field_name} is required")
        return errors

    if not (url.startswith("http://") or url.startswith("https://")):
        errors.append(f"{field_name} must start with http:// or https://: {url}")
        return errors

    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            errors.append(f"{field_name} has no hostname: {url}")
        if parsed.port is not None and (parsed.port < 1 or parsed.port > 65535):
            errors.append(f"{field_name} has invalid port number: {parsed.port}")
    except ValueError:
        errors.append(f"{field_name} is not a valid URL: {url}")

    return errors


def validate_config(config: TestConfig) -> List[str]:
    """
    Validate configuration and return list of errors.

    Args:
        config: TestConfig to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: List[str] = []

    # Validate OPA URL
    errors.extend(_validate_url(config.opa_url, "opa_url"))

    # Validate bundle service URL if provided
    if config.bundle_service_url:
        errors.extend(_validate_url(config.bundle_service_url, "bundle_service_url"))

    # Validate timeout
    if config.timeout_seconds <= 0:
        errors.append(f"timeout_seconds must be positive: {config.timeout_seconds}")
    elif config.timeout_seconds > 300:
        errors.append(f"timeout_seconds is too large (max 300): {config.timeout_seconds}")

    # Validate report format
    valid_formats = ["console", "junit", "json"]
    if config.report_format not in valid_formats:
        errors.append(f"report_format must be one of {valid_formats}: {config.report_format}")

    # Validate performance thresholds
    if config.performance_thresholds.max_response_time_ms <= 0:
        errors.append(
            f"max_response_time_ms must be positive: "
            f"{config.performance_thresholds.max_response_time_ms}"
        )

    if config.performance_thresholds.warning_threshold_ms <= 0:
        errors.append(
            f"warning_threshold_ms must be positive: "
            f"{config.performance_thresholds.warning_threshold_ms}"
        )

    if (
        config.performance_thresholds.warning_threshold_ms
        >= config.performance_thresholds.max_response_time_ms
    ):
        errors.append("warning_threshold_ms must be less than max_response_time_ms")

    # Validate per-category threshold overrides
    for cat_name, cat_thresholds in config.performance_thresholds.category_thresholds.items():
        cat_max = cat_thresholds.get("max_response_time_ms")
        cat_warn = cat_thresholds.get("warning_threshold_ms")
        if cat_max is not None and cat_max <= 0:
            errors.append(f"category_thresholds[{cat_name}].max_response_time_ms must be positive")
        if cat_warn is not None and cat_warn <= 0:
            errors.append(f"category_thresholds[{cat_name}].warning_threshold_ms must be positive")
        if cat_max is not None and cat_warn is not None and cat_warn >= cat_max:
            errors.append(
                f"category_thresholds[{cat_name}].warning_threshold_ms "
                f"must be less than max_response_time_ms"
            )

    # Validate policy tests
    for i, test in enumerate(config.test_policies):
        if not test.name:
            errors.append(f"Policy test {i} is missing name")
        if not test.policy_path:
            errors.append(f"Policy test '{test.name}' is missing policy_path")
        if test.input is None:
            errors.append(f"Policy test '{test.name}' is missing input")
        if test.expected_output is None:
            errors.append(f"Policy test '{test.name}' is missing expected_output")

    return errors
