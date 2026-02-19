# Getting Started

A step-by-step guide to setting up the OPA Test Framework from scratch, running your first tests, and understanding the results.

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.8+ | Runtime for the framework |
| **pip** | Latest | Package installation |
| **Docker** | 20.10+ | Running OPA (recommended) |
| **Docker Compose** | v2+ | Multi-container setup |
| **Git** | Any | Cloning the repository |
| **OPA CLI** | 0.70+ | _(optional)_ running Rego unit tests locally |

> **Windows users**: Use PowerShell or WSL2. The framework works natively on Windows — the console reporter auto-enables ANSI colours on Windows 10 1607+.

---

## Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd opa-test-framework
```

---

## Step 2: Create a Virtual Environment (Recommended)

```bash
# Linux / macOS
python -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

---

## Step 3: Install the Framework

```bash
pip install -r requirements.txt
pip install -e .
```

This installs the package in **editable mode** so that:
- The `opa-test` CLI command becomes available in your PATH.
- Changes to source files take effect immediately.

Verify the installation:

```bash
opa-test --help
```

You should see the full help output with all available options.

---

## Step 4: Start an OPA Server

You need a running OPA instance to test against. Choose one of the options below.

### Option A: Docker Compose (Recommended)

```bash
docker-compose up -d opa
```

This starts OPA on `http://localhost:8181` with the example policies mounted. The compose file includes a health check, so the container is marked healthy once OPA is ready.

### Option B: Docker (Manual)

```bash
docker run -d -p 8181:8181 \
  -v $(pwd)/examples/policies:/policies \
  openpolicyagent/opa:latest \
  run --server --addr :8181 /policies
```

### Option C: OPA CLI (No Docker)

```bash
# Download OPA binary
# Linux:
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static
chmod +x opa
sudo mv opa /usr/local/bin/

# macOS:
brew install opa

# Windows:
# Download from https://www.openpolicyagent.org/docs/latest/#running-opa

# Start the server
opa run --server --addr :8181 examples/policies/
```

### Verify OPA Is Running

```bash
curl http://localhost:8181/health
# Expected: {"status": "ok"}
```

---

## Step 5: Load Policies into OPA

If you used Docker Compose (`docker-compose up -d opa`), policies are mounted automatically via the volume. However, OPA in `--server` mode with a directory mount loads policies as data, not via the Policy API. To load them via the API (which is what the tests expect):

```bash
# Using Make (easiest)
make start-opa

# Or manually
curl -X PUT --data-binary @examples/policies/example.rego \
  http://localhost:8181/v1/policies/example
```

---

## Step 6: Run Your First Tests

### Smoke Tests (Fast — < 30 seconds)

```bash
opa-test --mode smoke --config config.example.yaml
```

Smoke tests run only **critical** checks:
- OPA health endpoint responds with `ok`
- Bundle status is accessible
- (If configured) one policy decision is validated

### Full Test Suite (Comprehensive — 1-5 minutes)

```bash
opa-test --mode full --config config.example.yaml
```

Full tests include everything in smoke, plus:
- Multiple policy decision tests
- Authentication tests
- Performance threshold validation

### Single Category

```bash
opa-test --mode category --category health --config config.example.yaml
```

Available categories: `health`, `bundle`, `auth`, `policy`.

---

## Step 7: Understand the Output

A successful smoke test run looks like this:

```
Running smoke tests...

OPA Test Results
============================================================

Summary:
  Total Tests: 4
  Passed: 4
  Failed: 0
  Skipped: 0
  Errors: 0
  Duration: 0.23s

✓ ALL TESTS PASSED

All Tests:
  ✓ health_check (12.34ms)
  ✓ health_response_validation (8.56ms)
  ✓ bundle_status_check (15.23ms)
  ✓ bundle_activation_check (10.12ms)
```

**Exit codes:**
- `0` — all tests passed (or skipped)
- `1` — one or more tests failed or errored

---

## Step 8: Try a Dry Run

Validate your configuration and OPA connectivity without executing any tests:

```bash
opa-test --dry-run --config config.example.yaml
```

Output:
```
Dry-run mode: validating configuration and connectivity only.
  OPA URL      : http://localhost:8181
  Timeout      : 10s
  Auth token   : not set
  Report format: console
  Policy tests : 3 configured

Probing OPA health endpoint...
  OPA reachable — status: ok

Dry-run passed. Configuration is valid and OPA is reachable.
```

This is useful as a **pre-flight check** in CI pipelines before running the full suite.

---

## Step 9: Generate CI Reports

For CI/CD integration, generate JUnit XML output:

```bash
opa-test --ci --mode smoke --report-format junit --output test-results/smoke.xml
```

Or JSON:

```bash
opa-test --mode full --report-format json --output test-results/results.json
```

---

## Step 10: Clean Up

```bash
# Stop OPA
docker-compose down

# Or if using Make
make stop-opa
```

---

## Using Make (All-in-One)

The `Makefile` provides shortcuts for common tasks:

```bash
make dev-setup     # Install deps + start OPA + load policies
make smoke         # Run smoke tests
make full          # Run full test suite
make ci-test       # Run tests in CI mode (JUnit output)
make docker-test   # Run tests inside Docker
make stop-opa      # Stop OPA containers
make clean         # Remove build artifacts and caches
make help          # Show all available targets
```

---

## Using the Quick Start Script

For a one-command setup on Linux/macOS:

```bash
chmod +x scripts/quick-start.sh
./scripts/quick-start.sh
```

This script starts OPA, loads policies, runs smoke tests, and prints the results.

---

## Next Steps

- [Configuration Reference](configuration.md) — customise OPA URL, auth, thresholds, policies
- [CLI Reference](cli-reference.md) — all command-line options
- [Writing Tests](writing-tests.md) — add your own policy test cases
- [CI/CD Integration](ci-cd.md) — set up automated pipelines
- [Architecture](architecture.md) — understand the internal design
