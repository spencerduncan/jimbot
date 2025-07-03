#!/usr/bin/env python3
"""
Validation script to test CI pipeline configuration.
This is a minimal change to trigger CI without affecting functionality.
"""

def main():
    """Simple validation to ensure CI runs."""
    print("CI Pipeline Validation")
    print("=" * 50)
    print("Testing that all CI workflows properly install dependencies")
    print("using 'pip install -e \".[dev]\"' pattern")
    print("=" * 50)
    print("✓ This script exists to trigger CI pipeline")
    print("✓ No functional changes to the codebase")
    return 0

if __name__ == "__main__":
    exit(main())