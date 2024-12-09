"""Tests for basic git operations."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from commitloom.core.git import GitError, GitOperations


@pytest.fixture
def git_operations():
    """Fixture for GitOperations instance."""
    return GitOperations()


@patch("subprocess.run")
def test_get_staged_files_success(mock_run, git_operations, mock_git_file):
    """Test successful retrieval of staged files."""
    mock_run.return_value = MagicMock(
        stdout=" M file1.py\nM  file2.py\n",
        stderr="",
        returncode=0,
    )

    files = git_operations.get_staged_files()

    assert len(files) == 2
    assert files[0].path == "file1.py"
    assert files[0].status == "M"
    assert files[1].path == "file2.py"
    assert files[1].status == "M"


@patch("subprocess.run")
def test_get_staged_files_empty(mock_run, git_operations):
    """Test when no files are staged."""
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

    files = git_operations.get_staged_files()

    assert len(files) == 0


@patch("subprocess.run")
def test_get_staged_files_error(mock_run, git_operations):
    """Test error handling in get_staged_files."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr=b"error")

    with pytest.raises(GitError) as exc_info:
        git_operations.get_staged_files()

    assert "Failed to get staged files" in str(exc_info.value)


@patch("subprocess.run")
def test_get_staged_files_with_renames(mock_run, git_operations):
    """Test handling of renamed files."""
    mock_run.return_value = MagicMock(
        stdout='R  "old file.py" -> "new file.py"\n',
        stderr="",
        returncode=0,
    )

    files = git_operations.get_staged_files()

    assert len(files) == 1
    assert files[0].path == "new file.py"
    assert files[0].status == "R"
    assert files[0].old_path == "old file.py"


@patch("subprocess.run")
def test_get_staged_files_ignores_untracked(mock_run, git_operations):
    """Test that untracked files are ignored."""
    mock_run.return_value = MagicMock(
        stdout="?? new.py\n M tracked.py\n",
        stderr="",
        returncode=0,
    )

    files = git_operations.get_staged_files()

    assert len(files) == 1
    assert files[0].path == "tracked.py"
    assert files[0].status == "M"
