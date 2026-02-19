"""
Console reporter for test results.
"""

import os
import sys

from ..models import TestResultsSummary, TestStatus
from .base import ReportGenerator


def _supports_color() -> bool:
    """Return True if the output stream likely supports ANSI colours."""
    # Explicit opt-in / opt-out via environment variable
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    # Non-TTY output (e.g. piped to a file) should not use colour
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    # Windows: enable ANSI processing via the virtual terminal flag.
    # This works on Windows 10 1607+ and Windows Terminal.
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            # STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(-11)
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            return False
    return True


class ConsoleReporter(ReportGenerator):
    """Generate colored console output for test results."""

    def __init__(self) -> None:
        color = _supports_color()
        self.GREEN = "\033[92m" if color else ""
        self.RED = "\033[91m" if color else ""
        self.YELLOW = "\033[93m" if color else ""
        self.BLUE = "\033[94m" if color else ""
        self.RESET = "\033[0m" if color else ""
        self.BOLD = "\033[1m" if color else ""

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
