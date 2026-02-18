# Windows Testing Guide

This guide shows you how to test the OPA Test Framework on Windows.

## ✅ What We've Verified

All framework components are working:
- ✅ CLI interface
- ✅ Configuration loading
- ✅ Test categories (Health, Bundle, Policy)
- ✅ Report generators (Console, JUnit, JSON)
- ✅ Result aggregation

## Testing Options

### Option 1: With Mock OPA Server (No Docker Required)

**Terminal 1 - Start Mock Server:**
```powershell
python mock_opa_server.py
```

**Terminal 2 - Run Tests:**
```powershell
# Smoke tests
opa-test --mode smoke --config config.example.yaml

# Full tests
opa-test --mode full --config config.example.yaml

# Generate reports
opa-test --mode smoke --config config.example.yaml --report-format json --output results.json
opa-test --mode smoke --config config.example.yaml --report-format junit --output results.xml
```

### Option 2: With Docker Desktop (Real OPA)

**Prerequisites:**
1. Install Docker Desktop for Windows
2. Start Docker Desktop (wait for it to fully start)

**Start OPA:**
```powershell
# Check Docker is running
docker ps

# Start OPA with example policies
docker run -d --name opa-test -p 8181:8181 `
  -v ${PWD}/examples/policies:/policies `
  openpolicyagent/opa:latest `
  run --server --addr :8181 /policies

# Wait a few seconds, then verify OPA is running
curl http://localhost:8181/health
```

**Run Tests:**
```powershell
# Smoke tests
opa-test --mode smoke --config config.example.yaml

# Full tests
opa-test --mode full --config config.example.yaml

# Specific category
opa-test --mode category --category health --config config.example.yaml
```

**Stop OPA:**
```powershell
docker stop opa-test
docker rm opa-test
```

### Option 3: With Docker Compose (Easiest with Docker)

**Start:**
```powershell
docker-compose up -d opa
```

**Run Tests:**
```powershell
# Set OPA URL
$env:OPA_URL="http://localhost:8181"

# Run tests
opa-test --mode smoke --config config.example.yaml
```

**Stop:**
```powershell
docker-compose down
```

## Quick Component Tests

Run these anytime to verify the framework:

```powershell
# Test all components
python test_local.py

# Test CLI and configuration
python test_cli_simple.py
```

## Common Commands

### Run Different Test Modes

```powershell
# Smoke tests (fast, critical tests only)
opa-test --mode smoke --config config.example.yaml

# Full test suite
opa-test --mode full --config config.example.yaml

# Specific category
opa-test --mode category --category health --config config.example.yaml
opa-test --mode category --category bundle --config config.example.yaml
opa-test --mode category --category policy --config config.example.yaml
```

### Generate Different Report Formats

```powershell
# Console output (default)
opa-test --mode smoke --config config.example.yaml

# JSON report
opa-test --mode smoke --config config.example.yaml `
  --report-format json --output results.json

# JUnit XML report (for CI/CD)
opa-test --mode smoke --config config.example.yaml `
  --report-format junit --output results.xml
```

### Use Environment Variables

```powershell
# Override OPA URL
$env:OPA_URL="http://localhost:8181"
opa-test --mode smoke --config config.example.yaml

# Override timeout
$env:OPA_TIMEOUT="20"
opa-test --mode smoke --config config.example.yaml

# Override auth token
$env:OPA_AUTH_TOKEN="your-token"
opa-test --mode smoke --config config.example.yaml
```

### CI Mode

```powershell
# Run in CI mode (proper exit codes)
opa-test --ci --mode smoke --config config.example.yaml

# Check exit code
echo $LASTEXITCODE
# 0 = all tests passed
# 1 = some tests failed
```

## Troubleshooting

### Docker Desktop Not Running

**Error:**
```
docker: request returned 500 Internal Server Error
```

**Solution:**
1. Open Docker Desktop
2. Wait for it to fully start (whale icon in system tray should be steady)
3. Try again

### Port 8181 Already in Use

**Error:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:8181: bind: Only one usage of each socket address
```

**Solution:**
```powershell
# Find what's using port 8181
netstat -ano | findstr :8181

# Stop the process or use a different port
docker run -d --name opa-test -p 8182:8181 ...

# Update config
$env:OPA_URL="http://localhost:8182"
```

### OPA Not Responding

**Check if OPA is running:**
```powershell
# Test health endpoint
curl http://localhost:8181/health

# Check Docker logs
docker logs opa-test

# Check Docker status
docker ps
```

### Configuration Errors

**Test configuration:**
```powershell
python -c "from src.opa_test_framework.config import load_config, validate_config; config = load_config('config.example.yaml'); print(validate_config(config))"
```

## Next Steps

### 1. Test with Mock Server (Easiest)

```powershell
# Terminal 1
python mock_opa_server.py

# Terminal 2
opa-test --mode smoke --config config.example.yaml
```

### 2. Test with Docker (Full Functionality)

```powershell
# Start Docker Desktop first!

# Start OPA
docker run -d --name opa-test -p 8181:8181 `
  -v ${PWD}/examples/policies:/policies `
  openpolicyagent/opa:latest `
  run --server --addr :8181 /policies

# Run tests
opa-test --mode smoke --config config.example.yaml

# Clean up
docker stop opa-test
docker rm opa-test
```

### 3. Customize Tests

Edit `config.example.yaml` to add your own policy tests:

```yaml
test_policies:
  - name: "my_custom_test"
    policy_path: "myapp/authorize"
    input:
      user: "alice"
      action: "read"
    expected_output:
      allow: true
```

### 4. Integrate with CI/CD

The framework is ready for GitHub Actions, GitLab CI, or Jenkins.
See `.github/workflows/` for examples.

## Summary

✅ **Framework is installed and working**
✅ **All components tested successfully**
✅ **Ready to test OPA deployments**

Choose your testing method:
- **Quick test**: Use mock server (no Docker needed)
- **Full test**: Use Docker Desktop with real OPA
- **Production**: Deploy to your environment and run tests

For more details, see:
- [README.md](README.md) - Overview
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [TESTING.md](TESTING.md) - Testing guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
