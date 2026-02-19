# Writing Tests

This guide covers how to add your own policy test cases to the configuration and how to create entirely new test categories when the built-in ones aren't enough.

---

## Adding Policy Test Cases (No Code Required)

The simplest way to extend the framework is to add entries under `test_policies` in your YAML config file. No Python code needed.

### Basic Example

```yaml
test_policies:
  - name: "test_admin_can_read"
    policy_path: "myapp/authorize"
    input:
      user: "alice"
      role: "admin"
      action: "read"
    expected_output: true

  - name: "test_guest_cannot_write"
    policy_path: "myapp/authorize"
    input:
      user: "bob"
      role: "guest"
      action: "write"
    expected_output: false
```

### How It Works

1. The framework sends a `POST` request to `http://<opa_url>/v1/data/<policy_path>` with the `input` as the JSON body.
2. OPA evaluates the policy and returns `{"result": <value>}`.
3. The framework compares `result` against `expected_output`.
4. If they match → **PASS**. If not → **FAIL** with details showing expected vs. actual.

### Matching Different Output Types

**Boolean rules** (most common):

```yaml
# Rego: default allow = false / allow { ... }
- name: "test_allow"
  policy_path: "example/allow"
  input: { role: "admin" }
  expected_output: true
```

**Set-generating rules** (returns an array):

```yaml
# Rego: permissions[action] { ... }
- name: "test_permissions"
  policy_path: "example/permissions"
  input: { user: "charlie", resource: "doc-1" }
  expected_output:
    - "read"
```

**Object rules** (returns a dict):

```yaml
# Rego: result := {"level": "admin", "actions": [...]}
- name: "test_structured"
  policy_path: "myapp/result"
  input: { user: "admin" }
  expected_output:
    level: "admin"
    actions: ["read", "write", "delete"]
```

### Smoke Policy Tests

Mark a policy test to run during smoke tests by adding `smoke: true`:

```yaml
- name: "test_critical_policy"
  policy_path: "core/authorize"
  input: { user: "healthcheck" }
  expected_output: true
  smoke: true     # ← included in smoke runs
```

---

## Writing Rego Policies

### Policy File Structure

Rego files live in `examples/policies/` (or wherever you configure). Each file must declare a `package`:

```rego
package myapp

default allow = false

allow {
    input.role == "admin"
}

allow {
    input.role == "user"
    input.action == "read"
}
```

### Rego Unit Tests

OPA has built-in unit testing. Create a `*_test.rego` file alongside your policy:

```rego
package myapp

test_admin_allowed {
    allow with input as {"role": "admin", "action": "write"}
}

test_user_read_allowed {
    allow with input as {"role": "user", "action": "read"}
}

test_user_write_denied {
    not allow with input as {"role": "user", "action": "write"}
}

test_guest_denied {
    not allow with input as {"role": "guest", "action": "read"}
}
```

Run Rego unit tests with the OPA CLI:

```bash
opa test examples/policies/ -v
```

The CI pipeline runs these automatically before the integration tests.

---

## Creating Custom Test Categories

When you need test logic that goes beyond "send input, compare output," create a custom test category.

### Step 1: Create the Test File

Create `src/opa_test_framework/categories/custom.py`:

