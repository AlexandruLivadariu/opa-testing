# OPA Test Framework Examples

This directory contains example policies and configurations for testing the OPA Test Framework.

## Quick Start

### 1. Start OPA with Example Policies

```bash
# Start OPA server with example policies
opa run --server --addr :8181 examples/policies/
```

### 2. Run Tests

```bash
# Run smoke tests
opa-test --mode smoke --config config.example.yaml

# Run full test suite
opa-test --mode full --config config.example.yaml

# Run specific category
opa-test --mode category --category health --config config.example.yaml
```

### 3. Test with CI Mode

```bash
# Generate JUnit XML report
opa-test --ci --mode smoke --report-format junit --output results.xml

# Generate JSON report
opa-test --ci --mode full --report-format json --output results.json
```

## Example Policies

### example.rego

Simple authorization policy that:
- Allows all actions for admin role
- Allows read action for user role
- Denies all other combinations

### example_test.rego

Rego unit tests for the example policy. Run with:

```bash
opa test examples/policies/
```

## Configuration

See `config.example.yaml` for a complete configuration example with:
- OPA instance URL
- Authentication settings
- Performance thresholds
- Policy test cases

## Docker Compose Example

```yaml
version: '3.8'
services:
  opa:
    image: openpolicyagent/opa:latest
    ports:
      - "8181:8181"
    command:
      - "run"
      - "--server"
      - "--addr=:8181"
    volumes:
      - ./examples/policies:/policies
```

Start with:
```bash
docker-compose up -d
```

Then run tests:
```bash
opa-test --mode smoke --config config.example.yaml
```
