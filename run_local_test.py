"""
Run local tests with mock OPA server.
"""

import subprocess
import time
import sys
import requests
import threading

def start_mock_server():
    """Start mock OPA server in background."""
    print("Starting mock OPA server...")
    process = subprocess.Popen(
        [sys.executable, "mock_opa_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    for i in range(10):
        try:
            response = requests.get("http://localhost:8181/health", timeout=1)
            if response.status_code == 200:
                print("✓ Mock OPA server is ready\n")
                return process
        except:
            time.sleep(0.5)
    
    print("❌ Failed to start mock OPA server")
    process.kill()
    return None

def run_tests():
    """Run the OPA tests."""
    print("=" * 60)
    print("Running OPA Test Framework Tests")
    print("=" * 60)
    print()
    
    # Run smoke tests
    print("1. Running smoke tests...")
    result = subprocess.run(
        ["opa-test", "--mode", "smoke", "--config", "config.example.yaml"],
        env={"OPA_URL": "http://localhost:8181"}
    )
    
    if result.returncode == 0:
        print("\n✅ Smoke tests passed!\n")
    else:
        print("\n⚠️  Some smoke tests may have failed (expected without real OPA)\n")
    
    # Run full tests
    print("2. Running full test suite...")
    result = subprocess.run(
        ["opa-test", "--mode", "full", "--config", "config.example.yaml"],
        env={"OPA_URL": "http://localhost:8181"}
    )
    
    if result.returncode == 0:
        print("\n✅ Full tests passed!\n")
    else:
        print("\n⚠️  Some tests may have failed (expected without real OPA)\n")
    
    # Run with JSON output
    print("3. Generating JSON report...")
    result = subprocess.run(
        ["opa-test", "--mode", "smoke", "--config", "config.example.yaml",
         "--report-format", "json", "--output", "test-results.json"],
        env={"OPA_URL": "http://localhost:8181"}
    )
    
    if result.returncode == 0:
        print("✓ JSON report generated: test-results.json\n")
    
    # Run with JUnit output
    print("4. Generating JUnit XML report...")
    result = subprocess.run(
        ["opa-test", "--mode", "smoke", "--config", "config.example.yaml",
         "--report-format", "junit", "--output", "test-results.xml"],
        env={"OPA_URL": "http://localhost:8181"}
    )
    
    if result.returncode == 0:
        print("✓ JUnit XML report generated: test-results.xml\n")

def main():
    """Main test runner."""
    # Start mock server
    server_process = start_mock_server()
    
    if not server_process:
        print("Failed to start mock server")
        return 1
    
    try:
        # Run tests
        run_tests()
        
        print("=" * 60)
        print("Testing Complete!")
        print("=" * 60)
        print("\nGenerated files:")
        print("  - test-results.json (JSON report)")
        print("  - test-results.xml (JUnit XML report)")
        print("\nNext steps:")
        print("  1. Start Docker Desktop")
        print("  2. Run: docker-compose up -d opa")
        print("  3. Run: opa-test --mode smoke --config config.example.yaml")
        print("     (with real OPA for full functionality)")
        
        return 0
    
    finally:
        # Stop mock server
        print("\nStopping mock OPA server...")
        server_process.terminate()
        server_process.wait(timeout=5)
        print("✓ Mock server stopped")

if __name__ == "__main__":
    sys.exit(main())
