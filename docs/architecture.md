# Architecture

This document describes the internal architecture of the OPA Test Framework — how the components fit together, how a test run flows from CLI invocation to final report, and the design decisions behind the system.

---

## High-Level Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   CLI        │────▶│  TestRunner   │────▶│  Test Categories  │
│  (Click)     │     │              │     │  health / bundle  │
│              │     │              │     │  policy / auth    │
└──────┬───────┘     └──────┬───────┘     └────────┬─────────┘
       │                    │                      │
       │              ┌─────▼──────┐         ┌─────▼──────┐
       │              │  OPAClient │────────▶│  OPA Server │
       │              │  (HTTP)    │◀────────│  (REST API) │
       │              └────────────┘         └────────────┘
       │
       ▼
┌──────────────┐
│  Reporters   │
│  console     │
│  junit xml   │
│  json        │
└──────────────┘
```

The framework follows a **pipeline** pattern:

1. **CLI** parses arguments and loads configuration
2. **TestRunner** selects the appropriate test categories based on mode
3. Each **TestCategory** contains one or more **Test** objects
4. Tests call the **OPAClient** to interact with the OPA REST API
5. Results are collected into a **TestResultsSummary**
6. A **Reporter** formats the summary for output

---

## Component Breakdown

### 1. CLI (`cli.py`)

The entry point for the framework, built with [Click](https://click.palletsprojects.com/). Responsibilities:

- Parse command-line arguments (`--mode`, `--category`, `--config`, `--ci`, etc.)
- Load and validate configuration from YAML / environment variables
- Instantiate the `TestRunner`
- Dispatch to the correct execution mode (`smoke`, `full`, `category`)
- Select and invoke the appropriate reporter
- Exit with code `0` (all pass) or `1` (any failure) for CI integration
- Support `--dry-run` for pre-flight config/connectivity validation

**Entry point registration** (in `pyproject.toml`):
```toml
[project.scripts]
opa-test = "opa_test_framework.cli:main"
```

### 2. Configuration (`config.py`)

Manages all runtime settings through a layered system:

```
Defaults  →  config.yaml  →  Environment Variables  →  CLI Flags
            (lowest priority)                        (highest priority)
```

Key data classes:

| Class | Purpose |
|-------|---------|
| `TestConfig` | Top-level config: OPA URL, auth, timeouts, policies, thresholds |
| `PerformanceThresholds` | Global + per-category response time limits |
| `PolicyTest` | Definition of a single policy test case |
| `ConfigurationError` | Raised on invalid or missing configuration |

Configuration loading is **thread-safe** (uses a module-level lock) so the framework can safely be imported by concurrent test processes.

### 3. OPA HTTP Client (`client.py`)

A robust HTTP client built on `requests.Session` with:

- **Connection pooling** — reuses TCP connections across requests
- **Automatic retries** — retries on 429, 500, 502, 503, 504 with exponential backoff
- **Retry-After header** — honours rate-limit headers from OPA
- **Bearer token auth** — injects `Authorization` header when configured
- **Timing measurement** — every request returns `(response, duration_ms)`
- **Context manager** — `with OPAClient(...) as client:` for clean session teardown

Key methods:

| Method | OPA Endpoint | Purpose |
|--------|-------------|---------|
| `health()` | `GET /health` | Health check — returns `HealthResponse` |
| `get_bundle_status()` | `GET /v1/status` | Bundle download/activation status |
| `evaluate_policy(path, input)` | `POST /v1/data/{path}` | Evaluate a policy with input |
| `get_data(path)` | `GET /v1/data/{path}` | Read data from OPA |
| `put_data(path, data)` | `PUT /v1/data/{path}` | Write data to OPA |
| `put_policy(name, rego)` | `PUT /v1/policies/{name}` | Upload a Rego policy |

### 4. Test Categories (`categories/`)

Tests are organised into **categories**, each represented by a class that extends `TestCategory`:

```
TestCategory (abstract)
├── HealthTests      — priority 0, smoke: yes
├── BundleTests      — priority 1, smoke: yes
├── AuthTests        — priority 2, smoke: no
└── PolicyTests      — priority 5, smoke: no (configurable)
```

Each category:
- Returns a list of `Test` objects via `get_tests()`
- Declares whether it's a smoke test (`is_smoke_test()`)
- Has an execution priority (lower = runs first)
- Executes all its tests via `execute_all(client, config)`

**Individual tests** extend the `Test` abstract class and implement `execute(client, config) -> TestResult`.

### 5. Test Runner (`runner.py`)

The orchestrator that ties everything together:

```python
runner = TestRunner(config)

