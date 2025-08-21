"""Tests for git file operations."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from commitloom.core.git import GitError, GitOperations


@pytest.fixture
def git_operations():
    """Fixture for GitOperations instance."""
    return GitOperations()


@patch("subprocess.run")
def test_get_diff_text_files(mock_run, git_operations, mock_git_file):
    """Test getting diff for text files."""
    mock_diff = "diff --git a/file1.py b/file1.py\n+new line"
    mock_run.return_value = MagicMock(
        stdout=mock_diff,
        stderr="",
        returncode=0,
    )

    diff = git_operations.get_diff([mock_git_file("file1.py")])

    assert diff == mock_diff


@patch("subprocess.run")
def test_get_diff_binary_files(mock_run, git_operations, mock_git_file):
    """Test getting diff for binary files."""
    mock_run.return_value = MagicMock(
        stdout="Binary files a/image.png and b/image.png differ",
        stderr="",
        returncode=0,
    )

    diff = git_operations.get_diff([mock_git_file("image.png", size=1024, hash_="abc123")])

    assert "Binary files" in diff


@patch("subprocess.run")
def test_reset_staged_changes_success(mock_run, git_operations):
    """Test successful reset of staged changes."""
    mock_run.return_value = MagicMock(returncode=0)

    git_operations.reset_staged_changes()

    mock_run.assert_called_with(["git", "reset"], capture_output=True, text=True, check=True)


@patch("subprocess.run")
def test_reset_staged_changes_failure(mock_run, git_operations):
    """Test handling of reset failure."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr=b"error")

    with pytest.raises(GitError) as exc_info:
        git_operations.reset_staged_changes()

    assert "Failed to reset staged changes" in str(exc_info.value)


@patch("subprocess.run")
@patch("commitloom.core.git.logger")
def test_stage_files_with_warning(mock_logger, mock_run, git_operations):
    """Test handling of git warnings during staging."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stderr="warning: LF will be replaced by CRLF in file1.py",
        stdout="",
    )

    git_operations.stage_files(["file1.py"])

    # Verify warning was logged
    mock_logger.warning.assert_called_once_with(
        "Git warning while staging %s: %s",
        "file1.py",
        "warning: LF will be replaced by CRLF in file1.py",
    )


@patch("subprocess.run")
@patch("commitloom.core.git.logger")
def test_stage_files_with_info(mock_logger, mock_run, git_operations):
    """Test handling of git info messages during staging."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stderr="Updating index",
        stdout="",
    )

    git_operations.stage_files(["file1.py"])

    # Verify info was logged
    mock_logger.info.assert_called_once_with("Git message while staging %s: %s", "file1.py", "Updating index")
