"""Extended configuration tests covering per-category thresholds and thread safety."""

import threading
import tempfile
import os

import pytest
import yaml

from src.opa_test_framework.config import (
    PerformanceThresholds,
    TestConfig,
    load_config,
    validate_config,
)


class TestPerCategoryThresholds:
    """Tests for PerformanceThresholds.for_category (issue #6 fix)."""

    def test_returns_self_when_no_override(self):
        thresholds = PerformanceThresholds(max_response_time_ms=500, warning_threshold_ms=100)
        result = thresholds.for_category("health")
        assert result.max_response_time_ms == 500
        assert result.warning_threshold_ms == 100

    def test_returns_overridden_values_for_matching_category(self):
        thresholds = PerformanceThresholds(
            max_response_time_ms=500,
            warning_threshold_ms=100,
            category_thresholds={
                "health": {"max_response_time_ms": 50, "warning_threshold_ms": 20}
            },
        )
        result = thresholds.for_category("health")
        assert result.max_response_time_ms == 50
        assert result.warning_threshold_ms == 20

    def test_partial_override_falls_back_to_global(self):
        """If only one field is overridden, the other keeps the global value."""
        thresholds = PerformanceThresholds(
            max_response_time_ms=500,
            warning_threshold_ms=100,
            category_thresholds={"policy": {"max_response_time_ms": 1000}},
        )
        result = thresholds.for_category("policy")
        assert result.max_response_time_ms == 1000
        assert result.warning_threshold_ms == 100  # falls back to global

    def test_override_for_different_category_not_applied(self):
        thresholds = PerformanceThresholds(
            max_response_time_ms=500,
            warning_threshold_ms=100,
            category_thresholds={
                "health": {"max_response_time_ms": 50, "warning_threshold_ms": 20}
            },
        )
        result = thresholds.for_category("bundle")
        # bundle has no override — should return global values
        assert result.max_response_time_ms == 500
        assert result.warning_threshold_ms == 100

    def test_override_does_not_propagate_nested_thresholds(self):
        """The override object must not have nested category_thresholds."""
        thresholds = PerformanceThresholds(
            max_response_time_ms=500,
            warning_threshold_ms=100,
            category_thresholds={
                "health": {"max_response_time_ms": 50, "warning_threshold_ms": 20}
            },
        )
        result = thresholds.for_category("health")
        assert result.category_thresholds == {}

    def test_multiple_category_overrides(self):
        thresholds = PerformanceThresholds(
            max_response_time_ms=500,
            warning_threshold_ms=100,
            category_thresholds={
                "health": {"max_response_time_ms": 50, "warning_threshold_ms": 20},
                "policy": {"max_response_time_ms": 2000, "warning_threshold_ms": 500},
            },
        )
        health = thresholds.for_category("health")
        policy = thresholds.for_category("policy")
        assert health.max_response_time_ms == 50
        assert policy.max_response_time_ms == 2000

    def test_category_thresholds_loaded_from_yaml(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "opa_url": "http://localhost:8181",
                    "performance_thresholds": {
                        "max_response_time_ms": 500,
                        "warning_threshold_ms": 100,
                        "category_thresholds": {
                            "health": {
                                "max_response_time_ms": 50,
                                "warning_threshold_ms": 20,
                            }
                        },
                    },
                }
            )
        )
        config = load_config(str(config_file))
        health_thresholds = config.performance_thresholds.for_category("health")
        assert health_thresholds.max_response_time_ms == 50
        assert health_thresholds.warning_threshold_ms == 20


class TestCategoryThresholdValidation:
    """Tests for validate_config with per-category threshold rules."""

    def test_valid_category_thresholds_no_errors(self):
        config = TestConfig(
            performance_thresholds=PerformanceThresholds(
                max_response_time_ms=500,
                warning_threshold_ms=100,
                category_thresholds={
                    "health": {"max_response_time_ms": 50, "warning_threshold_ms": 20}
                },
            )
        )
        errors = validate_config(config)
        assert errors == []

    def test_invalid_category_max_response_time(self):
        config = TestConfig(
            performance_thresholds=PerformanceThresholds(
                max_response_time_ms=500,
                warning_threshold_ms=100,
                category_thresholds={
                    "health": {"max_response_time_ms": -1, "warning_threshold_ms": 20}
                },
            )
        )
        errors = validate_config(config)
        assert any("health" in e and "max_response_time_ms" in e for e in errors)

    def test_invalid_category_warning_threshold(self):
        config = TestConfig(
            performance_thresholds=PerformanceThresholds(
                max_response_time_ms=500,
                warning_threshold_ms=100,
                category_thresholds={
                    "health": {"max_response_time_ms": 50, "warning_threshold_ms": 0}
                },
            )
        )
        errors = validate_config(config)
        assert any("health" in e and "warning_threshold_ms" in e for e in errors)

    def test_category_warning_gte_max_fails(self):
        config = TestConfig(
            performance_thresholds=PerformanceThresholds(
                max_response_time_ms=500,
                warning_threshold_ms=100,
                category_thresholds={
                    "health": {"max_response_time_ms": 50, "warning_threshold_ms": 100}
                },
            )
        )
        errors = validate_config(config)
        assert any("health" in e for e in errors)


class TestThreadSafeConfigLoading:
    """Tests for thread-safe config loading (issue #1 fix)."""

    def test_concurrent_load_config_calls_all_succeed(self, tmp_path):
        """Simulate multiple threads loading config simultaneously."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump({"opa_url": "http://localhost:8181", "timeout_seconds": 15})
        )

        results = []
        errors = []

        def load():
            try:
                cfg = load_config(str(config_file))
                results.append(cfg.timeout_seconds)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=load) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during concurrent load: {errors}"
        assert all(v == 15 for v in results), f"Inconsistent results: {results}"

    def test_concurrent_load_with_env_override(self, monkeypatch, tmp_path):
        """Env overrides should be consistent across concurrent loads."""
        monkeypatch.setenv("OPA_TIMEOUT", "25")
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"opa_url": "http://localhost:8181"}))

        results = []

        def load():
            cfg = load_config(str(config_file))
            results.append(cfg.timeout_seconds)

        threads = [threading.Thread(target=load) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(v == 25 for v in results)
