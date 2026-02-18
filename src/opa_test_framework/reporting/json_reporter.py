"""
JSON reporter for test results.
"""

import json

from ..models import TestResultsSummary
from .base import ReportGenerator


class JSONReporter(ReportGenerator):
    """Generate JSON format for programmatic analysis."""

    def generate(self, summary: TestResultsSummary) -> str:
        """Generate JSON report."""
        report = {
            "summary": {
                "total_tests": summary.total_tests,
                "passed": summary.passed,
                "failed": summary.failed,
                "skipped": summary.skipped,
                "errors": summary.errors,
                "duration_seconds": summary.duration_seconds,
                "success": summary.success,
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "message": r.message,
                    "details": r.details,
                }
                for r in summary.results
            ],
        }

        return json.dumps(report, indent=2)
