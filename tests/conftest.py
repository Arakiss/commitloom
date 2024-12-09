"""Common test fixtures."""

from unittest.mock import MagicMock

import pytest

from commitloom.core.git import GitFile


@pytest.fixture
def mock_git_file():
    """Fixture for creating GitFile instances."""
    def _create_git_file(path: str, status: str = "M", size: int = None, hash_: str = None):
        file = GitFile(path=path, status=status)
        if size is not None:
            file.size = size
        if hash_ is not None:
            file.hash = hash_
        return file
    return _create_git_file


@pytest.fixture
def mock_token_usage():
    """Fixture for token usage mock."""
    mock = MagicMock()
    mock.prompt_tokens = 100
    mock.completion_tokens = 50
    mock.total_tokens = 150
    mock.input_cost = 0.01
    mock.output_cost = 0.02
    mock.total_cost = 0.03
    return mock


@pytest.fixture
def mock_deps(mocker):
    """Fixture for mocked dependencies."""
    mock_git = mocker.patch("commitloom.cli.cli_handler.GitOperations", autospec=True)
    mock_analyzer = mocker.patch("commitloom.cli.cli_handler.CommitAnalyzer", autospec=True)
    mock_ai = mocker.patch("commitloom.cli.cli_handler.AIService", autospec=True)
    mocker.patch("commitloom.cli.cli_handler.load_dotenv")

    # Configure analyzer mock
    mock_analyzer.return_value.config.token_limit = 1000
    mock_analyzer.return_value.config.max_files_threshold = 5

    return {
        "git": mock_git.return_value,
        "analyzer": mock_analyzer.return_value,
        "ai": mock_ai.return_value,
    }
