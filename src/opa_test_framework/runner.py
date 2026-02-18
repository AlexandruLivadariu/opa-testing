"""
Test runner for executing OPA tests.
"""

import logging
from typing import List

from .categories.auth import AuthTests
from .categories.base import TestCategory
from .categories.bundle import BundleTests
from .categories.health import HealthTests
from .categories.policy import PolicyTests
from .client import OPAClient
from .config import TestConfig
from .models import TestResult, TestResultsSummary, TestStatus
from .results import aggregate_results

logger = logging.getLogger(__name__)


class TestRunner:
    """Orchestrates test execution across categories."""

    def __init__(self, config: TestConfig):
        self.config = config

    def _get_all_categories(self) -> List[TestCategory]:
        """Get all test categories."""
        categories = [
            HealthTests(),
            BundleTests(),
            AuthTests(),
        ]

        # Add policy tests if configured
        if self.config.test_policies:
            categories.append(PolicyTests(self.config))

        # Sort by priority
        categories.sort(key=lambda c: c.get_priority())
        return categories

    def _get_smoke_categories(self) -> List[TestCategory]:
        """Get only smoke test categories."""
        all_categories = self._get_all_categories()
        return [c for c in all_categories if c.is_smoke_test()]

    def run_smoke_tests(self) -> TestResultsSummary:
        """
        Run smoke tests only (fast, critical tests).

        Returns:
            TestResultsSummary with results
        """
        categories = self._get_smoke_categories()
        return self._run_categories(categories, fail_fast=True)

    def run_full_tests(self) -> TestResultsSummary:
        """
        Run all tests.

        Returns:
            TestResultsSummary with results
        """
        categories = self._get_all_categories()
        return self._run_categories(categories, fail_fast=False)

    def run_category(self, category_name: str) -> TestResultsSummary:
        """
        Run tests from a specific category.

        Args:
            category_name: Name of the category to run

        Returns:
            TestResultsSummary with results

        Raises:
            ValueError: If category name is not found
        """
        all_categories = self._get_all_categories()
        category = next((c for c in all_categories if c.name == category_name), None)

        if not category:
            available = [c.name for c in all_categories]
            raise ValueError(
                f"Category '{category_name}' not found. "
                f"Available categories: {', '.join(available)}"
            )

        return self._run_categories([category], fail_fast=False)

    def _run_categories(
        self, categories: List[TestCategory], fail_fast: bool = False
    ) -> TestResultsSummary:
        """
        Run tests from specified categories.

        Args:
            categories: List of TestCategory objects to run
            fail_fast: If True, stop on first failure

        Returns:
            TestResultsSummary with aggregated results
        """
        all_results: List[TestResult] = []

        logger.info(
            "Running %d test categories against %s",
            len(categories),
            self.config.opa_url,
        )

        # Create OPA client
        with OPAClient(
            base_url=self.config.opa_url,
            timeout=self.config.timeout_seconds,
            auth_token=self.config.auth_token,
        ) as client:
            for category in categories:
                logger.info("Executing category: %s", category.name)
                category_results = category.execute_all(client, self.config)
                all_results.extend(category_results)

                # Check for failures if fail_fast is enabled
                if fail_fast:
                    for result in category_results:
                        if result.status in (TestStatus.FAIL, TestStatus.ERROR):
                            # Stop immediately on failure
                            return aggregate_results(all_results)

        return aggregate_results(all_results)
