#!/usr/bin/env python3
"""
Test script to verify that all testing dependencies can be imported.
This helps validate that pyproject.toml properly declares all dependencies.
"""

import sys
import importlib

# List of modules that should be available when dev dependencies are installed
TEST_MODULES = [
    "pytest",
    "pytest_asyncio",
    "pytest_cov", 
    "pytest_mock",
    "pytest_timeout",
    "pytest_benchmark",
    "pytest_xdist",
    "coverage",
    "hypothesis",
    "black",
    "isort", 
    "ruff",
    "flake8",
    "mypy",
    "pylint",
    "pydocstyle",
    "bandit",
    "safety",
]

def test_import(module_name):
    """Try to import a module and return success status."""
    try:
        importlib.import_module(module_name)
        print(f"✓ {module_name}")
        return True
    except ImportError as e:
        print(f"✗ {module_name}: {e}")
        return False

def main():
    """Test all required imports."""
    print("Testing dev dependency imports...\n")
    
    failures = []
    for module in TEST_MODULES:
        if not test_import(module):
            failures.append(module)
    
    print(f"\nSummary: {len(TEST_MODULES) - len(failures)}/{len(TEST_MODULES)} modules imported successfully")
    
    if failures:
        print(f"\nFailed imports: {', '.join(failures)}")
        print("\nTo fix, run: pip install -e '.[dev]'")
        sys.exit(1)
    else:
        print("\nAll dev dependencies are properly installed!")
        sys.exit(0)

if __name__ == "__main__":
    main()