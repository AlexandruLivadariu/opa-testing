"""
JUnit XML reporter for test results.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

from ..models import TestResultsSummary, TestStatus
from .base import ReportGenerator


class JUnitReporter(ReportGenerator):
    """Generate JUnit XML format for CI/CD integration."""

    def generate(self, summary: TestResultsSummary) -> str:
        """Generate JUnit XML report."""
        # Create root testsuite element
        testsuite = ET.Element("testsuite")
        testsuite.set("name", "OPA Tests")
        testsuite.set("tests", str(summary.total_tests))
        testsuite.set("failures", str(summary.failed))
        testsuite.set("errors", str(summary.errors))
        testsuite.set("skipped", str(summary.skipped))
        testsuite.set("time", f"{summary.duration_seconds:.3f}")

        # Add each test case
        for result in summary.results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", result.test_name)
            testcase.set("time", f"{result.duration_ms / 1000:.3f}")

            if result.status == TestStatus.FAIL:
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", result.message)
                failure.text = str(result.details)

            elif result.status == TestStatus.ERROR:
                error = ET.SubElement(testcase, "error")
                error.set("message", result.message)
                error.text = str(result.details)

            elif result.status == TestStatus.SKIP:
                skipped = ET.SubElement(testcase, "skipped")
                skipped.set("message", result.message)

        # Convert to pretty-printed XML string
        xml_str = ET.tostring(testsuite, encoding="unicode")
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")
