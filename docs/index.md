# OPA Test Framework — Documentation

Welcome to the **OPA Test Framework** documentation. This framework provides automated, production-grade testing for [Open Policy Agent (OPA)](https://www.openpolicyagent.org/) deployments — covering health checks, bundle verification, policy decision validation, performance monitoring, and CI/CD integration.

---

## Table of Contents

| Document | Description |
|----------|-------------|
| [Getting Started](getting-started.md) | Prerequisites, installation, and running your first tests |
| [Architecture](architecture.md) | System design, component overview, and execution flow |
| [Configuration Reference](configuration.md) | All configuration options (YAML & environment variables) |
| [CLI Reference](cli-reference.md) | Command-line interface usage and examples |
| [Writing Tests](writing-tests.md) | Adding policy test cases and custom test categories |
| [CI/CD Integration](ci-cd.md) | GitHub Actions, GitLab CI, Jenkins, Docker, and Kubernetes |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |

---

## What Is This Project?

The OPA Test Framework is a Python-based CLI tool that runs **integration tests against a live OPA server** over HTTP. It is designed to answer one question at every stage of your deployment pipeline:

> _"Is OPA healthy, are bundles loaded, and are policy decisions correct?"_

### Core Capabilities

- **Health checks** — verify OPA is reachable and reporting `ok`
- **Bundle verification** — confirm bundles are downloaded and activated
- **Policy decision tests** — send inputs to OPA and assert expected outputs
- **Performance thresholds** — fail tests when response times exceed limits
- **Authentication tests** — validate bearer-token auth flows
- **Multiple report formats** — Console (coloured), JUnit XML, JSON
- **Docker & Kubernetes ready** — containerised test runner with health-checked compose setup
- **CI/CD first-class** — proper exit codes, artifact uploads, scheduled health checks

### When to Use It

| Scenario | Mode | Frequency |
|----------|------|-----------|
| Post-deployment verification | `smoke` | Every deploy |
| Nightly regression suite | `full` | Daily / nightly |
| Production health monitoring | `smoke` | Hourly (scheduled) |
| Pre-merge validation (PR) | `full` | Every pull request |
| Local development | `smoke` or `full` | On demand |

---

## Quick Start (60 Seconds)

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd opa-test-framework

# 2. Install
pip install -r requirements.txt
pip install -e .

# 3. Start OPA (Docker)
docker-compose up -d opa

# 4. Run smoke tests
opa-test --mode smoke --config config.example.yaml
```

See [Getting Started](getting-started.md) for the full walkthrough.

---

## Project Structure

```
opa-test-framework/
├── .github/workflows/          # CI/CD pipelines (GitHub Actions)
│   ├── test.yml                # Runs on push / PR
│   ├── deploy.yml              # Deploys to staging / production
│   └── scheduled.yml           # Hourly health checks
├── src/opa_test_framework/     # Python package
│   ├── cli.py                  # Click-based CLI entry point
│   ├── client.py               # OPA HTTP client (retries, pooling)
│   ├── config.py               # YAML + env-var configuration
│   ├── models.py               # Data models (TestResult, etc.)
│   ├── runner.py               # Test orchestrator
│   ├── results.py              # Result aggregation
│   ├── exceptions.py           # Custom error hierarchy
│   ├── categories/             # Test categories
│   │   ├── base.py             # Abstract base classes
│   │   ├── health.py           # Health endpoint tests
│   │   ├── bundle.py           # Bundle status tests
│   │   ├── auth.py             # Authentication tests
│   │   └── policy.py           # Policy decision tests
│   └── reporting/              # Report generators
│       ├── console.py          # Coloured terminal output
│       ├── junit.py            # JUnit XML for CI tools
│       └── json_reporter.py    # Machine-readable JSON
├── examples/policies/          # Sample Rego policies
├── scripts/quick-start.sh      # One-command setup script
├── docker-compose.yml          # OPA + test-runner containers
├── Dockerfile                  # Production image
├── Dockerfile.test             # CI/test-runner image
├── Makefile                    # Task automation
├── config.example.yaml         # Example configuration
├── pyproject.toml              # Python packaging
└── tests/                      # Unit tests (pytest)
```

---

## License

MIT — see repository root for details.
