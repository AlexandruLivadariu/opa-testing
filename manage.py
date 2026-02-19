#!/usr/bin/env python3
"""
Cross-platform management script for OPA Test Framework.
Replaces the Makefile for Windows compatibility.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from typing import List

# Constants
OPA_URL = "http://localhost:8181"
CONFIG_FILE = "config.example.yaml"


def run_command(command: List[str], cwd: str = None, env: dict = None, shell: bool = False, check: bool = True):
    """Run a shell command."""
    print(f"Running: {' '.join(command) if isinstance(command, list) else command}")
    try:
        subprocess.run(command, cwd=cwd, env=env, shell=shell, check=check)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(e.returncode)


def clean():
    """Clean up generated files."""
    print("Cleaning up...")
    dirs_to_remove = ["build", "dist", "test-results", "src/opa_test_framework.egg-info"]
    
    for d in dirs_to_remove:
        if os.path.exists(d):
            print(f"Removing {d}")
            shutil.rmtree(d)

    # Walk to remove __pycache__ and .pyc
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d))
        for f in files:
            if f.endswith(".pyc"):
                os.remove(os.path.join(root, f))


def install():
    """Install dependencies and package."""
    print("Installing dependencies...")
    run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Installing package in editable mode...")
    run_command([sys.executable, "-m", "pip", "install", "-e", "."])


def test():
    """Run all tests."""
    print("Running tests...")
    run_command([sys.executable, "-m", "pytest", "tests/", "-v"])


def smoke():
    """Run smoke tests against local OPA."""
    print("Running smoke tests...")
    env = os.environ.copy()
    env["OPA_URL"] = OPA_URL
    run_command(["opa-test", "--mode", "smoke", "--config", CONFIG_FILE], env=env, shell=True)


def full():
    """Run full test suite against local OPA."""
    print("Running full test suite...")
    env = os.environ.copy()
    env["OPA_URL"] = OPA_URL
    run_command(["opa-test", "--mode", "full", "--config", CONFIG_FILE], env=env, shell=True)


def docker_build():
    """Build Docker image."""
    run_command(["docker", "build", "-t", "opa-test-framework:latest", "."])


def docker_test():
    """Run tests in Docker."""
    run_command(["docker-compose", "up", "--abort-on-container-exit", "test-runner"])


def start_opa():
    """Start OPA using docker-compose and wait for it to be ready."""
    print("Starting OPA...")
    run_command(["docker-compose", "up", "-d", "opa"])
    
    print("Waiting for OPA to be ready...")
    start_time = time.time()
    timeout = 30
    
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"{OPA_URL}/health") as response:
                if response.status == 200:
                    print(f"✓ OPA is ready at {OPA_URL}")
                    break
        except Exception:
            time.sleep(2)
            continue
    else:
        print("OPA failed to start within timeout")
        sys.exit(1)

    print("Loading policies...")
    policies_dir = "examples/policies"
    if os.path.exists(policies_dir):
        for filename in os.listdir(policies_dir):
            if filename.endswith(".rego") and not filename.endswith("_test.rego"):
                policy_path = os.path.join(policies_dir, filename)
                policy_id = os.path.splitext(filename)[0]
                print(f"  Loading: {policy_id}")
                
                with open(policy_path, 'rb') as f:
                    data = f.read()
                
                req = urllib.request.Request(
                    f"{OPA_URL}/v1/policies/{policy_id}",
                    data=data,
                    method="PUT"
                )
                try:
                    with urllib.request.urlopen(req) as _:
                        pass
                except Exception as e:
                    print(f"Failed to load policy {policy_id}: {e}")


def stop_opa():
    """Stop OPA containers."""
    print("Stopping OPA...")
    run_command(["docker-compose", "down"])


def main():
    parser = argparse.ArgumentParser(description="Manage OPA Test Framework")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("install", help="Install dependencies")
    subparsers.add_parser("test", help="Run unit tests")
    subparsers.add_parser("smoke", help="Run smoke tests")
    subparsers.add_parser("full", help="Run full test suite")
    subparsers.add_parser("clean", help="Clean up artifacts")
    subparsers.add_parser("docker-build", help="Build Docker image")
    subparsers.add_parser("docker-test", help="Run tests in Docker")
    subparsers.add_parser("start-opa", help="Start OPA and load policies")
    subparsers.add_parser("stop-opa", help="Stop OPA")

    args = parser.parse_args()

    if args.command == "install":
        install()
    elif args.command == "test":
        test()
    elif args.command == "smoke":
        smoke()
    elif args.command == "full":
        full()
    elif args.command == "clean":
        clean()
    elif args.command == "docker-build":
        docker_build()
    elif args.command == "docker-test":
        docker_test()
    elif args.command == "start-opa":
        start_opa()
    elif args.command == "stop-opa":
        stop_opa()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
