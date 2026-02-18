"""
Test result aggregation and utilities.
"""

from typing import List

from .models import TestResult, TestResultsSummary, TestStatus


def aggregate_results(results: List[TestResult]) -> TestResultsSummary:
    """
    Aggregate individual test results into a summary.

    Args:
        results: List of TestResult objects

    Returns:
        TestResultsSummary with aggregated statistics
    """
    total_tests = len(results)
    passed = sum(1 for r in results if r.status == TestStatus.PASS)
    failed = sum(1 for r in results if r.status == TestStatus.FAIL)
    skipped = sum(1 for r in results if r.status == TestStatus.SKIP)
    errors = sum(1 for r in results if r.status == TestStatus.ERROR)

    # Calculate total duration in seconds
    total_duration_ms = sum(r.duration_ms for r in results)
    duration_seconds = total_duration_ms / 1000.0

    return TestResultsSummary(
        total_tests=total_tests,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        duration_seconds=duration_seconds,
        results=results,
    )
