"""Tests for data models."""

import pytest

from src.opa_test_framework.models import (
    BundleStatus,
    HealthResponse,
    PolicyDecision,
    TestResult,
    TestResultsSummary,
    TestStatus,
)


class TestTestStatus:
    """Tests for TestStatus enum."""

    def test_values(self):
        assert TestStatus.PASS.value == "pass"
        assert TestStatus.FAIL.value == "fail"
        assert TestStatus.SKIP.value == "skip"
        assert TestStatus.ERROR.value == "error"

    def test_all_statuses(self):
        assert len(TestStatus) == 4


class TestHealthResponse:
    """Tests for HealthResponse dataclass."""

    def test_minimal(self):
        hr = HealthResponse(status="ok")
        assert hr.status == "ok"
        assert hr.uptime_seconds is None
        assert hr.bundle_status is None
        assert hr.raw_response is None

    def test_full(self):
        hr = HealthResponse(
            status="ok",
            uptime_seconds=3600,
            bundle_status={"loaded": True},
            raw_response={"status": "ok"},
        )
        assert hr.uptime_seconds == 3600


class TestBundleStatus:
    """Tests for BundleStatus dataclass."""

    def test_defaults(self):
        bs = BundleStatus(name="test", active_revision="v1")
        assert bs.errors == []
        assert bs.last_successful_download is None

    def test_errors_not_shared_across_instances(self):
        bs1 = BundleStatus(name="test1", active_revision="v1")
        bs2 = BundleStatus(name="test2", active_revision="v2")
        bs1.errors.append("error1")
        assert bs2.errors == []


class TestPolicyDecision:
    """Tests for PolicyDecision dataclass."""

    def test_minimal(self):
        pd = PolicyDecision(result={"allow": True})
        assert pd.result == {"allow": True}
        assert pd.decision_id is None
        assert pd.metrics is None

    def test_with_metadata(self):
        pd = PolicyDecision(
            result=True,
            decision_id="abc-123",
            metrics={"timer_ns": 1000},
        )
        assert pd.decision_id == "abc-123"


class TestTestResult:
    """Tests for TestResult dataclass."""

    def test_defaults(self):
        tr = TestResult(
            test_name="test1",
            status=TestStatus.PASS,
            duration_ms=100.0,
        )
        assert tr.message == ""
        assert tr.details == {}

    def test_details_not_shared_across_instances(self):
        tr1 = TestResult(test_name="t1", status=TestStatus.PASS, duration_ms=1.0)
        tr2 = TestResult(test_name="t2", status=TestStatus.PASS, duration_ms=1.0)
        tr1.details["key"] = "value"
        assert tr2.details == {}


class TestTestResultsSummary:
    """Tests for TestResultsSummary dataclass."""

    def test_success_when_all_pass(self):
        summary = TestResultsSummary(
            total_tests=2,
            passed=2,
            failed=0,
            skipped=0,
            errors=0,
            duration_seconds=1.0,
            results=[],
        )
        assert summary.success is True

    def test_success_with_skips(self):
        summary = TestResultsSummary(
            total_tests=3,
            passed=2,
            failed=0,
            skipped=1,
            errors=0,
            duration_seconds=1.0,
            results=[],
        )
        assert summary.success is True

    def test_failure_when_tests_fail(self):
        summary = TestResultsSummary(
            total_tests=3,
            passed=2,
            failed=1,
            skipped=0,
            errors=0,
            duration_seconds=1.0,
            results=[],
        )
        assert summary.success is False

    def test_failure_when_errors(self):
        summary = TestResultsSummary(
            total_tests=3,
            passed=2,
            failed=0,
            skipped=0,
            errors=1,
            duration_seconds=1.0,
            results=[],
        )
        assert summary.success is False
