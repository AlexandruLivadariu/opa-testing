# OPA Test Framework - Deployment Guide

This guide covers different deployment scenarios for the OPA Test Framework.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [CI/CD Integration](#cicd-integration)
4. [Production Deployment](#production-deployment)


---

## Local Development

### Prerequisites

- Python 3.8+
- OPA CLI (optional, for Rego tests)
- Docker (optional, for containerized OPA)

### Setup

1. **Install the framework:**

```bash
pip install -r requirements.txt
pip install -e .
```

2. **Start OPA locally:**

Option A: Using Docker
```bash
docker run -d -p 8181:8181 \
  -v $(pwd)/examples/policies:/policies \
  openpolicyagent/opa:latest \
  run --server --addr :8181 /policies
```

Option B: Using OPA CLI
```bash
# Install OPA
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa
sudo mv opa /usr/local/bin/

# Run OPA server
opa run --server --addr :8181 examples/policies/
```

3. **Run tests:**

```bash
# Smoke tests
opa-test --mode smoke --config config.example.yaml

# Full tests
opa-test --mode full --config config.example.yaml
```

---

## Docker Deployment

### Using Docker Compose

The easiest way to test locally with Docker:

1. **Start OPA and run tests:**

```bash
# Start OPA
docker-compose up -d opa

# Wait for OPA to be ready
sleep 5

# Run tests using Docker
docker-compose run --rm test-runner --mode smoke --config /app/config.yaml
```

2. **Run with authentication:**

```bash
# Start OPA with auth enabled
docker-compose --profile auth up -d opa-auth

# Run tests with auth token
OPA_URL=http://localhost:8182 OPA_AUTH_TOKEN=test-token-12345 \
  opa-test --mode smoke --config config.example.yaml
```

3. **Clean up:**

```bash
docker-compose down -v
```

### Building Custom Docker Image

```bash
# Build the image
docker build -t opa-test-framework:latest .

# Run tests
docker run --rm \
  -e OPA_URL=http://host.docker.internal:8181 \
  opa-test-framework:latest \
  --mode smoke --config /app/config.yaml
```

---

## CI/CD Integration

### GitHub Actions

The repository includes three GitHub Actions workflows:

#### 1. **test.yml** - Run on every push/PR

Automatically:
- Starts OPA service
- Loads policies
- Runs Rego unit tests
- Runs smoke and full test suites
- Publishes test results
- Builds Docker image

**Setup:**
No additional configuration needed. Just push to `main` or `develop` branch.

#### 2. **deploy.yml** - Deploy to environments

Runs smoke tests against staging/production OPA instances.

**Setup:**
1. Add GitHub secrets:
   - `STAGING_OPA_URL`: Staging OPA URL
   - `STAGING_OPA_TOKEN`: Staging auth token (if needed)
   - `PRODUCTION_OPA_URL`: Production OPA URL
   - `PRODUCTION_OPA_TOKEN`: Production auth token (if needed)

2. Configure environments in GitHub:
   - Go to Settings → Environments
   - Create `staging` and `production` environments
   - Add protection rules as needed

#### 3. **scheduled.yml** - Hourly health checks

Runs smoke tests every hour against all environments.

**Setup:**
Same secrets as deploy.yml. Enable the workflow in Actions tab.

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - deploy

variables:
  OPA_IMAGE: openpolicyagent/opa:latest

services:
  - name: $OPA_IMAGE
    alias: opa
    command: ["run", "--server", "--addr=:8181"]

test:
  stage: test
  image: python:3.11
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

deploy_staging:
  stage: deploy
  image: python:3.11
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

### Jenkins

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any
    
    environment {
        OPA_URL = 'http://opa:8181'
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
                sh 'docker run -d --name opa -p 8181:8181 openpolicyagent/opa:latest run --server --addr :8181'
                sh 'sleep 5'
            }
        }
        
        stage('Run Tests') {
            steps {
                sh 'opa-test --ci --mode smoke --report-format junit --output smoke-results.xml'
                sh 'opa-test --ci --mode full --report-format junit --output full-results.xml'
            }
        }
    }
    
    post {
        always {
            junit 'smoke-results.xml,full-results.xml'
            sh 'docker stop opa && docker rm opa'
        }
    }
}
```

---

## Production Deployment

### Kubernetes Deployment

#### 1. Deploy OPA

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
        image: openpolicyagent/opa:latest
        args:
          - "run"
          - "--server"
          - "--addr=:8181"
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

#### 2. Deploy Test Framework as CronJob

```yaml
# opa-tests-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: opa-health-check
  namespace: policy
spec:
  schedule: "0 * * * *"  # Every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: opa-test
            image: your-registry/opa-test-framework:latest
            args:
              - "--ci"
              - "--mode"
              - "smoke"
              - "--report-format"
              - "json"
              - "--output"
              - "/results/health-check.json"
            env:
            - name: OPA_URL
              value: "http://opa:8181"
            - name: OPA_AUTH_TOKEN
              valueFrom:
                secretKeyRef:
                  name: opa-credentials
                  key: token
            volumeMounts:
            - name: results
              mountPath: /results
          volumes:
          - name: results
            emptyDir: {}
          restartPolicy: OnFailure
