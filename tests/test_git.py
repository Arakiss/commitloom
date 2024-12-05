"""Tests for git operations module."""

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from commitloom.core.git import GitOperations, GitFile, GitError


@pytest.fixture
def git_operations():
    """Fixture for GitOperations instance."""
    return GitOperations()


def test_should_ignore_file():
    """Test file ignore patterns."""
    assert GitOperations.should_ignore_file("node_modules/package.json") is True
    assert GitOperations.should_ignore_file("src/main.py") is False
    assert GitOperations.should_ignore_file("package-lock.json") is True
    assert GitOperations.should_ignore_file(".env.local") is True


@patch("subprocess.check_output")
def test_get_changed_files_success(mock_check_output, git_operations):
    """Test successful retrieval of changed files."""
    mock_check_output.side_effect = [
        b"file1.py\nfile2.py",  # First call for diff
        b"100644 abc123 0\tfile1.py",  # Second call for file1
        b"100",  # Third call for file1 size
        b"100644 def456 0\tfile2.py",  # Fourth call for file2
        b"200",  # Fifth call for file2 size
    ]

    files = git_operations.get_changed_files()

    assert len(files) == 2
    assert isinstance(files[0], GitFile)
    assert files[0].path == "file1.py"
    assert files[0].size == 100
    assert files[0].hash == "abc123"
    assert files[1].path == "file2.py"
    assert files[1].size == 200
    assert files[1].hash == "def456"


@patch("subprocess.check_output")
def test_get_changed_files_empty(mock_check_output, git_operations):
    """Test when no files are changed."""
    mock_check_output.return_value = b""

    files = git_operations.get_changed_files()

    assert len(files) == 0


@patch("subprocess.check_output")
def test_get_changed_files_error(mock_check_output, git_operations):
    """Test handling of git command errors."""
    mock_check_output.side_effect = subprocess.CalledProcessError(1, "git", b"error")

    with pytest.raises(GitError) as exc_info:
        git_operations.get_changed_files()

    assert "Failed to get changed files" in str(exc_info.value)


@patch("subprocess.check_output")
def test_get_diff_text_files(mock_check_output, git_operations):
    """Test getting diff for text files."""
    mock_diff = b"diff --git a/file1.py b/file1.py\n+new line"
    mock_check_output.side_effect = [
        b"-\t-\t",  # numstat check
        mock_diff,  # actual diff
    ]

    diff = git_operations.get_diff([GitFile(path="file1.py")])

    assert diff == mock_diff.decode("utf-8")


@patch("subprocess.check_output")
def test_get_diff_binary_files(mock_check_output, git_operations):
    """Test getting diff for binary files."""
    mock_check_output.return_value = b"-\t-\tbinary.bin"

    diff = git_operations.get_diff(
        [GitFile(path="binary.bin", size=1024, hash="abc123")]
    )

    assert "Binary files changed:" in diff
    assert "binary.bin" in diff
    assert "1.00 KB" in diff


def test_format_file_size():
    """Test file size formatting."""
    assert GitOperations.format_file_size(100) == "100.00 B"
    assert GitOperations.format_file_size(1024) == "1.00 KB"
    assert GitOperations.format_file_size(1024 * 1024) == "1.00 MB"
    assert GitOperations.format_file_size(1024 * 1024 * 1024) == "1.00 GB"


@patch("subprocess.run")
def test_create_commit_success(mock_run, git_operations):
    """Test successful commit creation."""
    mock_run.return_value = MagicMock(returncode=0)

    result = git_operations.create_commit(
        "test: add new feature", "Detailed commit message"
    )

    assert result is True
    mock_run.assert_called_with(
        [
            "git",
            "commit",
            "-m",
            "test: add new feature",
            "-m",
            "Detailed commit message",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


@patch("subprocess.run")
def test_create_commit_with_files(mock_run, git_operations):
    """Test commit creation with specific files."""
    mock_run.return_value = MagicMock(returncode=0)

    result = git_operations.create_commit(
        "test: add new feature", "Detailed commit message", ["file1.py", "file2.py"]
    )

    assert result is True
    assert mock_run.call_count == 3  # 2 adds + 1 commit


@patch("subprocess.run")
def test_create_commit_failure(mock_run, git_operations):
    """Test handling of commit creation failure."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git", b"error")

    with pytest.raises(GitError) as exc_info:
        git_operations.create_commit("test: add new feature", "Detailed commit message")

    assert "Failed to create commit" in str(exc_info.value)


@patch("subprocess.run")
def test_reset_staged_changes_success(mock_run, git_operations):
    """Test successful reset of staged changes."""
    mock_run.return_value = MagicMock(returncode=0)

    git_operations.reset_staged_changes()

    mock_run.assert_called_with(["git", "reset"], check=True)


@patch("subprocess.run")
def test_reset_staged_changes_failure(mock_run, git_operations):
    """Test handling of reset failure."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git", b"error")

    with pytest.raises(GitError) as exc_info:
        git_operations.reset_staged_changes()

    assert "Failed to reset staged changes" in str(exc_info.value)
