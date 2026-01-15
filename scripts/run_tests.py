#!/usr/bin/env python
"""
ChartSense Test Runner
Run this before committing to ensure all tests pass.
Usage: python scripts/run_tests.py
"""
import subprocess
import sys
import os

# Colors for Windows console
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    END = '\033[0m'

def run_command(cmd, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("=" * 50)
    print("ChartSense Pre-Commit Test Suite")
    print("=" * 50)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_dir = os.path.join(root_dir, "api")

    all_passed = True

    # Test 1: Python syntax check
    print(f"\n{Colors.YELLOW}[1/3] Checking Python syntax...{Colors.END}")
    success, stdout, stderr = run_command("python -m py_compile main.py", cwd=api_dir)
    if success:
        print(f"{Colors.GREEN}✓ Python syntax OK{Colors.END}")
    else:
        print(f"{Colors.RED}✗ Syntax errors found{Colors.END}")
        print(stderr)
        all_passed = False

    # Test 2: Import check
    print(f"\n{Colors.YELLOW}[2/3] Checking imports...{Colors.END}")
    success, stdout, stderr = run_command(
        'python -c "from main import app; print(\'Imports OK\')"',
        cwd=api_dir
    )
    if success and "Imports OK" in stdout:
        print(f"{Colors.GREEN}✓ All imports successful{Colors.END}")
    else:
        print(f"{Colors.RED}✗ Import errors{Colors.END}")
        print(stderr)
        all_passed = False

    # Test 3: Run pytest
    print(f"\n{Colors.YELLOW}[3/3] Running API tests...{Colors.END}")
    success, stdout, stderr = run_command(
        "python -m pytest tests/ -v --tb=short",
        cwd=api_dir
    )
    print(stdout)
    if success:
        print(f"{Colors.GREEN}✓ All tests passed{Colors.END}")
    else:
        print(f"{Colors.RED}✗ Some tests failed{Colors.END}")
        all_passed = False

    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print(f"{Colors.GREEN}All checks passed! Safe to commit.{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}Some checks failed. Please fix before committing.{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
