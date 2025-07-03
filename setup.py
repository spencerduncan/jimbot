#!/usr/bin/env python3
"""
Minimal setup.py for supporting editable installs with pyproject.toml
This file is required for pip install -e . to work properly
"""

from setuptools import setup, find_packages

# Read long description from README if it exists
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "JimBot - Sequential learning system for Balatro"

setup(
    name="jimbot",
    version="0.1.0",
    description="Sequential learning system for mastering Balatro using ML and AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="JimBot Team",
    author_email="noreply@jimbot.ai",
    url="https://github.com/spencerduncan/jimbot",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    python_requires=">=3.9",
    # Dependencies are managed in pyproject.toml
    # This setup.py is just for editable install support
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)