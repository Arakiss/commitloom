"""Tests for console output module."""

from unittest.mock import MagicMock, patch

import pytest

from commitloom.cli.console import console
from commitloom.services.ai_service import CommitSuggestion, TokenUsage


@pytest.fixture
def mock_console():
    """Fixture for mocked console."""
    return MagicMock()


def test_print_changed_files(mock_console, mock_git_file):
    """Test printing changed files."""
    files = [
        mock_git_file("file1.py"),
        mock_git_file("file2.py"),
    ]

    console.print_changed_files(files)


def test_print_warnings():
    """Test printing warnings."""
    warnings = ["Warning 1", "Warning 2"]
    console.print_warnings(warnings)


def test_print_warnings_no_warnings():
    """Test printing empty warnings list."""
    console.print_warnings([])


def test_print_token_usage(mock_token_usage):
    """Test printing token usage."""
    console.print_token_usage(mock_token_usage)


def test_print_commit_message():
    """Test printing commit message."""
    suggestion = CommitSuggestion(
        title="✨ feat: add new feature",
        body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
        summary="test summary",
    )
    console.print_commit_message(suggestion)


def test_print_batch_info():
    """Test printing batch information."""
    console.print_batch_info(1, 3)


def test_confirm_action():
    """Test action confirmation."""
    with patch("click.confirm", return_value=True):
        assert console.confirm_action("Test action?") is True


def test_print_success():
    """Test printing success message."""
    console.print_success("Success message")


def test_print_error():
    """Test printing error message."""
    console.print_error("Error message")


def test_print_info():
    """Test printing info message."""
    console.print_info("Info message")


def test_print_warning():
    """Test printing warning message."""
    console.print_warning("Warning message")
