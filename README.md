# OPA Test Framework

Automated testing framework for enterprise Open Policy Agent (OPA) deployments.

## Overview

This framework provides comprehensive testing capabilities for OPA deployments, including:

- **Pre-deployment validation**: Rego syntax checking and unit tests
- **Post-deployment verification**: HTTP-based integration tests
- **Smoke tests**: Fast critical checks for post-deployment verification
- **Performance testing**: Response time measurement and threshold validation
- **Security testing**: Authentication and authorization verification
- **CI/CD integration**: JUnit XML and JSON reporting
- **Docker support**: Containerized testing and deployment
- **GitHub Actions**: Pre-configured CI/CD workflows

## Quick Start

### Option 1: Using the Quick Start Script

```bash
# Clone the repository
git clone <your-repo-url>
cd opa-test-framework

# Run quick start (starts OPA and runs smoke tests)
chmod +x scripts/quick-start.sh
./scripts/quick-start.sh
```

### Option 2: Using Make

```bash
# Setup development environment
make dev-setup

# Run smoke tests
make smoke

# Run full tests
make full
```

### Option 3: Using Docker Compose

```bash
# Start OPA
docker-compose up -d opa

# Run tests
docker-compose run --rm test-runner --mode smoke --config /app/config.yaml
```

## Installation

### Local Installation

```bash
pip install -r requirements.txt
pip install -e .
```

### Docker Installation

```bash
# Build the image
docker build -t opa-test-framework:latest .

# Run tests
docker run --rm \
  -e OPA_URL=http://your-opa:8181 \
  opa-test-framework:latest \
  --mode smoke --config /app/config.yaml
```

## Quick Start

### Running Smoke Tests

```bash
opa-test --mode smoke --config config.yaml
```

### Running Full Test Suite

```bash
opa-test --mode full --config config.yaml
```

### Running Specific Category

```bash
opa-test --category health --config config.yaml
```

### CI/CD Mode

```bash
opa-test --ci --mode smoke --report-format junit
```

## Configuration

Create a `config.yaml` file:

```yaml
opa_url: "http://localhost:8181"
auth_token: "your-bearer-token"  # optional
timeout_seconds: 10

performance_thresholds:
  max_response_time_ms: 500
  warning_threshold_ms: 100

test_policies:
  - name: "test_allow"
    policy_path: "example/allow"
    input:
      user: "alice"
      action: "read"
    expected_output:
      allow: true
```

Environment variables can override configuration:

```bash
export OPA_URL="http://opa:8181"
export OPA_AUTH_TOKEN="token"
opa-test --mode smoke
```

## Development

Run tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=src/opa_test_framework --cov-report=html
```

Format code:

```bash
black src/ tests/
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment guides including:

- Local development setup
- Docker and Docker Compose deployment
- Kubernetes deployment
- CI/CD integration (GitHub Actions, GitLab CI, Jenkins)
- Production deployment patterns
- Monitoring and alerting setup

## CI/CD Integration

The framework includes pre-configured GitHub Actions workflows:

- **test.yml**: Runs on every push/PR
- **deploy.yml**: Deploys to staging/production
- **scheduled.yml**: Hourly health checks

See [.github/workflows/](.github/workflows/) for details.

## Docker Support

### Start OPA for Testing

```bash
# Using docker-compose
docker-compose up -d opa

# Using docker directly
docker run -d -p 8181:8181 \
  -v $(pwd)/examples/policies:/policies \
  openpolicyagent/opa:latest \
  run --server --addr :8181 /policies
```

### Run Tests in Docker

```bash
# Build and run
docker-compose run --rm test-runner --mode smoke --config /app/config.yaml

# Or use the Makefile
make docker-test
```

## Available Commands

```bash
# Using Make
make help              # Show all available commands
make install           # Install dependencies
make start-opa         # Start OPA with example policies
make smoke             # Run smoke tests
make full              # Run full test suite
make stop-opa          # Stop OPA
make quick-start       # Start OPA and run smoke tests

# Using CLI directly
opa-test --mode smoke --config config.yaml
opa-test --mode full --config config.yaml
opa-test --mode category --category health --config config.yaml
opa-test --ci --mode smoke --report-format junit --output results.xml
```

## Documentation

See the `.kiro/specs/opa-deployment-testing/` directory for:
- `requirements.md` - Detailed requirements
- `design.md` - Architecture and design decisions
- `tasks.md` - Implementation plan

Additional guides:
- [DEPLOYMENT.md](DEPLOYMENT.md) - Comprehensive deployment guide
- [TESTING.md](TESTING.md) - Testing guide and best practices
- [examples/README.md](examples/README.md) - Example usage

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CI/CD Pipeline                          │
│  (GitHub Actions, GitLab CI, Jenkins)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Pre-Deployment  │      │ Post-Deployment  │           │
│  │   Validation     │──────▶│  Verification   │           │
│  └──────────────────┘      └──────────────────┘           │
│         │                           │                      │
│         ▼                           ▼                      │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │ Rego Unit Tests  │      │ Integration Tests│           │
│  │ Syntax Checking  │      │  Smoke Tests     │           │
│  └──────────────────┘      └──────────────────┘           │
│                                     │                      │
│                                     ▼                      │
│                            ┌──────────────────┐            │
│                            │  OPA Instances   │            │
│                            │  (Deployment)    │            │
│                            └──────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Components

- **OPA Client**: HTTP client with retry logic and error handling
- **Test Categories**: Modular test organization (Health, Bundle, Policy, etc.)
- **Test Runner**: Orchestrates test execution with multiple modes
- **Reporters**: Console, JUnit XML, and JSON output formats
- **CLI**: Command-line interface with Click
- **Configuration**: YAML-based with environment variable overrides

## Features

✅ **Comprehensive Testing**
- Health checks
- Bundle status verification
- Policy decision validation
- Performance testing
- Security testing

✅ **CI/CD Ready**
- Pre-configured GitHub Actions workflows
- JUnit XML and JSON reporting
- Proper exit codes for automation
- Docker support

✅ **Flexible Deployment**
- Local development
- Docker and Docker Compose
- Kubernetes
- AWS Lambda
- Scheduled monitoring

✅ **Easy to Use**
- Simple CLI interface
- Quick start scripts
- Makefile for common tasks
- Comprehensive documentation

## License

MIT
