"""Tests for report generators."""

import json
import xml.etree.ElementTree as ET


from src.opa_test_framework.models import TestResult, TestStatus
from src.opa_test_framework.reporting import ConsoleReporter, JSONReporter, JUnitReporter
from src.opa_test_framework.results import aggregate_results


def _make_summary(results=None):
    """Helper to create a test summary."""
    if results is None:
        results = [
            TestResult("health_check", TestStatus.PASS, 45.0, "Health OK"),
            TestResult("bundle_status", TestStatus.PASS, 30.0, "Bundle loaded"),
            TestResult(
                "policy_test",
                TestStatus.FAIL,
                120.0,
                "Decision mismatch",
                {"expected": {"allow": True}, "actual": {"allow": False}},
            ),
            TestResult("skipped_test", TestStatus.SKIP, 1.0, "No config"),
        ]
    return aggregate_results(results)


class TestConsoleReporter:
    """Tests for ConsoleReporter."""

    def test_generates_output(self):
        reporter = ConsoleReporter()
        report = reporter.generate(_make_summary())
        assert isinstance(report, str)
        assert len(report) > 0

    def test_contains_header(self):
        report = ConsoleReporter().generate(_make_summary())
        assert "OPA Test Results" in report

    def test_contains_summary_stats(self):
        report = ConsoleReporter().generate(_make_summary())
        assert "Total Tests: 4" in report
        assert "Passed: 1" in report or "Passed:" in report

    def test_contains_test_names(self):
        report = ConsoleReporter().generate(_make_summary())
        assert "health_check" in report
        assert "policy_test" in report

    def test_shows_failure_details(self):
        report = ConsoleReporter().generate(_make_summary())
        assert "Decision mismatch" in report

    def test_all_pass_message(self):
        results = [TestResult("t1", TestStatus.PASS, 10.0, "ok")]
        report = ConsoleReporter().generate(aggregate_results(results))
        assert "ALL TESTS PASSED" in report

    def test_failure_message(self):
        report = ConsoleReporter().generate(_make_summary())
        assert "TESTS FAILED" in report

    def test_empty_results(self):
        report = ConsoleReporter().generate(aggregate_results([]))
        assert "Total Tests: 0" in report


class TestJUnitReporter:
    """Tests for JUnitReporter."""

    def test_generates_valid_xml(self):
        reporter = JUnitReporter()
        report = reporter.generate(_make_summary())
        # Should be valid XML
        ET.fromstring(report.split("?>")[1] if "?>" in report else report)

    def test_testsuite_attributes(self):
        reporter = JUnitReporter()
        report = reporter.generate(_make_summary())
        # Parse the XML (skip the XML declaration)
        xml_body = report.split("?>")[1] if "?>" in report else report
        root = ET.fromstring(xml_body)
        assert root.tag == "testsuite"
        assert root.get("name") == "OPA Tests"
        assert root.get("tests") == "4"
        assert root.get("failures") == "1"

    def test_testcase_elements(self):
        reporter = JUnitReporter()
        report = reporter.generate(_make_summary())
        xml_body = report.split("?>")[1] if "?>" in report else report
        root = ET.fromstring(xml_body)
        testcases = root.findall("testcase")
        assert len(testcases) == 4

    def test_failure_element(self):
        reporter = JUnitReporter()
        report = reporter.generate(_make_summary())
        xml_body = report.split("?>")[1] if "?>" in report else report
        root = ET.fromstring(xml_body)
        failures = root.findall(".//failure")
        assert len(failures) == 1
        assert failures[0].get("message") == "Decision mismatch"

    def test_skipped_element(self):
        reporter = JUnitReporter()
        report = reporter.generate(_make_summary())
        xml_body = report.split("?>")[1] if "?>" in report else report
        root = ET.fromstring(xml_body)
        skipped = root.findall(".//skipped")
        assert len(skipped) == 1

    def test_empty_results(self):
        reporter = JUnitReporter()
        report = reporter.generate(aggregate_results([]))
        xml_body = report.split("?>")[1] if "?>" in report else report
        root = ET.fromstring(xml_body)
        assert root.get("tests") == "0"


class TestJSONReporter:
    """Tests for JSONReporter."""

    def test_generates_valid_json(self):
        reporter = JSONReporter()
        report = reporter.generate(_make_summary())
        data = json.loads(report)
        assert isinstance(data, dict)

    def test_summary_fields(self):
        reporter = JSONReporter()
        data = json.loads(reporter.generate(_make_summary()))
        summary = data["summary"]
        assert summary["total_tests"] == 4
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["skipped"] == 1
        assert summary["errors"] == 0
        assert summary["success"] is False

    def test_results_array(self):
        reporter = JSONReporter()
        data = json.loads(reporter.generate(_make_summary()))
        assert len(data["results"]) == 4
        result = data["results"][0]
        assert "test_name" in result
        assert "status" in result
        assert "duration_ms" in result
        assert "message" in result
        assert "details" in result

    def test_status_values_are_strings(self):
        reporter = JSONReporter()
        data = json.loads(reporter.generate(_make_summary()))
        statuses = [r["status"] for r in data["results"]]
        assert "pass" in statuses
        assert "fail" in statuses
        assert "skip" in statuses

    def test_empty_results(self):
        reporter = JSONReporter()
        data = json.loads(reporter.generate(aggregate_results([])))
        assert data["summary"]["total_tests"] == 0
        assert data["results"] == []
