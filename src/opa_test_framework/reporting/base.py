"""
Base class for report generators.
"""

from abc import ABC, abstractmethod

from ..models import TestResultsSummary


class ReportGenerator(ABC):
    """Base class for generating test reports."""

    @abstractmethod
    def generate(self, summary: TestResultsSummary) -> str:
        """
        Generate a report from test results.

        Args:
            summary: TestResultsSummary with test results

        Returns:
            Report as a string
        """
        pass
