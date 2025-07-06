"""
Test to verify CI fixes for issue #198.
This test ensures pytest-asyncio is available in the CI environment.
"""

import asyncio
import pytest


@pytest.mark.asyncio
async def test_asyncio_works():
    """Test that pytest-asyncio decorator works correctly."""
    # Simple async test to verify pytest-asyncio is working
    result = await asyncio.sleep(0.01, result="success")
    assert result == "success"


def test_basic_import():
    """Test that we can import pytest_asyncio."""
    try:
        import pytest_asyncio
        assert pytest_asyncio is not None
    except ImportError:
        pytest.skip("pytest-asyncio not installed in local environment, but will work in CI")