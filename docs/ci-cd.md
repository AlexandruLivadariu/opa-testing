# CI/CD Integration

This guide covers how the OPA Test Framework integrates into automated pipelines — the pre-configured GitHub Actions workflows, how to set them up, and how to adapt for GitLab CI and Jenkins.

---

## Overview

The framework is designed CI-first:

- **Exit codes**: `0` = all pass, `1` = any failure — CI tools use this to gate deployments
- **JUnit XML**: Standard format consumed by every major CI platform
- **JSON reports**: For custom dashboards and monitoring
- **Docker images**: Containerised test runner with pinned dependencies
- **Scheduled runs**: Hourly health checks for production monitoring

---

## GitHub Actions Workflows

The repository ships with three workflows in `.github/workflows/`:

### 1. `test.yml` — Run on Every Push / PR

**Trigger**: Push to `main` or `develop`, any pull request to those branches, or manual dispatch.

**What it does**:

```
lint (black, flake8, mypy)
         │
         ▼
   test (main job)
   ├── Start OPA server (Docker)
   ├── Install Python + framework
   ├── Install OPA CLI
   ├── Load policies into OPA via API
   ├── Run Rego unit tests (opa test)
   ├── Run pytest unit tests (with coverage)
   ├── Run smoke tests → JUnit XML
   ├── Run full test suite → JUnit XML
   ├── Generate JSON report
   ├── Upload test-results/ artifact
   ├── Upload coverage report
   └── Publish results to PR checks
         │
         ▼
   docker-build (build image)
```

**Setup**: No configuration needed — it works out of the box with a self-contained OPA server.

**Artifacts produced**:
- `test-results/pytest-results.xml`
- `test-results/smoke-results.xml`
- `test-results/full-results.xml`
- `test-results/results.json`
- `coverage.xml`

### 2. `deploy.yml` — Deploy to Staging / Production

**Trigger**: Push to `main` (staging), version tags `v*` (production), or manual dispatch with environment selection.

**What it does**:

```
deploy-staging
├── Install framework
├── Run smoke tests against staging OPA
└── Upload staging-smoke-results.xml
         │
         ▼  (only for v* tags)
deploy-production
├── Install framework
├── Run smoke tests against production OPA
├── Run full tests against production OPA
├── Upload production results
└── Notify on failure
```

**Setup** — Add GitHub Secrets:

| Secret | Description |
|--------|-------------|
| `STAGING_OPA_URL` | Full URL of staging OPA (e.g., `https://opa.staging.internal:8181`) |
| `STAGING_OPA_TOKEN` | Bearer token for staging _(if auth enabled)_ |
| `PRODUCTION_OPA_URL` | Full URL of production OPA |
| `PRODUCTION_OPA_TOKEN` | Bearer token for production |

**Configure environments** in GitHub:
1. Go to **Settings → Environments**
2. Create `staging` and `production` environments
3. Add protection rules (required reviewers, wait timers) for production

> If required secrets are not set, the jobs now fail fast with explicit errors.

### 3. `scheduled.yml` — Hourly Health Checks

**Trigger**: Cron schedule (`0 * * * *` — every hour) or manual dispatch.

**What it does**:

```
scheduled-tests (matrix: [staging, production])
├── Install framework
├── Run smoke tests against each environment
├── Upload JSON report (7-day retention)
└── Alert on failure
```

**Setup**: Same secrets as `deploy.yml`. Enable the workflow in the **Actions** tab if it's disabled by default.

---

## Setting Up GitHub Actions (Step by Step)

### 1. Ensure Workflows Exist

The workflows are already in `.github/workflows/`. If you cloned the repo, they're ready to go.

### 2. Add Secrets (for Staging/Production)

1. Go to your repository on GitHub
2. Navigate to **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Add each secret:

```
STAGING_OPA_URL       = https://opa.staging.example.com:8181
STAGING_OPA_TOKEN     = your-staging-token
PRODUCTION_OPA_URL    = https://opa.prod.example.com:8181
PRODUCTION_OPA_TOKEN  = your-production-token
```

### 3. Push and Watch

```bash
git push origin main
```

Go to the **Actions** tab to see the `OPA Tests` workflow running.

### 4. View Results

- **Summary**: Click on the workflow run → see the overview
- **Test details**: Scroll to "OPA Test Results" check (published by `publish-unit-test-result-action`)
- **Artifacts**: Download `test-results` from the workflow run page
- **PR annotations**: Failed tests appear as annotations on the pull request

---

## Docker-Based Testing

### Docker Compose (Local)

```bash
# Start OPA
docker-compose up -d opa

# Run tests in a container
docker-compose run --rm test-runner --mode smoke --config /app/config.yaml

# Or use the test profile
docker-compose --profile test up --abort-on-container-exit
```

