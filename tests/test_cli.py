"""Tests for CLI interface."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.opa_test_framework.cli import _run_dry_run, main
from src.opa_test_framework.exceptions import (
    OPAConnectionError,
    OPAHTTPError,
    OPATimeoutError,
)
from src.opa_test_framework.models import TestResult, TestResultsSummary, TestStatus


def _passing_summary(n=1):
    return TestResultsSummary(
        total_tests=n,
        passed=n,
        failed=0,
        skipped=0,
        errors=0,
        duration_seconds=0.1,
        results=[TestResult(f"t{i}", TestStatus.PASS, 10.0, "ok") for i in range(n)],
    )


def _failing_summary():
    return TestResultsSummary(
        total_tests=1,
        passed=0,
        failed=1,
        skipped=0,
        errors=0,
        duration_seconds=0.1,
        results=[TestResult("t1", TestStatus.FAIL, 100.0, "failed")],
    )


class TestCLI:
    """Tests for CLI commands."""

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "OPA Test Framework" in result.output
        assert "--mode" in result.output
        assert "--config" in result.output

    def test_help_shows_dry_run(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "--dry-run" in result.output

    def test_invalid_mode(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--mode", "invalid"])
        assert result.exit_code != 0

    def test_category_mode_without_category(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_load.return_value = MagicMock(report_format="console")
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                result = runner.invoke(main, ["--mode", "category"])
                assert result.exit_code == 1
                assert "--category is required" in result.output

    def test_config_validation_errors(self, tmp_path):
        config_file = tmp_path / "bad_config.yaml"
        config_file.write_text("opa_url: not-a-url\ntimeout_seconds: -1\n")
        runner = CliRunner()
        result = runner.invoke(main, ["--config", str(config_file)])
        assert result.exit_code == 1
        assert "Configuration errors" in result.output

    def test_exit_code_on_failure(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(report_format="console")
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                    MockRunner.return_value.run_full_tests.return_value = _failing_summary()
                    result = runner.invoke(main, ["--mode", "full"])
                    assert result.exit_code == 1

    def test_exit_code_on_success(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(report_format="console")
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                    MockRunner.return_value.run_full_tests.return_value = _passing_summary()
                    result = runner.invoke(main, ["--mode", "full"])
                    assert result.exit_code == 0

    def test_output_to_file(self, tmp_path):
        output_file = tmp_path / "report.json"
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(report_format="json")
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                    MockRunner.return_value.run_full_tests.return_value = _passing_summary()
                    result = runner.invoke(
                        main,
                        ["--mode", "full", "--report-format", "json", "--output", str(output_file)],
                    )
                    assert result.exit_code == 0
                    assert output_file.exists()

    def test_smoke_mode(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(report_format="console")
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                    MockRunner.return_value.run_smoke_tests.return_value = _passing_summary()
                    result = runner.invoke(main, ["--mode", "smoke"])
                    assert result.exit_code == 0
                    MockRunner.return_value.run_smoke_tests.assert_called_once()

    def test_category_mode_success(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(report_format="console")
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                    MockRunner.return_value.run_category.return_value = _passing_summary()
                    result = runner.invoke(main, ["--mode", "category", "--category", "health"])
                    assert result.exit_code == 0
                    MockRunner.return_value.run_category.assert_called_once_with("health")

    def test_category_mode_invalid_name(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(report_format="console")
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                    MockRunner.return_value.run_category.side_effect = ValueError("not found")
                    result = runner.invoke(main, ["--mode", "category", "--category", "bogus"])
                    assert result.exit_code == 1

    def test_junit_report_format(self, tmp_path):
        output_file = tmp_path / "results.xml"
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(report_format="junit")
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                    MockRunner.return_value.run_full_tests.return_value = _passing_summary()
                    result = runner.invoke(
                        main,
                        ["--report-format", "junit", "--output", str(output_file)],
                    )
                    assert result.exit_code == 0
                    assert output_file.exists()

    def test_report_format_override(self):
        """--report-format flag overrides config file format."""
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(report_format="console")
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                    MockRunner.return_value.run_full_tests.return_value = _passing_summary()
                    runner.invoke(main, ["--report-format", "json"])
                    # The config object's report_format must have been updated
                    assert mock_config.report_format == "json"


class TestDryRun:
    """Tests for --dry-run flag."""

    def test_dry_run_flag_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "--dry-run" in result.output

    def test_dry_run_success(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(
                report_format="console",
                opa_url="http://localhost:8181",
                timeout_seconds=10,
                auth_token=None,
                test_policies=[],
            )
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.OPAClient") as MockClient:
                    mock_health = MagicMock(status="ok")
                    MockClient.return_value.__enter__ = MagicMock(
                        return_value=MockClient.return_value
                    )
                    MockClient.return_value.__exit__ = MagicMock(return_value=False)
                    MockClient.return_value.health.return_value = mock_health
                    result = runner.invoke(main, ["--dry-run"])
                    assert result.exit_code == 0
                    assert "Dry-run passed" in result.output

    def test_dry_run_shows_config_summary(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(
                report_format="console",
                opa_url="http://opa-test:8181",
                timeout_seconds=30,
                auth_token="secret",
                test_policies=["p1", "p2"],
            )
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.OPAClient") as MockClient:
                    MockClient.return_value.__enter__ = MagicMock(
                        return_value=MockClient.return_value
                    )
                    MockClient.return_value.__exit__ = MagicMock(return_value=False)
                    MockClient.return_value.health.return_value = MagicMock(status="ok")
                    result = runner.invoke(main, ["--dry-run"])
                    assert "http://opa-test:8181" in result.output
                    assert "30s" in result.output
                    assert "set" in result.output  # auth token masked as 'set'
                    assert "2" in result.output  # 2 policy tests

    def test_dry_run_connection_error_exits_1(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(
                report_format="console",
                opa_url="http://localhost:8181",
                timeout_seconds=10,
                auth_token=None,
                test_policies=[],
            )
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.OPAClient") as MockClient:
                    MockClient.return_value.__enter__ = MagicMock(
                        return_value=MockClient.return_value
                    )
                    MockClient.return_value.__exit__ = MagicMock(return_value=False)
                    import requests

                    MockClient.return_value.health.side_effect = OPAConnectionError(
                        "http://localhost:8181", Exception("refused")
                    )
                    result = runner.invoke(main, ["--dry-run"])
                    assert result.exit_code == 1
                    assert "failed" in result.output.lower()

    def test_dry_run_timeout_exits_1(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(
                report_format="console",
                opa_url="http://localhost:8181",
                timeout_seconds=10,
                auth_token=None,
                test_policies=[],
            )
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.OPAClient") as MockClient:
                    MockClient.return_value.__enter__ = MagicMock(
                        return_value=MockClient.return_value
                    )
                    MockClient.return_value.__exit__ = MagicMock(return_value=False)
                    MockClient.return_value.health.side_effect = OPATimeoutError(
                        "http://localhost:8181", 10
                    )
                    result = runner.invoke(main, ["--dry-run"])
                    assert result.exit_code == 1

    def test_dry_run_http_error_exits_1(self):
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(
                report_format="console",
                opa_url="http://localhost:8181",
                timeout_seconds=10,
                auth_token=None,
                test_policies=[],
            )
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.OPAClient") as MockClient:
                    MockClient.return_value.__enter__ = MagicMock(
                        return_value=MockClient.return_value
                    )
                    MockClient.return_value.__exit__ = MagicMock(return_value=False)
                    MockClient.return_value.health.side_effect = OPAHTTPError(
                        500, "http://localhost:8181", "internal error"
                    )
                    result = runner.invoke(main, ["--dry-run"])
                    assert result.exit_code == 1

    def test_dry_run_does_not_run_tests(self):
        """Dry-run must never invoke the test runner."""
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_config = MagicMock(
                report_format="console",
                opa_url="http://localhost:8181",
                timeout_seconds=10,
                auth_token=None,
                test_policies=[],
            )
            mock_load.return_value = mock_config
            with patch("src.opa_test_framework.cli.validate_config", return_value=[]):
                with patch("src.opa_test_framework.cli.OPAClient") as MockClient:
                    MockClient.return_value.__enter__ = MagicMock(
                        return_value=MockClient.return_value
                    )
                    MockClient.return_value.__exit__ = MagicMock(return_value=False)
                    MockClient.return_value.health.return_value = MagicMock(status="ok")
                    with patch("src.opa_test_framework.cli.TestRunner") as MockRunner:
                        runner.invoke(main, ["--dry-run"])
                        MockRunner.assert_not_called()

    def test_dry_run_config_validation_error_exits_before_probe(self):
        """Dry-run exits on config errors without probing OPA."""
        runner = CliRunner()
        with patch("src.opa_test_framework.cli.load_config") as mock_load:
            mock_load.return_value = MagicMock(report_format="console")
            with patch(
                "src.opa_test_framework.cli.validate_config",
                return_value=["opa_url is required"],
            ):
                with patch("src.opa_test_framework.cli.OPAClient") as MockClient:
                    result = runner.invoke(main, ["--dry-run"])
                    assert result.exit_code == 1
                    MockClient.assert_not_called()
