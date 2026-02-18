# Testing Guide

This guide explains how to test your OPA deployment using the OPA Test Framework.

## Table of Contents

1. [Test Types](#test-types)
2. [Running Tests Locally](#running-tests-locally)
3. [Writing Custom Tests](#writing-custom-tests)
4. [Configuration](#configuration)
5. [Interpreting Results](#interpreting-results)

---

## Test Types

### 1. Smoke Tests

Fast, critical tests that verify basic functionality:
- OPA health check
- Bundle status verification
- One policy decision test

**When to use**: After every deployment, in CI/CD pipelines

```bash
opa-test --mode smoke --config config.yaml
```

**Expected duration**: < 30 seconds

### 2. Full Test Suite

Comprehensive validation including:
- All smoke tests
- Multiple policy decision tests
- Performance validation
- Data API tests

**When to use**: Scheduled runs (hourly/daily), before production releases

```bash
opa-test --mode full --config config.yaml
```

**Expected duration**: 1-5 minutes

### 3. Category Tests

Run specific test categories:
- `health`: Health endpoint tests
- `bundle`: Bundle status tests
- `policy`: Policy decision tests

```bash
opa-test --mode category --category health --config config.yaml
```

---

## Running Tests Locally

### Prerequisites

1. **Start OPA**:

```bash
# Option A: Docker
docker run -d -p 8181:8181 \
  -v $(pwd)/examples/policies:/policies \
  openpolicyagent/opa:latest \
  run --server --addr :8181 /policies

# Option B: OPA CLI
opa run --server --addr :8181 examples/policies/
```

2. **Install framework**:

```bash
pip install -r requirements.txt
pip install -e .
```

### Run Tests

```bash
# Smoke tests
opa-test --mode smoke --config config.example.yaml

# Full tests
opa-test --mode full --config config.example.yaml

# Specific category
opa-test --mode category --category policy --config config.example.yaml
```

### Using Environment Variables

Override configuration with environment variables:

```bash
export OPA_URL=http://localhost:8181
export OPA_AUTH_TOKEN=your-token
export OPA_TIMEOUT=15

opa-test --mode smoke --config config.example.yaml
```

---

## Writing Custom Tests

### 1. Add Policy Test Cases

Edit your config file:

```yaml
test_policies:
  - name: "test_my_policy"
    policy_path: "myapp/authorize"
    input:
      user: "alice"
      resource: "document-123"
      action: "read"
    expected_output:
      allow: true
      reason: "user has read permission"
```

### 2. Create Custom Test Category

Create a new file `src/opa_test_framework/categories/custom.py`:

```python
from typing import List
from ..client import OPAClient
from ..config import TestConfig
from ..models import TestResult, TestStatus
from .base import Test, TestCategory

class MyCustomTest(Test):
    def __init__(self):
        super().__init__(
            name="my_custom_test",
            description="Test custom functionality"
        )
    
    def execute(self, client: OPAClient, config: TestConfig) -> TestResult:
        import time
        start_time = time.time()
        
        try:
            # Your test logic here
            result = client.evaluate_policy("myapp/policy", {"user": "test"})
            duration_ms = (time.time() - start_time) * 1000
            
            if result.result.get("allow"):
                return self._create_result(
                    status=TestStatus.PASS,
                    duration_ms=duration_ms,
                    message="Custom test passed"
                )
            else:
                return self._create_result(
                    status=TestStatus.FAIL,
                    duration_ms=duration_ms,
                    message="Custom test failed"
                )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_result(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Error: {str(e)}"
            )

class CustomTests(TestCategory):
    def __init__(self):
        super().__init__("custom")
    
    def get_tests(self) -> List[Test]:
        return [MyCustomTest()]
    
    def is_smoke_test(self) -> bool:
        return False
    
    def get_priority(self) -> int:
        return 10
```

Register in `src/opa_test_framework/runner.py`:

```python
from .categories.custom import CustomTests

def _get_all_categories(self) -> List[TestCategory]:
    categories = [
        HealthTests(),
        BundleTests(),
        CustomTests(),  # Add your category
    ]
    # ...
```

---

## Configuration

### Basic Configuration

```yaml
# config.yaml
opa_url: "http://localhost:8181"
timeout_seconds: 10

performance_thresholds:
  max_response_time_ms: 500
  warning_threshold_ms: 100

test_policies:
  - name: "test_allow"
    policy_path: "example/allow"
    input:
      role: "admin"
    expected_output:
      allow: true
```

### Advanced Configuration

```yaml
# Multiple OPA instances
opa_urls:
  - "http://opa-1:8181"
  - "http://opa-2:8181"
  - "http://opa-3:8181"

# Authentication
auth_token: "your-bearer-token"

# Bundle verification
bundle_service_url: "http://bundle-server:8080"
expected_bundle_revision: "v1.2.3"

# Rego test configuration
rego_test_paths:
  - "policies"
  - "custom-policies"
rego_coverage_enabled: true

# Report format
report_format: "console"  # or "junit", "json"
```

### Environment Variable Overrides

All configuration can be overridden with environment variables:

```bash
OPA_URL=http://prod-opa:8181
OPA_AUTH_TOKEN=secret-token
OPA_TIMEOUT=20
OPA_MAX_RESPONSE_TIME_MS=1000
OPA_WARNING_THRESHOLD_MS=200
OPA_REPORT_FORMAT=json
```

---

## Interpreting Results

### Console Output

```
OPA Test Results
============================================================

Summary:
  Total Tests: 5
  Passed: 4
  Failed: 1
  Skipped: 0
  Errors: 0
  Duration: 2.34s

✗ TESTS FAILED

Failed Tests:

  ✗ policy_test_deny_guest
    Policy decision mismatch
    Details: {'expected': {'allow': False}, 'actual': {'allow': True}}
    Duration: 123.45ms

All Tests:
  ✓ health_check (45.23ms)
  ✓ bundle_status (67.89ms)
  ✓ policy_test_allow_admin (123.45ms)
  ✗ policy_test_deny_guest (123.45ms)
  ✓ health_response_validation (34.56ms)
```

### JUnit XML Output

```bash
opa-test --mode full --report-format junit --output results.xml
```

Output format compatible with CI/CD tools:

```xml
<?xml version="1.0" ?>
<testsuite name="OPA Tests" tests="5" failures="1" errors="0" skipped="0" time="2.340">
  <testcase name="health_check" time="0.045"/>
  <testcase name="policy_test_deny_guest" time="0.123">
    <failure message="Policy decision mismatch">
      {'expected': {'allow': False}, 'actual': {'allow': True}}
    </failure>
  </testcase>
</testsuite>
```

### JSON Output

```bash
opa-test --mode full --report-format json --output results.json
```

```json
{
  "summary": {
    "total_tests": 5,
    "passed": 4,
    "failed": 1,
    "skipped": 0,
    "errors": 0,
    "duration_seconds": 2.34,
    "success": false
  },
  "results": [
    {
      "test_name": "health_check",
      "status": "pass",
      "duration_ms": 45.23,
      "message": "Health check passed",
      "details": {"status": "ok"}
    }
  ]
}
```

### Exit Codes

In CI mode (`--ci` flag):
- `0`: All tests passed
- `1`: One or more tests failed or errors occurred

```bash
opa-test --ci --mode smoke --config config.yaml
echo $?  # Check exit code
```

---

## Common Test Scenarios

### 1. Post-Deployment Verification

```bash
# Run smoke tests after deployment
opa-test --ci --mode smoke \
  --config config.yaml \
  --report-format junit \
  --output deployment-results.xml

# Check exit code
if [ $? -eq 0 ]; then
  echo "Deployment verified successfully"
else
  echo "Deployment verification failed"
  exit 1
fi
```

### 2. Continuous Monitoring

```bash
# Run every hour via cron
0 * * * * /usr/local/bin/opa-test --ci --mode smoke --config /etc/opa-test/config.yaml
```

### 3. Multi-Environment Testing

```bash
# Test staging
OPA_URL=https://opa-staging.example.com \
  opa-test --mode smoke --config config.yaml

# Test production
OPA_URL=https://opa-prod.example.com \
  opa-test --mode smoke --config config.yaml
```

### 4. Performance Regression Testing

```yaml
# config.yaml with strict thresholds
performance_thresholds:
  max_response_time_ms: 100  # Fail if > 100ms
  warning_threshold_ms: 50   # Warn if > 50ms
```

```bash
opa-test --mode full --config config.yaml
```

---

## Troubleshooting

### Test Failures

1. **Check OPA is running**:
```bash
curl http://localhost:8181/health
```

2. **Verify policies are loaded**:
```bash
curl http://localhost:8181/v1/policies
```

3. **Test policy manually**:
```bash
curl -X POST http://localhost:8181/v1/data/example/allow \
  -H 'Content-Type: application/json' \
  -d '{"input": {"role": "admin"}}'
```

### Connection Issues

```bash
# Check network connectivity
ping opa-server

# Check DNS resolution
nslookup opa-server

# Test with curl
curl -v http://opa-server:8181/health
```

### Authentication Issues

```bash
# Verify token works
curl -H "Authorization: Bearer $OPA_AUTH_TOKEN" \
  http://localhost:8181/health

# Check token in config
grep auth_token config.yaml
```

---

## Best Practices

1. **Start with smoke tests** - Fast feedback on critical functionality
2. **Run full tests regularly** - Catch issues before they reach production
3. **Version your test configs** - Track changes alongside policy changes
4. **Monitor test trends** - Track test duration and failure rates
5. **Fail fast in CI** - Use smoke tests with `--ci` flag
6. **Test in isolation** - Use dedicated OPA instances for testing
7. **Document custom tests** - Make it easy for others to understand
8. **Keep tests fast** - Optimize slow tests or move to scheduled runs

---

## Running Python Unit Tests

The framework itself is tested with pytest. Tests are in `tests/`.

```bash
# Run all unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src/opa_test_framework --cov-report=term-missing

# Run a specific test file
pytest tests/test_config.py -v

# Run a specific test class
pytest tests/test_config.py::TestValidateConfig -v
```

## Running Rego Unit Tests

Rego unit tests validate policy logic directly without needing a running OPA server.

```bash
# Run all Rego tests
opa test examples/policies/ -v

# Run with coverage
opa test examples/policies/ -v --coverage
```

### Writing Rego Tests

Always test edge cases alongside happy paths:

```rego
# Happy path
test_allow_admin {
    allow with input as {"role": "admin", "action": "write"}
}

# Edge cases
test_deny_empty_input {
    not allow with input as {}
}

test_deny_missing_role {
    not allow with input as {"action": "read"}
}

test_deny_null_values {
    not allow with input as {"role": null, "action": null}
}
```

## Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/

# Or use Make
make format
make lint
make type-check
```

---

## Next Steps

- See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- See [examples/](examples/) for more test examples
- See [.github/workflows/](.github/workflows/) for CI/CD integration
