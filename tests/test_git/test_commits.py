"""Tests for git commit operations."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from commitloom.core.git import GitError, GitOperations


@pytest.fixture
def git_operations():
    """Fixture for GitOperations instance."""
    return GitOperations()


@patch("subprocess.run")
def test_create_commit_success(mock_run, git_operations):
    """Test successful commit creation."""
    mock_run.side_effect = [
        # git diff --cached --quiet
        MagicMock(returncode=1),  # Non-zero means there are staged changes
        # git commit
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    result = git_operations.create_commit(
        title="test: add new feature", message="Detailed commit message"
    )

    assert result is True
    mock_run.assert_any_call(
        [
            "git",
            "commit",
            "-m",
            "test: add new feature",
            "-m",
            "Detailed commit message",
        ],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("subprocess.run")
def test_create_commit_failure(mock_run, git_operations):
    """Test handling of commit creation failure."""
    mock_run.side_effect = [
        # git diff --cached --quiet
        MagicMock(returncode=1),  # Non-zero means there are staged changes
        # git commit
        subprocess.CalledProcessError(1, "git", stderr=b"error"),
    ]

    with pytest.raises(GitError) as exc_info:
        git_operations.create_commit(title="test: add new feature", message="Detailed commit message")

    assert "Failed to create commit" in str(exc_info.value)


@patch("subprocess.run")
@patch("commitloom.core.git.logger")
def test_create_commit_with_warning(mock_logger, mock_run, git_operations):
    """Test handling of git warnings during commit."""
    mock_run.side_effect = [
        # git diff --cached --quiet
        MagicMock(returncode=1),  # Non-zero means there are staged changes
        # git commit
        MagicMock(returncode=0, stderr="warning: CRLF will be replaced by LF", stdout=""),
    ]

    result = git_operations.create_commit(title="test", message="message")

    assert result is True
    # Verify warning was logged
    mock_logger.warning.assert_called_once_with(
        "Git warning during commit: %s", "warning: CRLF will be replaced by LF"
    )


@patch("subprocess.run")
@patch("commitloom.core.git.logger")
def test_create_commit_nothing_to_commit(mock_logger, mock_run, git_operations):
    """Test handling of 'nothing to commit' message."""
    mock_run.return_value = MagicMock(
        returncode=0,  # Zero means no staged changes
        stderr="",
        stdout="nothing to commit, working tree clean",
    )

    result = git_operations.create_commit(title="test", message="message")

    assert result is False
    mock_logger.info.assert_called_once_with("Nothing to commit") 