```python
"""
Custom test category — example.
"""

import time
from typing import List

from ..client import OPAClient
from ..config import TestConfig
from ..models import TestResult, TestStatus
from .base import Test, TestCategory


class DataConsistencyTest(Test):
    """Verify that expected data is present in OPA."""

    def __init__(self):
        super().__init__(
            name="data_consistency_check",
            description="Verify critical data is loaded in OPA",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()
        try:
            # Read data from OPA's data API
            data = client.get_data("myapp/users")
            duration_ms = (time.time() - start_time) * 1000

            if data and len(data) > 0:
                return self._create_result(
                    status=TestStatus.PASS,
                    duration_ms=duration_ms,
                    message=f"Found {len(data)} users in OPA data store",
                )
            else:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message="No users found in OPA data store",
                    details={"expected": "> 0 users", "actual": 0},
                )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Error checking data: {str(e)}",
            )


class ResponseTimeTest(Test):
    """Verify policy evaluation completes within threshold."""

    def __init__(self):
        super().__init__(
            name="response_time_check",
            description="Ensure policy response time is within limits",
        )

    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        start_time = time.time()
        try:
            client.evaluate_policy("myapp/authorize", {"user": "perf-test"})
            duration_ms = (time.time() - start_time) * 1000

            max_ms = config.performance_thresholds.max_response_time_ms
            if duration_ms > max_ms:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message=f"Response time {duration_ms:.0f}ms exceeds max {max_ms}ms",
                )
            return self._create_result(
                status=TestStatus.PASS,
                duration_ms=duration_ms,
                message=f"Response time {duration_ms:.0f}ms within {max_ms}ms limit",
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Error: {str(e)}",
            )


class CustomTests(TestCategory):
    """Custom test category grouping."""

    def __init__(self):
        super().__init__("custom")

    def get_tests(self) -> List[Test]:
        return [
            DataConsistencyTest(),
            ResponseTimeTest(),
        ]

    def is_smoke_test(self) -> bool:
        return False       # Set True to include in smoke runs

    def get_priority(self) -> int:
        return 10          # Lower = runs earlier (health=0, bundle=1, policy=5)
```

### Step 2: Register the Category

Edit `src/opa_test_framework/runner.py` — add your category to `_get_all_categories()`:

```python
from .categories.custom import CustomTests

def _get_all_categories(self) -> List[TestCategory]:
    categories = [
        HealthTests(),
        BundleTests(),
        AuthTests(),
        CustomTests(),          # ← add your category
    ]
    if self.config.test_policies:
        categories.append(PolicyTests(self.config))
    categories.sort(key=lambda c: c.get_priority())
    return categories
```

### Step 3: Run It

```bash
# Run just the custom category
opa-test --mode category --category custom --config config.yaml

# Or include it in the full suite (it's picked up automatically)
opa-test --mode full --config config.yaml
```

---

## Test Base Classes Reference

### `Test` (Abstract)

```python
class Test(ABC):
    name: str                    # Unique test identifier
    description: str             # Human-readable description

    @abstractmethod
    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        """Run the test and return a result."""

    def _create_result(self, status, duration_ms, message="", details=None) -> TestResult:
        """Helper to build a TestResult."""
```

### `TestCategory` (Abstract)

```python
class TestCategory(ABC):
    name: str                    # Category identifier (used with --category)

    @abstractmethod
    def get_tests(self) -> List[Test]:
        """Return all tests in this category."""

    @abstractmethod
    def is_smoke_test(self) -> bool:
        """True = included in smoke runs."""

    @abstractmethod
    def get_priority(self) -> int:
        """Execution order. Lower = earlier."""

    def execute_all(self, client, config) -> List[TestResult]:
        """Run all tests (provided by base class)."""
```

### `TestResult`

```python
@dataclass
class TestResult:
    test_name: str               # Matches Test.name
    status: TestStatus           # PASS | FAIL | SKIP | ERROR
    duration_ms: float           # Execution time in milliseconds
    message: str                 # Human-readable outcome
    details: Dict[str, Any]      # Additional data (expected/actual, etc.)
```

---

## Best Practices

1. **Name tests descriptively** — `test_admin_write_allowed` is better than `test_1`
2. **Test both allow and deny** — always verify that unauthorised inputs are rejected
3. **Use smoke tests sparingly** — only the most critical checks should be smoke
4. **Keep inputs realistic** — use values that match your actual application data
5. **Set per-category thresholds** — health checks should be faster than policy evals
6. **Write Rego unit tests too** — the framework tests OPA's HTTP interface; Rego tests validate policy logic in isolation
7. **Version your policies** — track `expected_bundle_revision` to catch stale deployments
