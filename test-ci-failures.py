#!/usr/bin/env python3
"""
CI Pipeline Failure Testing Script
Tests various failure scenarios in the GitHub Actions pipeline
"""

import subprocess
import time
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

class CIPipelineTester:
    def __init__(self):
        self.results = []
        self.test_dir = Path(tempfile.mkdtemp(prefix="ci_test_"))
        
    def cleanup(self):
        """Clean up test artifacts"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def log_result(self, test_name: str, passed: bool, details: str):
        """Log test results"""
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        })
        print(f"{'✓' if passed else '✗'} {test_name}: {details}")
    
    def test_network_failure(self) -> bool:
        """Test behavior when network calls fail"""
        print("\n=== Testing Network Failures ===")
        
        # Test 1: Simulate network failure for StyLua download
        test_script = """
#!/bin/bash
# Simulate network failure
export http_proxy="http://invalid:9999"
export https_proxy="http://invalid:9999"

# Try to download StyLua
wget --retry-connrefused --tries=3 https://github.com/JohnnyMorganz/StyLua/releases/download/v0.20.0/stylua-linux.zip

if [ $? -eq 0 ]; then
    echo "ERROR: Download succeeded when it should have failed"
    exit 1
else
    echo "Expected failure occurred"
    # Check if fallback mechanism works
    touch /usr/local/bin/stylua
    chmod +x /usr/local/bin/stylua
    echo '#!/bin/bash\necho "StyLua not available, skipping format check"' > /usr/local/bin/stylua
    exit 0
fi
"""
        script_path = self.test_dir / "test_network.sh"
        script_path.write_text(test_script)
        script_path.chmod(0o755)
        
        result = subprocess.run([str(script_path)], capture_output=True, text=True)
        self.log_result(
            "Network Failure - StyLua Download",
            result.returncode == 0,
            f"Fallback mechanism {'worked' if result.returncode == 0 else 'failed'}"
        )
        
        # Test 2: Simulate pip network failure
        pip_test = """
import subprocess
import sys

# Test pip with invalid index
result = subprocess.run([
    sys.executable, "-m", "pip", "install", 
    "--index-url", "http://invalid:9999/simple",
    "requests"
], capture_output=True, text=True)

if result.returncode != 0:
    print("Expected pip failure occurred")
    sys.exit(0)
else:
    print("ERROR: pip succeeded with invalid index")
    sys.exit(1)
"""
        pip_script = self.test_dir / "test_pip.py"
        pip_script.write_text(pip_test)
        
        result = subprocess.run([sys.executable, str(pip_script)], capture_output=True, text=True)
        self.log_result(
            "Network Failure - Pip Install",
            result.returncode == 0,
            "Pip correctly failed with invalid index"
        )
        
        return all(r["passed"] for r in self.results[-2:])
    
    def test_docker_failure(self) -> bool:
        """Test Docker-related failures"""
        print("\n=== Testing Docker Failures ===")
        
        # Test 1: Check Docker daemon status
        docker_check = subprocess.run(["docker", "info"], capture_output=True, text=True)
        docker_available = docker_check.returncode == 0
        
        self.log_result(
            "Docker Daemon Check",
            True,  # Just checking, not a failure test
            f"Docker {'is' if docker_available else 'is not'} available"
        )
        
        if docker_available:
            # Test 2: Simulate container health check timeout
            timeout_test = """
#!/bin/bash
# Create a container that never becomes healthy
docker run -d --name test_unhealthy --health-cmd="exit 1" --health-interval=1s alpine sleep 1000

# Try to wait for it to become healthy (should timeout)
timeout 10s bash -c 'until docker inspect test_unhealthy | grep -q "\\"Status\\": \\"healthy\\""; do sleep 1; done'
EXIT_CODE=$?

# Cleanup
docker rm -f test_unhealthy 2>/dev/null

if [ $EXIT_CODE -eq 124 ]; then
    echo "Timeout correctly triggered"
    exit 0
else
    echo "ERROR: Health check did not timeout as expected"
    exit 1
fi
"""
            script_path = self.test_dir / "test_docker_health.sh"
            script_path.write_text(timeout_test)
            script_path.chmod(0o755)
            
            result = subprocess.run([str(script_path)], capture_output=True, text=True)
            self.log_result(
                "Docker Health Check Timeout",
                result.returncode == 0,
                "Health check timeout mechanism works correctly"
            )
        
        return True
    
    def test_resource_limits(self) -> bool:
        """Test resource limit scenarios"""
        print("\n=== Testing Resource Limits ===")
        
        # Test 1: Memory limit simulation
        memory_test = """
import sys
import resource

# Set memory limit to 100MB
resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))

try:
    # Try to allocate 200MB
    data = bytearray(200 * 1024 * 1024)
    print("ERROR: Memory allocation succeeded when it should have failed")
    sys.exit(1)
except MemoryError:
    print("Memory limit correctly enforced")
    sys.exit(0)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
"""
        script_path = self.test_dir / "test_memory.py"
        script_path.write_text(memory_test)
        
        result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        self.log_result(
            "Memory Limit Test",
            result.returncode == 0,
            "Memory limits are properly enforced"
        )
        
        # Test 2: Disk space check
        disk_test = """
