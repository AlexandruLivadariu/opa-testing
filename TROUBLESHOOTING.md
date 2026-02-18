# Troubleshooting Guide

Common issues and solutions for the OPA Test Framework.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Connection Issues](#connection-issues)
3. [Test Failures](#test-failures)
4. [Docker Issues](#docker-issues)
5. [CI/CD Issues](#cicd-issues)

---

## Installation Issues

### Issue: `pip install` fails

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solutions:**

1. **Update pip:**
```bash
python -m pip install --upgrade pip
```

2. **Check Python version:**
```bash
python --version  # Should be 3.8+
```

3. **Use virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Issue: `opa-test` command not found

**Symptoms:**
```bash
opa-test: command not found
```

**Solutions:**

1. **Install in editable mode:**
```bash
pip install -e .
```

2. **Check PATH:**
```bash
which opa-test
# If not found, add to PATH or use full path
python -m opa_test_framework.cli --help
```

3. **Reinstall:**
```bash
pip uninstall opa-test-framework
pip install -e .
```

---

## Connection Issues

### Issue: Cannot connect to OPA

**Symptoms:**
```
Error: Failed to connect to OPA at http://localhost:8181: Connection refused
```

**Solutions:**

1. **Check if OPA is running:**
```bash
curl http://localhost:8181/health
```

2. **Check Docker container:**
```bash
docker ps | grep opa
docker logs opa-test
```

3. **Verify URL:**
```bash
# Check config file
grep opa_url config.yaml

# Or use environment variable
export OPA_URL=http://localhost:8181
```

4. **Check firewall:**
```bash
# On Linux
sudo ufw status
sudo ufw allow 8181

# On macOS
sudo pfctl -sr | grep 8181
```

### Issue: Connection timeout

**Symptoms:**
```
Error: Request to OPA at http://opa:8181 timed out after 10 seconds
```

**Solutions:**

1. **Increase timeout:**
```yaml
# config.yaml
timeout_seconds: 30
```

Or:
```bash
export OPA_TIMEOUT=30
```

2. **Check network latency:**
```bash
ping opa-server
curl -w "@curl-format.txt" http://opa-server:8181/health
```

3. **Check OPA performance:**
```bash
# OPA logs
docker logs opa-test

# System resources
docker stats opa-test
```

### Issue: DNS resolution fails

**Symptoms:**
```
Error: Failed to connect to OPA: Name or service not known
```

**Solutions:**

1. **Use IP address instead:**
```bash
export OPA_URL=http://192.168.1.100:8181
```

2. **Check /etc/hosts:**
```bash
cat /etc/hosts
# Add if missing:
# 127.0.0.1 opa-server
```

3. **In Docker, use service name:**
```yaml
# docker-compose.yml
services:
  test-runner:
    environment:
      - OPA_URL=http://opa:8181  # Use service name
```

---

## Test Failures

### Issue: Health check fails

**Symptoms:**
```
✗ health_check
  Health endpoint returned HTTP 404
```

**Solutions:**

1. **Check OPA version:**
```bash
docker exec opa-test opa version
# Health endpoint available in OPA 0.10.0+
```

2. **Verify endpoint:**
```bash
curl http://localhost:8181/health
curl http://localhost:8181/  # Try root
```

3. **Check OPA logs:**
```bash
docker logs opa-test
```

### Issue: Bundle status test fails

**Symptoms:**
```
✗ bundle_status
  No bundles loaded in OPA
```

**Solutions:**

1. **Check if bundles are configured:**
```bash
curl http://localhost:8181/v1/status
```

2. **Load policies manually:**
```bash
curl -X PUT --data-binary @policy.rego \
  http://localhost:8181/v1/policies/mypolicy
```

3. **Check bundle service:**
```bash
curl http://bundle-server:8080/bundles/bundle.tar.gz
```

4. **Skip bundle tests if not using bundles:**
```yaml
# config.yaml - remove bundle tests
# Or run specific category:
opa-test --mode category --category health
```

### Issue: Policy decision mismatch

**Symptoms:**
```
✗ policy_test_allow_admin
  Policy decision mismatch
  Expected: {'allow': True}
  Actual: {'allow': False}
```

**Solutions:**

1. **Test policy manually:**
```bash
curl -X POST http://localhost:8181/v1/data/example/allow \
  -H 'Content-Type: application/json' \
  -d '{"input": {"role": "admin"}}'
```

2. **Check policy is loaded:**
```bash
curl http://localhost:8181/v1/policies
```

3. **Verify input data:**
```yaml
# config.yaml
test_policies:
  - name: "test_allow_admin"
    policy_path: "example/allow"
    input:
      role: "admin"  # Check this matches policy expectations
```

4. **Check Rego syntax:**
```bash
opa check examples/policies/example.rego
```

### Issue: Authentication fails

**Symptoms:**
```
Error: OPA returned HTTP 401
```

**Solutions:**

1. **Verify token:**
```bash
curl -H "Authorization: Bearer $OPA_AUTH_TOKEN" \
  http://localhost:8181/health
```

2. **Check token in config:**
```yaml
# config.yaml
auth_token: "your-token-here"
```

Or:
```bash
export OPA_AUTH_TOKEN=your-token-here
```

3. **Check OPA auth configuration:**
```bash
# OPA should be started with --authentication=token
docker logs opa-test | grep authentication
```

---

## Docker Issues

### Issue: Docker build fails

**Symptoms:**
```
ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully
```

**Solutions:**

1. **Check Dockerfile syntax:**
```bash
docker build --no-cache -t opa-test-framework:latest .
```

2. **Check requirements.txt:**
```bash
cat requirements.txt
# Ensure all packages are valid
```

3. **Use specific Python version:**
```dockerfile
FROM python:3.11-slim  # Instead of :latest
```

### Issue: Container exits immediately

**Symptoms:**
```bash
docker-compose up -d opa
docker ps  # Container not running
```

**Solutions:**

1. **Check logs:**
```bash
docker-compose logs opa
```

2. **Run interactively:**
```bash
docker run -it --rm openpolicyagent/opa:latest run --server --addr :8181
```

3. **Check command:**
```yaml
# docker-compose.yml
command:
  - "run"
  - "--server"
  - "--addr=:8181"
  # Ensure command is correct
```

### Issue: Volume mount not working

**Symptoms:**
```
Policies not loaded in OPA
```

**Solutions:**

1. **Check volume path:**
```yaml
# docker-compose.yml
volumes:
  - ./examples/policies:/policies:ro  # Use absolute path if needed
```

2. **Verify files exist:**
```bash
ls -la examples/policies/
```

3. **Check permissions:**
```bash
chmod -R 755 examples/policies/
```

### Issue: Network issues between containers

**Symptoms:**
```
test-runner cannot connect to opa
```

**Solutions:**

1. **Use service names:**
```yaml
# docker-compose.yml
services:
  test-runner:
    environment:
      - OPA_URL=http://opa:8181  # Use service name, not localhost
```

2. **Check network:**
```bash
docker network ls
docker network inspect opa-test-framework_default
```

3. **Use depends_on:**
```yaml
services:
  test-runner:
    depends_on:
      opa:
        condition: service_healthy
```

---

## CI/CD Issues

### Issue: GitHub Actions workflow fails

**Symptoms:**
```
Error: OPA service not ready
```

**Solutions:**

1. **Check service health:**
```yaml
# .github/workflows/test.yml
services:
  opa:
    options: >-
      --health-cmd "wget --spider -q http://localhost:8181/health"
      --health-interval 5s
      --health-timeout 3s
      --health-retries 3
```

2. **Add wait step:**
```yaml
- name: Wait for OPA
  run: |
    timeout 30 bash -c 'until curl -f http://localhost:8181/health; do sleep 2; done'
```

3. **Check service logs:**
```yaml
- name: Debug OPA
  if: failure()
  run: |
    docker logs ${{ job.services.opa.id }}
```

### Issue: Secrets not available

**Symptoms:**
```
Error: OPA_URL is not set
```

**Solutions:**

1. **Add secrets in GitHub:**
   - Go to Settings → Secrets and variables → Actions
   - Add `STAGING_OPA_URL`, `PRODUCTION_OPA_URL`, etc.

2. **Use secrets in workflow:**
```yaml
env:
  OPA_URL: ${{ secrets.STAGING_OPA_URL }}
  OPA_AUTH_TOKEN: ${{ secrets.STAGING_OPA_TOKEN }}
```

3. **Check environment:**
```yaml
jobs:
  deploy:
    environment: staging  # Must match environment name
```

### Issue: Artifacts not uploaded

**Symptoms:**
```
Test results not visible in GitHub
```

**Solutions:**

1. **Check artifact path:**
```yaml
- name: Upload test results
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: test-results/  # Ensure path is correct
```

2. **Generate reports:**
```bash
opa-test --report-format junit --output test-results/results.xml
```

3. **Use always condition:**
```yaml
- name: Upload results
  if: always()  # Upload even if tests fail
  uses: actions/upload-artifact@v4
```

---

## Performance Issues

### Issue: Tests are slow

**Symptoms:**
```
Tests taking > 5 minutes
```

**Solutions:**

1. **Use smoke tests:**
```bash
opa-test --mode smoke  # < 30 seconds
```

2. **Reduce test iterations:**
```yaml
# For property-based tests
# Reduce from 100 to 10 iterations
```

3. **Check OPA performance:**
```bash
# Monitor OPA
docker stats opa-test

# Check OPA metrics
curl http://localhost:8181/metrics
```

4. **Increase timeout:**
```yaml
timeout_seconds: 30  # Increase if needed
```

---

## Getting Help

If you're still stuck:

1. **Check logs:**
```bash
# OPA logs
docker logs opa-test

# Test framework logs
opa-test --mode smoke --config config.yaml 2>&1 | tee test.log
```

2. **Enable debug mode:**
```bash
export OPA_LOG_LEVEL=debug
opa-test --mode smoke --config config.yaml
```

3. **Test manually:**
```bash
# Test OPA directly
curl -v http://localhost:8181/health
curl -v -X POST http://localhost:8181/v1/data/example/allow \
  -d '{"input": {"role": "admin"}}'
```

4. **Check documentation:**
- [README.md](README.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [TESTING.md](TESTING.md)

5. **Open an issue:**
- Include error messages
- Include configuration
- Include steps to reproduce
- Include environment details (OS, Python version, Docker version)
