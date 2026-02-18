"""Tests for result aggregation."""

import pytest

from src.opa_test_framework.models import TestResult, TestStatus
from src.opa_test_framework.results import aggregate_results


class TestAggregateResults:
    """Tests for aggregate_results function."""

    def test_empty_results(self):
        summary = aggregate_results([])
        assert summary.total_tests == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.skipped == 0
        assert summary.errors == 0
        assert summary.duration_seconds == 0.0
        assert summary.success is True

    def test_all_pass(self):
        results = [
            TestResult("t1", TestStatus.PASS, 100.0, "ok"),
            TestResult("t2", TestStatus.PASS, 200.0, "ok"),
        ]
        summary = aggregate_results(results)
        assert summary.total_tests == 2
        assert summary.passed == 2
        assert summary.failed == 0
        assert summary.success is True
        assert summary.duration_seconds == 0.3

    def test_mixed_results(self):
        results = [
            TestResult("t1", TestStatus.PASS, 100.0),
            TestResult("t2", TestStatus.FAIL, 150.0),
            TestResult("t3", TestStatus.SKIP, 10.0),
            TestResult("t4", TestStatus.ERROR, 50.0),
        ]
        summary = aggregate_results(results)
        assert summary.total_tests == 4
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.skipped == 1
        assert summary.errors == 1
        assert summary.success is False

    def test_all_skipped(self):
        results = [
            TestResult("t1", TestStatus.SKIP, 5.0),
            TestResult("t2", TestStatus.SKIP, 5.0),
        ]
        summary = aggregate_results(results)
        assert summary.total_tests == 2
        assert summary.skipped == 2
        assert summary.success is True

    def test_duration_calculation(self):
        results = [
            TestResult("t1", TestStatus.PASS, 500.0),
            TestResult("t2", TestStatus.PASS, 500.0),
        ]
        summary = aggregate_results(results)
        assert summary.duration_seconds == pytest.approx(1.0)

    def test_results_preserved(self):
        results = [
            TestResult("t1", TestStatus.PASS, 100.0, "msg1"),
        ]
        summary = aggregate_results(results)
        assert len(summary.results) == 1
        assert summary.results[0].test_name == "t1"
        assert summary.results[0].message == "msg1"