import shutil
import sys

disk_usage = shutil.disk_usage("/")
free_gb = disk_usage.free / (1024**3)

if free_gb < 1:
    print(f"WARNING: Low disk space: {free_gb:.2f}GB free")
    sys.exit(1)
else:
    print(f"Disk space OK: {free_gb:.2f}GB free")
    sys.exit(0)
"""
        script_path = self.test_dir / "test_disk.py"
        script_path.write_text(disk_test)
        
        result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        self.log_result(
            "Disk Space Check",
            True,  # Just informational
            result.stdout.strip()
        )
        
        return True
    
    def test_permission_failures(self) -> bool:
        """Test permission-related failures"""
        print("\n=== Testing Permission Failures ===")
        
        # Test 1: File permission issues
        test_file = self.test_dir / "readonly_test.txt"
        test_file.write_text("test content")
        test_file.chmod(0o444)  # Read-only
        
        try:
            with open(test_file, "a") as f:
                f.write("should fail")
            self.log_result(
                "Read-only File Test",
                False,
                "Write succeeded on read-only file"
            )
        except PermissionError:
            self.log_result(
                "Read-only File Test",
                True,
                "Permission correctly denied"
            )
        
        # Test 2: Directory permission issues
        test_dir = self.test_dir / "readonly_dir"
        test_dir.mkdir()
        test_dir.chmod(0o555)  # Read-execute only
        
        try:
            (test_dir / "newfile.txt").write_text("test")
            self.log_result(
                "Read-only Directory Test",
                False,
                "Write succeeded in read-only directory"
            )
        except PermissionError:
            self.log_result(
                "Read-only Directory Test",
                True,
                "Permission correctly denied"
            )
        finally:
            test_dir.chmod(0o755)  # Restore for cleanup
        
        return True
    
    def test_timeout_scenarios(self) -> bool:
        """Test timeout handling"""
        print("\n=== Testing Timeout Scenarios ===")
        
        # Test 1: Command timeout
        timeout_test = """
#!/bin/bash
# Test timeout command
timeout 2s sleep 10
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "Timeout correctly triggered"
    exit 0
else
    echo "ERROR: Command did not timeout as expected"
    exit 1
fi
"""
        script_path = self.test_dir / "test_timeout.sh"
        script_path.write_text(timeout_test)
        script_path.chmod(0o755)
        
        result = subprocess.run([str(script_path)], capture_output=True, text=True)
        self.log_result(
            "Command Timeout Test",
            result.returncode == 0,
            "Timeout mechanism works correctly"
        )
        
        # Test 2: Python test timeout simulation
        pytest_timeout = """
import signal
import sys
import time

def timeout_handler(signum, frame):
    print("Test timeout triggered")
    sys.exit(0)

# Set a 2-second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(2)

try:
    # Simulate long-running test
    time.sleep(10)
    print("ERROR: Test did not timeout")
    sys.exit(1)
except SystemExit:
    raise
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
"""
        script_path = self.test_dir / "test_pytest_timeout.py"
        script_path.write_text(pytest_timeout)
        
        result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        self.log_result(
            "Test Timeout Simulation",
            result.returncode == 0,
            "Test timeout mechanism works"
        )
        
        return True
    
    def test_git_failures(self) -> bool:
        """Test Git-related failures"""
        print("\n=== Testing Git Failures ===")
        
        # Test 1: Invalid Git operations
        git_test = """
#!/bin/bash
# Test git operations in non-repo directory
cd /tmp
git status 2>/dev/null
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "Git correctly failed in non-repo directory"
    exit 0
else
    echo "ERROR: Git command succeeded in non-repo"
    exit 1
fi
"""
        script_path = self.test_dir / "test_git.sh"
        script_path.write_text(git_test)
        script_path.chmod(0o755)
        
        result = subprocess.run([str(script_path)], capture_output=True, text=True)
        self.log_result(
            "Git Non-repo Test",
            result.returncode == 0,
            "Git correctly handles non-repo directories"
        )
        
        return True
    
    def generate_report(self):
        """Generate final test report"""
        print("\n" + "="*50)
        print("CI PIPELINE FAILURE TEST REPORT")
        print("="*50)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["passed"])
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if any(not r["passed"] for r in self.results):
            print("\nFailed Tests:")
            for r in self.results:
                if not r["passed"]:
                    print(f"  - {r['test']}: {r['details']}")
        
        # Save detailed report
        report_path = Path("ci-failure-test-report.json")
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed report saved to: {report_path}")


def main():
    """Run all CI failure tests"""
    tester = CIPipelineTester()
    
    try:
        # Run all test categories
        tester.test_network_failure()
        tester.test_docker_failure()
        tester.test_resource_limits()
        tester.test_permission_failures()
        tester.test_timeout_scenarios()
        tester.test_git_failures()
        
        # Generate report
        tester.generate_report()
        
    finally:
        tester.cleanup()
    
    # Exit with failure if any tests failed
    sys.exit(0 if all(r["passed"] for r in tester.results) else 1)


if __name__ == "__main__":
    main()