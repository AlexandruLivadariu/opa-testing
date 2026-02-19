# CLI Reference

The `opa-test` command is the primary interface for running tests. It is registered as a console script when the package is installed.

---

## Synopsis

```
opa-test [OPTIONS]
```

---

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--mode` | `smoke` \| `full` \| `category` | `full` | Test execution mode |
| `--category` | string | — | Category name (required when `--mode category`) |
| `--config` | path | — | Path to YAML configuration file |
| `--ci` | flag | `false` | Enable CI mode (exit codes + report output) |
| `--report-format` | `console` \| `junit` \| `json` | from config | Override report format |
| `--output` | path | stdout | Write report to file instead of stdout |
| `--log-level` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` | `INFO` | Logging verbosity |
| `--dry-run` | flag | `false` | Validate config and probe OPA; don't run tests |
| `--help` | flag | — | Show help and exit |

---

## Execution Modes

### Smoke (`--mode smoke`)

Runs only categories marked as smoke tests (health, bundle). Designed for post-deployment verification.

- **Fail-fast**: stops on the first failure
- **Duration**: < 30 seconds
- **Use case**: CI pipelines, post-deploy gates

```bash
opa-test --mode smoke --config config.yaml
```

### Full (`--mode full`)

Runs all registered test categories including policy decision tests and auth tests.

- **Comprehensive**: runs every test, does not stop on failure
- **Duration**: 1–5 minutes depending on policy count
- **Use case**: nightly runs, pre-release validation

```bash
opa-test --mode full --config config.yaml
```

### Category (`--mode category`)

Runs a single named category.

```bash
opa-test --mode category --category health --config config.yaml
opa-test --mode category --category bundle --config config.yaml
opa-test --mode category --category policy --config config.yaml
opa-test --mode category --category auth --config config.yaml
```

---

## Common Usage Examples

### Local Development

```bash
# Quick health check
opa-test --mode smoke --config config.example.yaml

# Full suite with debug logging
opa-test --mode full --config config.example.yaml --log-level DEBUG

# Test only policies
opa-test --mode category --category policy --config config.example.yaml
```

### CI/CD Pipeline

```bash
# Smoke tests with JUnit output
opa-test --ci --mode smoke \
  --config config.yaml \
  --report-format junit \
  --output test-results/smoke-results.xml

# Full suite with JSON output
opa-test --ci --mode full \
  --config config.yaml \
  --report-format json \
  --output test-results/full-results.json
```

### Pre-Flight Validation

```bash
# Validate config + connectivity only (no tests run)
opa-test --dry-run --config config.yaml
```

### Environment Variable Overrides

```bash
# Override OPA URL and auth token
OPA_URL=http://opa-prod:8181 \
OPA_AUTH_TOKEN=secret \
  opa-test --mode smoke --config config.yaml
```

### Docker

```bash
# Run via Docker Compose
docker-compose run --rm test-runner --mode smoke --config /app/config.yaml

# Run via Docker directly
docker run --rm \
  -e OPA_URL=http://host.docker.internal:8181 \
  opa-test-framework:latest \
  --mode smoke --config /app/config.yaml
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All tests passed (or skipped) |
| `1` | One or more tests failed, errored, or configuration was invalid |

CI tools (Jenkins, GitHub Actions, GitLab CI) use exit codes to determine pipeline pass/fail.

---

## Report Formats

### Console (default)

Human-readable, ANSI-coloured output:

```
OPA Test Results
============================================================

Summary:
  Total Tests: 5
  Passed: 5
  Failed: 0
  Skipped: 0
  Errors: 0
  Duration: 0.34s

✓ ALL TESTS PASSED
```

Colour is auto-detected. Control with `NO_COLOR=1` (disable) or `FORCE_COLOR=1` (force).

### JUnit XML (`--report-format junit`)

Standard JUnit XML consumed by CI tools:

```xml
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="OPA Tests" tests="5" failures="0" errors="0" skipped="0" time="0.34">
    <testcase name="health_check" classname="health" time="0.012"/>
    <testcase name="bundle_status_check" classname="bundle" time="0.015"/>
    ...
  </testsuite>
</testsuites>
```

### JSON (`--report-format json`)

Machine-readable JSON for dashboards and monitoring:

```json
{
  "total_tests": 5,
  "passed": 5,
  "failed": 0,
  "skipped": 0,
  "errors": 0,
  "duration_seconds": 0.34,
  "success": true,
  "results": [
    {
      "test_name": "health_check",
      "status": "pass",
      "duration_ms": 12.34,
      "message": "Health check passed"
    }
  ]
}
```

---

## Alternative Invocation

If `opa-test` is not in your PATH, you can run the module directly:

```bash
python -m opa_test_framework.cli --help
```