```

#### 3. Deploy as Post-Deployment Test

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
        args:
          - "--ci"
          - "--mode"
          - "full"
          - "--report-format"
          - "junit"
          - "--output"
          - "/results/test-results.xml"
        env:
        - name: OPA_URL
          value: "http://opa:8181"
      restartPolicy: Never
  backoffLimit: 2
```

### AWS Lambda Deployment

For serverless monitoring:

```python
# lambda_handler.py
import json
import os
from opa_test_framework.config import TestConfig
from opa_test_framework.runner import TestRunner

def lambda_handler(event, context):
    # Load config from environment
    config = TestConfig(
        opa_url=os.environ['OPA_URL'],
        auth_token=os.environ.get('OPA_AUTH_TOKEN'),
        timeout_seconds=10
    )
    
    # Run smoke tests
    runner = TestRunner(config)
    summary = runner.run_smoke_tests()
    
    # Return results
    return {
        'statusCode': 200 if summary.success else 500,
        'body': json.dumps({
            'success': summary.success,
            'total_tests': summary.total_tests,
            'passed': summary.passed,
            'failed': summary.failed
        })
    }
```

### Monitoring Integration

#### Prometheus Metrics

Export test results as Prometheus metrics:

```python
# prometheus_exporter.py
from prometheus_client import Gauge, Counter, start_http_server
from opa_test_framework.runner import TestRunner

# Define metrics
opa_tests_total = Counter('opa_tests_total', 'Total OPA tests run')
opa_tests_passed = Counter('opa_tests_passed', 'OPA tests passed')
opa_tests_failed = Counter('opa_tests_failed', 'OPA tests failed')
opa_test_duration = Gauge('opa_test_duration_seconds', 'OPA test duration')

def run_and_export():
    runner = TestRunner(config)
    summary = runner.run_smoke_tests()
    
    opa_tests_total.inc(summary.total_tests)
    opa_tests_passed.inc(summary.passed)
    opa_tests_failed.inc(summary.failed)
    opa_test_duration.set(summary.duration_seconds)

if __name__ == '__main__':
    start_http_server(8000)
    while True:
        run_and_export()
        time.sleep(300)  # Run every 5 minutes
```

#### Datadog Integration

```bash
# Send results to Datadog
opa-test --mode smoke --config config.yaml --report-format json --output results.json

# Parse and send to Datadog
cat results.json | jq -r '.summary | 
  "opa.tests.total:\(.total_tests)|g,
   opa.tests.passed:\(.passed)|g,
   opa.tests.failed:\(.failed)|g"' | \
  while read metric; do
    echo $metric | nc -u -w1 localhost 8125
  done
```

---

## Configuration Management

### Environment-Specific Configs

Create separate config files:

```bash
configs/
├── local.yaml
├── staging.yaml
└── production.yaml
```

Use environment variable to select:

```bash
export OPA_CONFIG=configs/production.yaml
opa-test --mode smoke --config $OPA_CONFIG
```

### Secrets Management

#### Using Kubernetes Secrets

```bash
kubectl create secret generic opa-credentials \
  --from-literal=token=your-secret-token \
  --namespace=policy
```

#### Using AWS Secrets Manager

```python
import boto3
from opa_test_framework.config import TestConfig

def load_config_from_secrets():
    client = boto3.client('secretsmanager')
    secret = client.get_secret_value(SecretId='opa-credentials')
    creds = json.loads(secret['SecretString'])
    
    return TestConfig(
        opa_url=creds['opa_url'],
        auth_token=creds['auth_token']
    )
```

---

## Troubleshooting

### Common Issues

1. **Connection refused**
   ```bash
   # Check if OPA is running
   curl http://localhost:8181/health
   
   # Check Docker logs
   docker logs opa-test
   ```

2. **Authentication failures**
   ```bash
   # Verify token
   curl -H "Authorization: Bearer $OPA_AUTH_TOKEN" \
     http://localhost:8181/health
   ```

3. **Policy not found**
   ```bash
   # List loaded policies
   curl http://localhost:8181/v1/policies
   
   # Load policy manually
   curl -X PUT --data-binary @policy.rego \
     http://localhost:8181/v1/policies/mypolicy
   ```

### Debug Mode

Enable verbose logging:

```bash
export OPA_LOG_LEVEL=debug
opa-test --mode smoke --config config.yaml
```

---

## Best Practices

1. **Run smoke tests after every deployment**
2. **Schedule full tests hourly or daily**
3. **Monitor test results and alert on failures**
4. **Version your policies and test configurations**
5. **Use separate OPA instances for testing and production**
6. **Implement circuit breakers for test failures**
7. **Store test results for trend analysis**

---

## Support

For issues and questions:
- GitHub Issues: [your-repo/issues]
- Documentation: [your-docs-url]
- Slack: [your-slack-channel]
