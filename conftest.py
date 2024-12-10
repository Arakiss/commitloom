"""Global pytest configuration."""


def pytest_configure(config):
    """Configure pytest."""
    config.option.asyncio_mode = "strict"
    config.option.asyncio_fixture_mode = "function"
