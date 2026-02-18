"""
Data models for OPA test framework.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TestStatus(Enum):
    """Status of a test execution."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class HealthResponse:
    """Response from OPA health endpoint."""

    status: str
    uptime_seconds: Optional[int] = None
    bundle_status: Optional[Dict[str, Any]] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class BundleStatus:
    """Status of a policy bundle in OPA."""

    name: str
    active_revision: str
    last_successful_download: Optional[str] = None
    last_successful_activation: Optional[str] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class PolicyDecision:
    """Result from evaluating a policy."""

    result: Any
    decision_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class TestResult:
    """Result of a single test execution."""

    test_name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResultsSummary:
    """Aggregated summary of test results."""

    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_seconds: float
    results: List[TestResult]

    @property
    def success(self) -> bool:
        """Return True if all tests passed or were skipped."""
        return self.failed == 0 and self.errors == 0
