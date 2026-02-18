"""
Command-line interface for OPA test framework.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .client import OPAClient
from .config import ConfigurationError, TestConfig, load_config, validate_config
from .exceptions import OPAConnectionError, OPAHTTPError, OPATimeoutError
from .reporting import ConsoleReporter, JSONReporter, JUnitReporter
from .runner import TestRunner

logger = logging.getLogger(__name__)


def _run_dry_run(test_config: TestConfig) -> None:
    """Validate config and OPA connectivity without running any tests.

    Prints a summary of what *would* be tested, probes the OPA health
    endpoint, and exits 0 on success or 1 on any failure.
    """
    click.echo("Dry-run mode: validating configuration and connectivity only.")
    click.echo(f"  OPA URL      : {test_config.opa_url}")
    click.echo(f"  Timeout      : {test_config.timeout_seconds}s")
    click.echo(f"  Auth token   : {'set' if test_config.auth_token else 'not set'}")
    click.echo(f"  Report format: {test_config.report_format}")
    click.echo(f"  Policy tests : {len(test_config.test_policies)} configured")

    click.echo("\nProbing OPA health endpoint...")
    try:
        with OPAClient(
            base_url=test_config.opa_url,
            timeout=test_config.timeout_seconds,
            auth_token=test_config.auth_token,
        ) as client:
            health = client.health()
        click.echo(f"  OPA reachable — status: {health.status}")
        click.echo("\nDry-run passed. Configuration is valid and OPA is reachable.")
        sys.exit(0)
    except OPAConnectionError as e:
        click.echo(f"  Connection failed: {e}", err=True)
        click.echo(
            "\nDry-run failed: could not connect to OPA. "
            "Check opa_url and network connectivity.",
            err=True,
        )
        sys.exit(1)
    except OPATimeoutError as e:
        click.echo(f"  Request timed out: {e}", err=True)
        click.echo(
            "\nDry-run failed: OPA did not respond within the configured timeout.",
            err=True,
        )
        sys.exit(1)
    except OPAHTTPError as e:
        click.echo(f"  OPA returned HTTP {e.status_code}: {e}", err=True)
        click.echo(
            "\nDry-run failed: OPA responded with an error status.",
            err=True,
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"  Unexpected error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["smoke", "full", "category"]),
    default="full",
    help="Test execution mode",
)
@click.option(
    "--category",
    type=str,
    help="Category name (required when mode=category)",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to configuration file (YAML)",
)
@click.option(
    "--ci",
    is_flag=True,
    help="Enable CI mode (exit codes, report generation)",
)
@click.option(
    "--report-format",
    type=click.Choice(["console", "junit", "json"]),
    help="Report format (overrides config)",
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file for report (default: stdout)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help=(
        "Validate configuration and probe OPA connectivity without running any tests. "
        "Exits 0 if OPA is reachable and the config is valid, 1 otherwise. "
        "Useful for pre-flight checks in CI pipelines."
    ),
)
def main(
    mode: str,
    category: Optional[str],
    config: Optional[str],
    ci: bool,
    report_format: Optional[str],
    output: Optional[str],
    log_level: str,
    dry_run: bool,
) -> None:
    """
    OPA Test Framework - Automated testing for Open Policy Agent deployments.

    Examples:

      # Validate config and connectivity only (no tests run)
      opa-test --dry-run --config config.yaml

      # Run smoke tests
      opa-test --mode smoke --config config.yaml

      # Run full test suite
      opa-test --mode full --config config.yaml

      # Run specific category
      opa-test --mode category --category health --config config.yaml

      # CI mode with JUnit output
      opa-test --ci --mode smoke --report-format junit --output results.xml
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    try:
        # Load configuration
        logger.info("Loading configuration...")
        test_config = load_config(config)

        # Override report format if specified
        if report_format:
            test_config.report_format = report_format

        # Validate configuration
        errors = validate_config(test_config)
        if errors:
            click.echo("Configuration errors:", err=True)
            for error in errors:
                click.echo(f"  - {error}", err=True)
            sys.exit(1)

        # --dry-run: validate config + connectivity, then exit without running tests
        if dry_run:
            _run_dry_run(test_config)
            return  # _run_dry_run calls sys.exit internally

        # Create test runner
        runner = TestRunner(test_config)

        # Execute tests based on mode
        if mode == "smoke":
            logger.info("Running smoke tests...")
            click.echo("Running smoke tests...")
            summary = runner.run_smoke_tests()
        elif mode == "category":
            if not category:
                click.echo("Error: --category is required when mode=category", err=True)
                sys.exit(1)
            logger.info("Running tests for category: %s", category)
            click.echo(f"Running tests for category: {category}")
            try:
                summary = runner.run_category(category)
            except ValueError as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
        else:  # full
            logger.info("Running full test suite...")
            click.echo("Running full test suite...")
            summary = runner.run_full_tests()

        # Generate report
        if test_config.report_format == "junit":
            reporter = JUnitReporter()
        elif test_config.report_format == "json":
            reporter = JSONReporter()
        else:
            reporter = ConsoleReporter()

        report = reporter.generate(summary)

        # Output report
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report)
            click.echo(f"Report written to: {output}")
            # Also print summary to console
            if test_config.report_format != "console":
                console_reporter = ConsoleReporter()
                click.echo(console_reporter.generate(summary))
        else:
            click.echo(report)

        logger.info(
            "Tests complete: %d passed, %d failed, %d errors",
            summary.passed,
            summary.failed,
            summary.errors,
        )

        # Always exit with appropriate code based on test results
        sys.exit(0 if summary.success else 1)

    except ConfigurationError as e:
        logger.error("Configuration error: %s", e)
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
