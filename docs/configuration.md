# Configuration Reference

The framework uses a **layered configuration** system. Settings are resolved in this order (last wins):

```
Built-in defaults  →  config.yaml file  →  Environment variables  →  CLI flags
```

---

## Configuration File (YAML)

Create a `config.yaml` (or copy `config.example.yaml`):

```yaml
# OPA server connection
opa_url: "http://localhost:8181"
auth_token: "your-bearer-token"       # optional
timeout_seconds: 10

# Performance thresholds
performance_thresholds:
  max_response_time_ms: 500
  warning_threshold_ms: 100
  category_thresholds:              # optional per-category overrides
    health:
      max_response_time_ms: 50
      warning_threshold_ms: 20
    policy:
      max_response_time_ms: 1000
      warning_threshold_ms: 300

# Report output format
report_format: "console"              # console | junit | json

# Rego unit test settings
rego_test_paths:
  - "policies"
rego_coverage_enabled: false

# Policy test cases
test_policies:
  - name: "test_allow_admin"
    policy_path: "example/allow"
    input:
      user: "alice"
      role: "admin"
      action: "read"
    expected_output: true
```

---

## Full Option Reference

### Connection Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `opa_url` | string | `http://localhost:8181` | Base URL of the OPA instance |
| `auth_token` | string | `null` | Bearer token for the `Authorization` header |
| `timeout_seconds` | int | `10` | HTTP request timeout in seconds |

### Bundle Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `bundle_service_url` | string | `null` | URL of the bundle server (for bundle tests) |
| `expected_bundle_revision` | string | `null` | Expected bundle revision string |

### Performance Thresholds

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `performance_thresholds.max_response_time_ms` | int | `500` | Fail threshold (ms) |
| `performance_thresholds.warning_threshold_ms` | int | `100` | Warning threshold (ms) |
| `performance_thresholds.category_thresholds` | dict | `{}` | Per-category overrides (see below) |

#### Per-Category Thresholds

Health checks are typically much faster than complex policy evaluations. Use per-category overrides for accurate alerting:

```yaml
performance_thresholds:
  max_response_time_ms: 500           # global default
  warning_threshold_ms: 100
  category_thresholds:
    health:
      max_response_time_ms: 50        # health should be fast
      warning_threshold_ms: 20
    bundle:
      max_response_time_ms: 200
      warning_threshold_ms: 80
    policy:
      max_response_time_ms: 1000      # complex policies can be slower
      warning_threshold_ms: 300
```

### Report Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `report_format` | string | `console` | Output format: `console`, `junit`, `json` |

### Rego Test Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `rego_test_paths` | list[string] | `["policies"]` | Directories containing Rego test files |
| `rego_coverage_enabled` | bool | `false` | Enable Rego test coverage reporting |

### Policy Test Cases

Each entry under `test_policies` defines a test:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `name` | string | Yes | Unique test name (used in reports) |
| `policy_path` | string | Yes | OPA data path (e.g., `example/allow`) |
| `input` | dict | Yes | JSON input to send to OPA |
| `expected_output` | any | Yes | Expected result — can be `true`, `false`, a dict, or a list |
| `expected_allow` | bool | No | Shorthand for `expected_output: {allow: <value>}` |
| `smoke` | bool | No (`false`) | Include this test in smoke runs |

#### Policy Path Explained

OPA's REST API at `/v1/data/{path}` returns the value at that document path. For a policy file like:

```rego
package example

default allow = false

allow {
    input.role == "admin"
}
```

The `policy_path` would be `example/allow`, and `expected_output` would be `true` or `false`.

For set-generating rules like `permissions[action]`, the result is a JSON array:

```yaml
- name: "test_permissions"
  policy_path: "example/permissions"
  input:
    user: "charlie"
    resource: "document-123"
  expected_output:
    - "read"
```

---

## Environment Variables

All configuration can be overridden via environment variables. This is especially useful in CI/CD and Docker:

| Variable | Overrides | Example |
|----------|-----------|---------|
| `OPA_URL` | `opa_url` | `http://opa:8181` |
| `OPA_AUTH_TOKEN` | `auth_token` | `my-secret-token` |
| `OPA_TIMEOUT` | `timeout_seconds` | `20` |
| `OPA_MAX_RESPONSE_TIME_MS` | `performance_thresholds.max_response_time_ms` | `1000` |
| `OPA_WARNING_THRESHOLD_MS` | `performance_thresholds.warning_threshold_ms` | `200` |
| `OPA_REPORT_FORMAT` | `report_format` | `json` |

### Example

```bash
export OPA_URL=http://prod-opa:8181
export OPA_AUTH_TOKEN=secret-token
export OPA_TIMEOUT=20

opa-test --mode smoke --config config.yaml
```

Environment variables take precedence over the YAML file but are overridden by CLI flags like `--report-format`.

---

## CLI Flag Overrides

Several settings can be overridden directly on the command line:

```bash
opa-test --mode smoke \
         --config config.yaml \
         --report-format junit \
         --output results.xml \
         --log-level DEBUG
```

See [CLI Reference](cli-reference.md) for the full list.

---

## Example Configurations

### Minimal (Local Development)

```yaml
opa_url: "http://localhost:8181"
test_policies:
  - name: "test_basic"
    policy_path: "example/allow"
    input:
      role: "admin"
    expected_output: true
```

### Production with Auth

```yaml
opa_url: "https://opa.prod.internal:8181"
auth_token: "${OPA_AUTH_TOKEN}"
timeout_seconds: 15

performance_thresholds:
  max_response_time_ms: 300
  warning_threshold_ms: 50

report_format: "junit"

test_policies:
  - name: "test_admin_allow"
    policy_path: "authz/allow"
    input:
      user: "admin@company.com"
      action: "read"
      resource: "/api/data"
    expected_output: true

  - name: "test_guest_deny"
    policy_path: "authz/allow"
    input:
      user: "anonymous"
      action: "write"
      resource: "/api/data"
    expected_output: false
```

### Multi-Environment (Using Env Vars)

Use the same YAML file across environments — override only the connection:

```yaml
opa_url: "http://localhost:8181"      # default for local dev
timeout_seconds: 10

test_policies:
  - name: "test_core_policy"
    policy_path: "app/authorize"
    input:
      user: "test-user"
      action: "read"
    expected_output: true
```

```bash
# Staging
OPA_URL=https://opa.staging.internal:8181 OPA_AUTH_TOKEN=stg-token opa-test --mode smoke

# Production
OPA_URL=https://opa.prod.internal:8181 OPA_AUTH_TOKEN=prod-token opa-test --mode smoke
```

---

## Validation

The framework validates configuration on load and reports actionable errors:

```bash
$ opa-test --mode smoke --config bad-config.yaml
Configuration errors:
  - opa_url must be a valid URL
  - timeout_seconds must be a positive integer
```

Use `--dry-run` to validate without executing tests:

```bash
opa-test --dry-run --config config.yaml
```
