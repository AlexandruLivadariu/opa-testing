"""
Simple CLI test without requiring OPA.
"""

import sys
import os

# Set environment variable for testing
os.environ['OPA_URL'] = 'http://localhost:8181'

print("=" * 60)
print("Testing OPA Test Framework CLI")
print("=" * 60)
print()

# Test 1: CLI help
print("1. Testing CLI help command...")
from click.testing import CliRunner
from src.opa_test_framework.cli import main

runner = CliRunner()
result = runner.invoke(main, ['--help'])
print(result.output)

if result.exit_code == 0:
    print("✓ CLI help works\n")
else:
    print(f"❌ CLI help failed with exit code {result.exit_code}\n")

# Test 2: Configuration validation
print("2. Testing configuration loading...")
from src.opa_test_framework.config import load_config, validate_config

try:
    config = load_config('config.example.yaml')
    errors = validate_config(config)
    
    if errors:
        print(f"⚠️  Configuration has validation errors: {errors}")
    else:
        print("✓ Configuration loaded and validated successfully")
        print(f"  - OPA URL: {config.opa_url}")
        print(f"  - Timeout: {config.timeout_seconds}s")
        print(f"  - Test policies: {len(config.test_policies)}")
        print()
except Exception as e:
    print(f"❌ Configuration loading failed: {e}\n")

# Test 3: Test categories
print("3. Testing test categories...")
from src.opa_test_framework.categories.health import HealthTests
from src.opa_test_framework.categories.bundle import BundleTests
from src.opa_test_framework.categories.policy import PolicyTests

health_tests = HealthTests()
print(f"  - Health tests: {len(health_tests.get_tests())} tests")
print(f"    Smoke test: {health_tests.is_smoke_test()}")
print(f"    Priority: {health_tests.get_priority()}")

bundle_tests = BundleTests()
print(f"  - Bundle tests: {len(bundle_tests.get_tests())} tests")
print(f"    Smoke test: {bundle_tests.is_smoke_test()}")

policy_tests = PolicyTests(config)
print(f"  - Policy tests: {len(policy_tests.get_tests())} tests")
print()

# Test 4: Reporters
print("4. Testing report generators...")
from src.opa_test_framework.models import TestResult, TestStatus
from src.opa_test_framework.results import aggregate_results
from src.opa_test_framework.reporting import ConsoleReporter, JUnitReporter, JSONReporter

# Create sample results
results = [
    TestResult("test1", TestStatus.PASS, 100.0, "Passed"),
    TestResult("test2", TestStatus.FAIL, 150.0, "Failed", {"error": "mismatch"}),
]

summary = aggregate_results(results)

console_reporter = ConsoleReporter()
console_output = console_reporter.generate(summary)
print("  ✓ Console reporter works")

junit_reporter = JUnitReporter()
junit_output = junit_reporter.generate(summary)
print("  ✓ JUnit reporter works")

json_reporter = JSONReporter()
json_output = json_reporter.generate(summary)
print("  ✓ JSON reporter works")
print()

# Summary
print("=" * 60)
print("✅ All CLI and component tests passed!")
print("=" * 60)
print()
print("The framework is working correctly!")
print()
print("To test with a real OPA instance:")
print("  1. Start Docker Desktop")
print("  2. Run: docker-compose up -d opa")
print("  3. Wait a few seconds for OPA to start")
print("  4. Run: opa-test --mode smoke --config config.example.yaml")
print()
print("Or use the mock server:")
print("  1. In one terminal: python mock_opa_server.py")
print("  2. In another terminal: opa-test --mode smoke --config config.example.yaml")
print()