# Three execution modes:
summary = runner.run_smoke_tests()    # Only smoke categories
summary = runner.run_full_tests()     # All categories
summary = runner.run_category("health")  # Single category
```

Execution flow:
1. Collect applicable categories (sorted by priority)
2. Open a single `OPAClient` session (connection pooling)
3. Iterate categories → iterate tests → collect `TestResult` objects
4. In smoke mode, **fail-fast**: stop on first failure
5. Aggregate all results into a `TestResultsSummary`

### 6. Data Models (`models.py`)

Simple dataclasses that flow through the system:

```
TestStatus (enum)     PASS | FAIL | SKIP | ERROR
     │
     ▼
TestResult            test_name, status, duration_ms, message, details
     │
     ▼
TestResultsSummary    total, passed, failed, skipped, errors, duration, results[]
                      └─ .success property → True when failed==0 and errors==0
```

Other models: `HealthResponse`, `BundleStatus`, `PolicyDecision`.

### 7. Result Aggregation (`results.py`)

A single function `aggregate_results(results: List[TestResult]) -> TestResultsSummary` that:
- Counts pass/fail/skip/error
- Sums total duration
- Packages everything into a summary object

### 8. Reporters (`reporting/`)

All reporters implement the `ReportGenerator` abstract class with a single method:

```python
def generate(self, summary: TestResultsSummary) -> str
```

| Reporter | Output | Use Case |
|----------|--------|----------|
| `ConsoleReporter` | ANSI-coloured text | Terminal / local development |
| `JUnitReporter` | JUnit XML | Jenkins, GitHub Actions, GitLab CI |
| `JSONReporter` | Structured JSON | Monitoring dashboards, programmatic analysis |

The console reporter auto-detects colour support (Windows VT processing, TTY detection, `NO_COLOR` / `FORCE_COLOR` env vars).

### 9. Exception Hierarchy (`exceptions.py`)

```
OPATestError (base)
├── OPAConnectionError    — cannot reach OPA (network-level)
├── OPATimeoutError       — request timed out
├── OPAHTTPError          — OPA returned 4xx/5xx
└── OPAPolicyError        — policy evaluation error
```

All exceptions carry context (URL, status code, etc.) for actionable error messages.

---

## Execution Flow Diagram

Below is the complete lifecycle of a test run:

```
User runs:  opa-test --mode smoke --config config.yaml
                │
                ▼
         ┌─────────────┐
         │  CLI (main)  │
         │  - parse args│
         │  - load YAML │
         │  - env vars  │
         │  - validate  │
         └──────┬───────┘
                │
                ▼
         ┌─────────────┐
         │ TestRunner   │
         │ .run_smoke() │
         └──────┬───────┘
                │
     ┌──────────┼──────────┐
     ▼          ▼          ▼
 HealthTests BundleTests  ...
   │            │
   ▼            ▼
 health_check  bundle_status
 health_valid  bundle_revision
   │            │
   └─────┬──────┘
         │  (each test calls OPAClient)
         ▼
  ┌────────────┐       ┌────────────┐
  │ OPAClient  │──────▶│ OPA Server │
  │ GET /health│       │ :8181      │
  │ GET /status│       └────────────┘
  │ POST /data │
  └─────┬──────┘
        │
        ▼
  List[TestResult]
        │
        ▼
  aggregate_results()
        │
        ▼
  TestResultsSummary
        │
        ▼
  ┌────────────┐
  │  Reporter  │──▶  stdout / file
  └────────────┘
        │
        ▼
  sys.exit(0 or 1)
```

---

## Design Principles

1. **Separation of concerns** — Each module has a single responsibility (client, runner, reporter, etc.)
2. **Open/closed** — Add new test categories or reporters without modifying existing code
3. **Fail-fast for smoke** — Smoke tests stop at the first failure for quick feedback
4. **Configuration layering** — Sensible defaults, overridden by YAML, overridden by env vars
5. **CI-first** — Exit codes, JUnit XML, and artifact uploads are first-class features
6. **Resilient client** — Retries, connection pooling, and timeouts prevent flaky tests from network issues