The `test-runner` service:
- Builds from `Dockerfile.test`
- Depends on the `opa` service (waits for health check)
- Mounts `config.example.yaml` as `/app/config.yaml`
- Writes results to `./test-results/` via volume mount

### Docker Images

| Dockerfile | Purpose | Entry point |
|------------|---------|-------------|
| `Dockerfile` | Production image | `opa-test` CLI |
| `Dockerfile.test` | CI/test runner | `opa-test` CLI |

Both images:
- Use `python:3.11-slim` base
- Install OPA CLI (version configurable via `OPA_VERSION` build arg)
- Run as non-root user (`appuser`, UID 1000)
- Include the full framework package

Build with a specific OPA version:

```bash
docker build --build-arg OPA_VERSION=0.71.0 -t opa-test-framework:latest .
```

---

## GitLab CI Configuration

Create `.gitlab-ci.yml` in the repository root:

```yaml
stages:
  - lint
  - test
  - deploy

variables:
  OPA_IMAGE: openpolicyagent/opa:0.70.0
  PYTHON_IMAGE: python:3.11

# -- Lint Stage --
lint:
  stage: lint
  image: $PYTHON_IMAGE
  before_script:
    - pip install -r requirements.txt
    - pip install -e ".[dev]"
  script:
    - black --check src/ tests/
    - flake8 src/ tests/
    - mypy src/

# -- Test Stage --
test:
  stage: test
  image: $PYTHON_IMAGE
  services:
    - name: $OPA_IMAGE
      alias: opa
      command: ["run", "--server", "--addr=:8181"]
  before_script:
    - pip install -r requirements.txt
    - pip install -e .
  script:
    - export OPA_URL=http://opa:8181
    - opa-test --ci --mode smoke --report-format junit --output smoke-results.xml
    - opa-test --ci --mode full --report-format junit --output full-results.xml
  artifacts:
    reports:
      junit:
        - smoke-results.xml
        - full-results.xml

# -- Deploy Stage --
deploy_staging:
  stage: deploy
  image: $PYTHON_IMAGE
  only:
    - main
  before_script:
    - pip install -r requirements.txt
    - pip install -e .
  script:
    - export OPA_URL=$STAGING_OPA_URL
    - export OPA_AUTH_TOKEN=$STAGING_OPA_TOKEN
    - opa-test --ci --mode smoke --report-format junit --output staging-results.xml
  artifacts:
    reports:
      junit: staging-results.xml
```

### GitLab Variables

Set these in **Settings → CI/CD → Variables**:

| Variable | Protected | Masked |
|----------|-----------|--------|
| `STAGING_OPA_URL` | Yes | No |
| `STAGING_OPA_TOKEN` | Yes | Yes |
| `PRODUCTION_OPA_URL` | Yes | No |
| `PRODUCTION_OPA_TOKEN` | Yes | Yes |

---

## Jenkins Configuration

Create a `Jenkinsfile`:

```groovy
pipeline {
    agent any

    environment {
        OPA_URL = 'http://localhost:8181'
        OPA_VERSION = '0.70.0'
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pip install -e .'
            }
        }

        stage('Start OPA') {
            steps {
                sh """
                    docker run -d --name opa-test-server \
                      -p 8181:8181 \
                      openpolicyagent/opa:${OPA_VERSION} \
                      run --server --addr :8181
                """
                sh 'sleep 5'
                sh 'curl -sf http://localhost:8181/health'
            }
        }

        stage('Smoke Tests') {
            steps {
                sh 'opa-test --ci --mode smoke --report-format junit --output smoke-results.xml'
            }
        }

        stage('Full Tests') {
            steps {
                sh 'opa-test --ci --mode full --report-format junit --output full-results.xml'
            }
        }
    }

    post {
        always {
            junit 'smoke-results.xml,full-results.xml'
            sh 'docker rm -f opa-test-server || true'
        }
    }
}
```

---

## CI/CD Flow Diagram

```
Developer pushes code
        │
        ▼
┌─────────────────────────────────────────┐
│  test.yml (GitHub Actions)              │
│  1. Lint (black, flake8, mypy)          │
│  2. Start OPA in Docker                 │
│  3. Load policies via REST API          │
│  4. Run Rego unit tests (opa test)      │
│  5. Run pytest unit tests               │
│  6. Run opa-test --mode smoke (JUnit)   │
│  7. Run opa-test --mode full (JUnit)    │
│  8. Build Docker image                  │
│  9. Upload artifacts                    │
└─────────────┬───────────────────────────┘
              │
              ▼ (merge to main)
┌─────────────────────────────────────────┐
│  deploy.yml                             │
│  1. Run smoke tests against staging OPA │
│  2. (on v* tag) Run tests against prod  │
│  3. Notify on failure                   │
└─────────────┬───────────────────────────┘
              │
              ▼ (scheduled)
┌─────────────────────────────────────────┐
│  scheduled.yml (every hour)             │
│  1. Run smoke tests: staging            │
│  2. Run smoke tests: production         │
│  3. Alert on failure                    │
└─────────────────────────────────────────┘
```

