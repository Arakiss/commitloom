import os
import pytest


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Set up environment variables for testing."""
    os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing"
    yield
    # Clean up
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"] 