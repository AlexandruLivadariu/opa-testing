"""
Base classes for test categories and tests.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..client import OPAClient
from ..config import TestConfig
from ..models import TestResult, TestStatus


class Test(ABC):
    """Base class for individual tests."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        """
        Execute the test.

        Args:
            client: OPAClient instance
            config: Test configuration

        Returns:
            TestResult with test outcome
        """
        pass

    def _create_result(
        self,
        status: TestStatus,
        duration_ms: float,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> TestResult:
        """
        Helper to create a TestResult.

        Args:
            status: Test status
            duration_ms: Test duration in milliseconds
            message: Optional message
            details: Optional details dictionary

        Returns:
            TestResult object
        """
        return TestResult(
            test_name=self.name,
            status=status,
            duration_ms=duration_ms,
            message=message,
            details=details or {},
        )


class TestCategory(ABC):
    """Base class for test categories."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def get_tests(self) -> List[Test]:
        """
        Get all tests in this category.

        Returns:
            List of Test objects
        """
        pass

    @abstractmethod
    def is_smoke_test(self) -> bool:
        """
        Check if this category contains smoke tests.

        Returns:
            True if this is a smoke test category
        """
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """
        Get execution priority (lower number = higher priority).

        Returns:
            Priority value (0-100)
        """
        pass

    def execute_all(self, client: OPAClient, config: TestConfig) -> List[TestResult]:
        """
        Execute all tests in this category.

        Args:
            client: OPAClient instance
            config: Test configuration

        Returns:
            List of TestResult objects
        """
        results = []
        for test in self.get_tests():
            result = test.execute(client, config)
            results.append(result)
        return results
