"""
Console reporter for test results.
"""

from ..models import TestResultsSummary, TestStatus
from .base import ReportGenerator


class ConsoleReporter(ReportGenerator):
    """Generate colored console output for test results."""

    # ANSI color codes
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def generate(self, summary: TestResultsSummary) -> str:
        """Generate console report."""
        lines = []

        # Header
        lines.append(f"\n{self.BOLD}OPA Test Results{self.RESET}")
        lines.append("=" * 60)

        # Summary statistics
        lines.append(f"\n{self.BOLD}Summary:{self.RESET}")
        lines.append(f"  Total Tests: {summary.total_tests}")
        lines.append(f"  {self.GREEN}Passed: {summary.passed}{self.RESET}")
        lines.append(f"  {self.RED}Failed: {summary.failed}{self.RESET}")
        lines.append(f"  {self.YELLOW}Skipped: {summary.skipped}{self.RESET}")
        lines.append(f"  {self.RED}Errors: {summary.errors}{self.RESET}")
        lines.append(f"  Duration: {summary.duration_seconds:.2f}s")

        # Overall status
        if summary.success:
            lines.append(f"\n{self.GREEN}{self.BOLD}✓ ALL TESTS PASSED{self.RESET}")
        else:
            lines.append(f"\n{self.RED}{self.BOLD}✗ TESTS FAILED{self.RESET}")

        # Failed tests details
        failed_results = [
            r for r in summary.results if r.status in (TestStatus.FAIL, TestStatus.ERROR)
        ]

        if failed_results:
            lines.append(f"\n{self.BOLD}Failed Tests:{self.RESET}")
            for result in failed_results:
                status_color = self.RED
                status_symbol = "✗"
                lines.append(f"\n  {status_color}{status_symbol} {result.test_name}{self.RESET}")
                lines.append(f"    {result.message}")
                if result.details:
                    lines.append(f"    Details: {result.details}")
                lines.append(f"    Duration: {result.duration_ms:.2f}ms")

        # All tests summary (if not too many)
        if summary.total_tests <= 20:
            lines.append(f"\n{self.BOLD}All Tests:{self.RESET}")
            for result in summary.results:
                if result.status == TestStatus.PASS:
                    symbol = f"{self.GREEN}✓{self.RESET}"
                elif result.status == TestStatus.FAIL:
                    symbol = f"{self.RED}✗{self.RESET}"
                elif result.status == TestStatus.SKIP:
                    symbol = f"{self.YELLOW}○{self.RESET}"
                else:  # ERROR
                    symbol = f"{self.RED}✗{self.RESET}"

                lines.append(f"  {symbol} {result.test_name} ({result.duration_ms:.2f}ms)")

        lines.append("")  # Empty line at end
        return "\n".join(lines)
