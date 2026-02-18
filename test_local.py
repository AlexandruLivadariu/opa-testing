"""
Quick local test script to verify the framework works.
This tests the framework components without requiring a running OPA instance.
"""

import sys
from src.opa_test_framework.config import TestConfig, PolicyTest, validate_config
from src.opa_test_framework.models import TestResult, TestStatus, TestResultsSummary
from src.opa_test_framework.results import aggregate_results
from src.opa_test_framework.reporting import ConsoleReporter, JUnitReporter, JSONReporter

def test_configuration():
    """Test configuration loading and validation."""
    print("Testing configuration...")
    
    # Create a test config
    config = TestConfig(
        opa_url="http://localhost:8181",
        timeout_seconds=10,
        test_policies=[
            PolicyTest(
                name="test_allow",
                policy_path="example/allow",
                input={"role": "admin"},
                expected_output={"allow": True}
            )
        ]
    )
    
    # Validate config
    errors = validate_config(config)
    if errors:
        print(f"  ❌ Configuration validation failed: {errors}")
        return False
    
    print("  ✓ Configuration validation passed")
    return True

def test_result_aggregation():
    """Test result aggregation."""
    print("\nTesting result aggregation...")
    
    # Create some test results
    results = [
        TestResult(
            test_name="test1",
            status=TestStatus.PASS,
            duration_ms=100.0,
            message="Test passed"
        ),
        TestResult(
            test_name="test2",
            status=TestStatus.PASS,
            duration_ms=150.0,
            message="Test passed"
        ),
        TestResult(
            test_name="test3",
            status=TestStatus.FAIL,
            duration_ms=200.0,
            message="Test failed"
        ),
    ]
    
    # Aggregate results
    summary = aggregate_results(results)
    
    # Verify aggregation
    assert summary.total_tests == 3, "Total tests should be 3"
    assert summary.passed == 2, "Passed tests should be 2"
    assert summary.failed == 1, "Failed tests should be 1"
    assert summary.duration_seconds == 0.45, "Duration should be 0.45s"
    assert not summary.success, "Summary should not be successful"
    
    print("  ✓ Result aggregation works correctly")
    return True

def test_reporters():
    """Test report generators."""
    print("\nTesting reporters...")
    
    # Create test results
    results = [
        TestResult(
            test_name="health_check",
            status=TestStatus.PASS,
            duration_ms=45.23,
            message="Health check passed"
        ),
        TestResult(
            test_name="policy_test",
            status=TestStatus.FAIL,
            duration_ms=123.45,
            message="Policy decision mismatch",
            details={"expected": {"allow": True}, "actual": {"allow": False}}
        ),
    ]
    
    summary = aggregate_results(results)
    
    # Test console reporter
    console_reporter = ConsoleReporter()
    console_report = console_reporter.generate(summary)
    assert "OPA Test Results" in console_report
    assert "health_check" in console_report
    assert "policy_test" in console_report
    print("  ✓ Console reporter works")
    
    # Test JUnit reporter
    junit_reporter = JUnitReporter()
    junit_report = junit_reporter.generate(summary)
    assert "<testsuite" in junit_report
    assert "<testcase" in junit_report
    assert "<failure" in junit_report
    print("  ✓ JUnit reporter works")
    
    # Test JSON reporter
    json_reporter = JSONReporter()
    json_report = json_reporter.generate(summary)
    assert '"total_tests": 2' in json_report
    assert '"passed": 1' in json_report
    assert '"failed": 1' in json_report
    print("  ✓ JSON reporter works")
    
    return True

def test_cli_import():
    """Test that CLI can be imported."""
    print("\nTesting CLI import...")
    
    try:
        from src.opa_test_framework import cli
        print("  ✓ CLI module imports successfully")
        return True
    except Exception as e:
        print(f"  ❌ CLI import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("OPA Test Framework - Local Component Tests")
    print("=" * 60)
    
    tests = [
        test_configuration,
        test_result_aggregation,
        test_reporters,
        test_cli_import,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ All component tests passed!")
        print("\nNext steps:")
        print("1. Start Docker Desktop")
        print("2. Run: docker-compose up -d opa")
        print("3. Run: opa-test --mode smoke --config config.example.yaml")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