---

## Kubernetes Deployment

### OPA Deployment + Service

```yaml
# opa-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opa
  namespace: policy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: opa
  template:
    metadata:
      labels:
        app: opa
    spec:
      containers:
      - name: opa
        image: openpolicyagent/opa:0.70.0
        args: ["run", "--server", "--addr=:8181"]
        ports:
        - containerPort: 8181
        livenessProbe:
          httpGet:
            path: /health
            port: 8181
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8181
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: opa
  namespace: policy
spec:
  selector:
    app: opa
  ports:
  - port: 8181
    targetPort: 8181
```

### Scheduled Health Checks (CronJob)

```yaml
# opa-tests-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: opa-health-check
  namespace: policy
spec:
  schedule: "0 * * * *"    # Every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: opa-test
            image: your-registry/opa-test-framework:latest
            args: ["--ci", "--mode", "smoke", "--report-format", "json",
                   "--output", "/results/health-check.json"]
            env:
            - name: OPA_URL
              value: "http://opa.policy.svc.cluster.local:8181"
            - name: OPA_AUTH_TOKEN
              valueFrom:
                secretKeyRef:
                  name: opa-credentials
                  key: token
          restartPolicy: OnFailure
```

### Post-Deployment Verification (Job)

```yaml
# opa-post-deploy-test.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: opa-post-deploy-test
  namespace: policy
spec:
  template:
    spec:
      containers:
      - name: opa-test
        image: your-registry/opa-test-framework:latest
        args: ["--ci", "--mode", "full", "--report-format", "junit",
               "--output", "/results/test-results.xml"]
        env:
        - name: OPA_URL
          value: "http://opa.policy.svc.cluster.local:8181"
      restartPolicy: Never
  backoffLimit: 2
```

### Kubernetes Secrets

```bash
kubectl create secret generic opa-credentials \
  --from-literal=token=your-secret-token \
  --namespace=policy
```

---

## Monitoring Integration

### Prometheus Metrics

Export test results as Prometheus metrics for dashboards and alerting:

```python
# prometheus_exporter.py
import time
from prometheus_client import Gauge, Counter, start_http_server
from opa_test_framework.config import TestConfig
from opa_test_framework.runner import TestRunner

opa_tests_total = Counter('opa_tests_total', 'Total OPA tests run')
opa_tests_passed = Counter('opa_tests_passed', 'OPA tests passed')
opa_tests_failed = Counter('opa_tests_failed', 'OPA tests failed')
opa_test_duration = Gauge('opa_test_duration_seconds', 'OPA test duration')

def run_and_export(config):
    runner = TestRunner(config)
    summary = runner.run_smoke_tests()

    opa_tests_total.inc(summary.total_tests)
    opa_tests_passed.inc(summary.passed)
    opa_tests_failed.inc(summary.failed)
    opa_test_duration.set(summary.duration_seconds)

if __name__ == '__main__':
    start_http_server(8000)
    while True:
        run_and_export(config)
        time.sleep(300)     # Every 5 minutes
```

### Datadog

Parse JSON output and send custom metrics:

```bash
opa-test --mode smoke --report-format json --output results.json

cat results.json | jq -r '.summary |
  "opa.tests.total:\(.total_tests)|g\n" +
  "opa.tests.passed:\(.passed)|g\n" +
  "opa.tests.failed:\(.failed)|g"' | \
  while read metric; do
    echo "$metric" | nc -u -w1 localhost 8125
  done
```

### AWS Lambda (Serverless Monitoring)

```python
# lambda_handler.py
import json
import os
from opa_test_framework.config import TestConfig
from opa_test_framework.runner import TestRunner

def lambda_handler(event, context):
    config = TestConfig(
        opa_url=os.environ['OPA_URL'],
        auth_token=os.environ.get('OPA_AUTH_TOKEN'),
        timeout_seconds=10,
    )

    runner = TestRunner(config)
    summary = runner.run_smoke_tests()

    return {
        'statusCode': 200 if summary.success else 500,
        'body': json.dumps({
            'success': summary.success,
            'total_tests': summary.total_tests,
            'passed': summary.passed,
            'failed': summary.failed,
        }),
    }
```

---

## Tips

- **Pin OPA version**: Use `OPA_VERSION` env var in Docker Compose and CI to avoid surprises from `latest` tag changes.
- **Use `--dry-run` as a gate**: Before a full test run, validate config and connectivity cheaply.
- **Separate smoke and full**: Smoke tests are fast enough for every push; reserve full tests for merges or nightly runs.
- **Retain artifacts**: Set a retention policy (e.g., 7 days) for scheduled health check results.
- **Add notifications**: Wire up Slack, email, or PagerDuty alerts in the `scheduled.yml` failure path.
