"""Tests for console output and user interaction."""

from unittest.mock import MagicMock, patch

import pytest

from commitloom.cli import console
from commitloom.core.analyzer import CommitAnalysis, Warning, WarningLevel
from commitloom.core.git import GitFile
from commitloom.services.ai_service import CommitSuggestion


@pytest.fixture
def mock_console(mocker):
    """Fixture for mocked console."""
    return mocker.patch("commitloom.cli.console.console")


def test_print_changed_files(mock_console, mock_git_file):
    """Test printing changed files."""
    files = [
        mock_git_file("file1.py"),
        mock_git_file("file2.py"),
    ]

    console.print_changed_files(files)

    mock_console.print.assert_called()


def test_print_warnings():
    """Test printing warnings."""
    warnings = [
        Warning(level=WarningLevel.HIGH, message="Warning 1"),
        Warning(level=WarningLevel.MEDIUM, message="Warning 2"),
    ]
    analysis = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=2,
        warnings=warnings,
        is_complex=False,
    )
    console.print_warnings(analysis)


def test_print_warnings_no_warnings():
    """Test printing empty warnings list."""
    analysis = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=2,
        warnings=[],
        is_complex=False,
    )
    console.print_warnings(analysis)


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
    console.print_commit_message(suggestion.format_body())


def test_print_batch_info():
    """Test printing batch information."""
    files = ["file1.py", "file2.py"]
    console.print_batch_info(1, files)


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
