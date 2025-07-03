#!/usr/bin/env python3
"""Test that all required testing dependencies can be imported."""

import sys

def test_imports():
    """Test that all testing dependencies can be imported."""
    failed_imports = []
    
    test_packages = [
        "pytest",
        "pytest_cov",
        "pytest_mock", 
        "pytest_timeout",
        "pytest_asyncio",
        "pytest_benchmark",
        "pytest_xdist",
        "coverage",
        "hypothesis"
    ]
    
    for package in test_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError as e:
            failed_imports.append((package, str(e)))
            print(f"✗ {package}: {e}")
    
    if failed_imports:
        print(f"\n{len(failed_imports)} packages failed to import:")
        for pkg, err in failed_imports:
            print(f"  - {pkg}: {err}")
        sys.exit(1)
    else:
        print(f"\nAll {len(test_packages)} testing packages imported successfully!")
        sys.exit(0)

if __name__ == "__main__":
    test_imports()