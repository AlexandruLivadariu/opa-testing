# OPA Test Framework

Automated integration testing for [Open Policy Agent](https://www.openpolicyagent.org/) deployments — health checks, bundle verification, policy decision validation, and CI/CD reporting.

## Quick Start

```bash
# Install
pip install -r requirements.txt && pip install -e .

# Start OPA
docker-compose up -d opa

# Run smoke tests
opa-test --mode smoke --config config.example.yaml
```

## What It Tests

| Category | What it checks | Smoke? |
|----------|---------------|--------|
| **Health** | OPA is reachable and reports `ok` | Yes |
| **Bundle** | Bundles are downloaded and activated | Yes |
| **Auth** | Bearer-token authentication works | No |
| **Policy** | Policy decisions match expected outputs | Configurable |

## Usage

```bash
# Smoke tests (< 30s, fail-fast)
opa-test --mode smoke --config config.yaml

# Full suite (all categories)
opa-test --mode full --config config.yaml

# Single category
opa-test --mode category --category health --config config.yaml

# CI mode with JUnit XML output
opa-test --ci --mode smoke --report-format junit --output results.xml

# Validate config without running tests
opa-test --dry-run --config config.yaml
```

## Configuration

Create a `config.yaml` (or copy `config.example.yaml`):

```yaml
opa_url: "http://localhost:8181"
auth_token: "your-bearer-token"       # optional
timeout_seconds: 10

test_policies:
  - name: "test_allow_admin"
    policy_path: "example/allow"
    input: { user: "alice", role: "admin" }
    expected_output: true
```

Override with environment variables:

```bash
OPA_URL=http://prod-opa:8181 OPA_AUTH_TOKEN=secret opa-test --mode smoke
```

## Documentation

Full documentation is in the [`docs/`](docs/index.md) folder:

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Prerequisites, installation, first test run |
| [Architecture](docs/architecture.md) | System design, components, execution flow |
| [Configuration](docs/configuration.md) | All YAML options, env vars, per-category thresholds |
| [CLI Reference](docs/cli-reference.md) | Command-line options and examples |
| [Writing Tests](docs/writing-tests.md) | Policy test cases and custom test categories |
| [CI/CD Integration](docs/ci-cd.md) | GitHub Actions, GitLab CI, Jenkins, Docker |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and solutions |

## Development

```bash
pytest                                          # Run unit tests
pytest --cov=src/opa_test_framework             # With coverage
black src/ tests/ && flake8 src/ tests/         # Format + lint
mypy src/                                       # Type check
```

## Project Structure

```
src/opa_test_framework/
  cli.py              CLI entry point (Click)
  client.py           OPA HTTP client (retries, pooling)
  config.py           YAML + env-var configuration
  runner.py           Test orchestrator
  models.py           Data models (TestResult, TestStatus, etc.)
  categories/         Health, Bundle, Auth, Policy test categories
  reporting/          Console, JUnit XML, JSON reporters
```

## License

MIT
