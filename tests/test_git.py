"""Tests for git operations module."""

import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from commitloom.core.git import GitError, GitFile, GitOperations


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
    # Mock successful status, add and commit operations
    mock_run.side_effect = [
        # git status call
        MagicMock(stdout=" M file1.py\n M file2.py\n", stderr="", returncode=0),
        # git add file1.py
        MagicMock(returncode=0, stderr=""),
        # git add file2.py
        MagicMock(returncode=0, stderr=""),
        # git commit
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    result = git_operations.create_commit(
        "test: add new feature", "Detailed commit message", ["file1.py", "file2.py"]
    )

    assert result is True
    assert mock_run.call_count == 4  # status + 2 adds + 1 commit


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


@patch("subprocess.run")
@patch("commitloom.core.git.logger")
def test_stage_files_with_warning(mock_logger, mock_run, git_operations):
    """Test handling of git warnings during staging."""
    mock_run.side_effect = [
        # git status call
        MagicMock(stdout=" M file1.py\n", stderr="", returncode=0),
        # git add call
        MagicMock(
            returncode=0, stderr="warning: LF will be replaced by CRLF in file1.py"
        ),
    ]

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
    mock_run.side_effect = [
        # git status call
        MagicMock(stdout=" M file1.py\n", stderr="", returncode=0),
        # git add call
        MagicMock(returncode=0, stderr="Updating index"),
    ]

    git_operations.stage_files(["file1.py"])

    # Verify info was logged
    mock_logger.info.assert_called_once_with(
        "Git message while staging %s: %s", "file1.py", "Updating index"
    )


@patch("subprocess.run")
@patch("commitloom.core.git.logger")
def test_create_commit_with_warning(mock_logger, mock_run, git_operations):
    """Test handling of git warnings during commit."""
    mock_run.return_value = MagicMock(
        returncode=0, stderr="warning: CRLF will be replaced by LF", stdout=""
    )

    result = git_operations.create_commit("test", "message")

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
        returncode=0, stderr="", stdout="nothing to commit, working tree clean"
    )

    result = git_operations.create_commit("test", "message")

    assert result is False
    # Verify info was logged
    mock_logger.info.assert_called_once_with("No changes to commit")


@patch("subprocess.run")
def test_stage_deleted_files(mock_run):
    """Test staging deleted files."""
    # Mock git status to show a deleted file
    mock_run.side_effect = [
        # git status call
        MagicMock(stdout=" D file1.txt\n M file2.txt\n", stderr="", returncode=0),
        # git rm call for deleted file
        MagicMock(stdout="", stderr="", returncode=0),
        # git add call for modified file
        MagicMock(stdout="", stderr="", returncode=0),
    ]

    GitOperations.stage_files(["file1.txt", "file2.txt"])

    # Verify correct commands were called
    assert mock_run.call_args_list == [
        call(
            ["git", "status", "--porcelain"], check=True, capture_output=True, text=True
        ),
        call(["git", "rm", "file1.txt"], check=True, capture_output=True, text=True),
        call(["git", "add", "file2.txt"], check=True, capture_output=True, text=True),
    ]


@patch("subprocess.run")
def test_stage_nonexistent_file(mock_run):
    """Test staging a file that doesn't exist in git status."""
    # Mock git status with no files
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

    GitOperations.stage_files(["nonexistent.txt"])

    # Verify only status was checked
    mock_run.assert_called_once_with(
        ["git", "status", "--porcelain"], check=True, capture_output=True, text=True
    )


@patch("subprocess.run")
def test_get_changed_files_error(mock_run, git_operations):
    """Test error handling in get_changed_files."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "git diff", stderr=b"fatal: not a git repository"
    )

    with pytest.raises(GitError, match="Failed to get changed files"):
        git_operations.get_changed_files()


@patch("subprocess.run")
def test_get_changed_files_binary(mock_run, git_operations):
    """Test handling binary files in get_changed_files."""
    # Mock ls-files to fail for binary file
    mock_run.side_effect = [
        # git diff call
        MagicMock(stdout=b"binary.bin\n"),
        # ls-files call fails
        subprocess.CalledProcessError(128, "git ls-files", stderr=b"error"),
        # cat-file call fails
        subprocess.CalledProcessError(128, "git cat-file", stderr=b"error"),
    ]

    files = git_operations.get_changed_files()
    assert len(files) == 1
    assert files[0].path == "binary.bin"
    assert files[0].size is None
    assert files[0].hash is None


@patch("subprocess.run")
def test_stage_files_error(mock_run, git_operations):
    """Test error handling in stage_files."""
    mock_run.side_effect = [
        # git status call
        MagicMock(stdout=" M file1.py\n", stderr="", returncode=0),
        # git add call fails
        subprocess.CalledProcessError(
            128, "git add", stderr=b"fatal: pathspec 'file1.py' did not match any files"
        ),
    ]

    with pytest.raises(GitError, match="Error staging file1.py"):
        git_operations.stage_files(["file1.py"])


@patch("subprocess.run")
def test_create_commit_nothing_to_commit(mock_run, git_operations):
    """Test create_commit when there's nothing to commit."""
    mock_run.side_effect = [
        # git status call
        MagicMock(stdout="", stderr="", returncode=0),
        # git commit call
        subprocess.CalledProcessError(
            1, "git commit", stderr=b"nothing to commit, working tree clean"
        ),
    ]

    result = git_operations.create_commit("test", "message")
    assert result is False


@patch("subprocess.run")
def test_reset_staged_changes(mock_run, git_operations):
    """Test resetting staged changes."""
    mock_run.return_value = MagicMock(returncode=0)

    git_operations.reset_staged_changes()

    mock_run.assert_called_once_with(["git", "reset"], check=True)


@patch("subprocess.run")
def test_reset_staged_changes_error(mock_run, git_operations):
    """Test error handling when resetting staged changes."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "git reset", stderr=b"fatal: not a git repository"
    )

    with pytest.raises(GitError, match="Failed to reset staged changes"):
        git_operations.reset_staged_changes()


@patch("subprocess.run")
def test_stash_changes(mock_run, git_operations):
    """Test stashing changes."""
    mock_run.return_value = MagicMock(returncode=0)

    git_operations.stash_changes()

    mock_run.assert_called_once_with(
        ["git", "stash", "-u"], check=True, capture_output=True, text=True
    )


@patch("subprocess.run")
def test_stash_changes_error(mock_run, git_operations):
    """Test error handling when stashing changes."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "git stash", stderr=b"fatal: not a git repository"
    )

    with pytest.raises(GitError, match="Failed to stash changes"):
        git_operations.stash_changes()


@patch("subprocess.run")
def test_pop_stashed_changes(mock_run, git_operations):
    """Test popping stashed changes."""
    mock_run.return_value = MagicMock(returncode=0)

    git_operations.pop_stashed_changes()

    mock_run.assert_called_once_with(
        ["git", "stash", "pop"], check=True, capture_output=True, text=True
    )


@patch("subprocess.run")
def test_pop_stashed_changes_no_stash(mock_run, git_operations):
    """Test popping stashed changes when there's no stash."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "git stash pop", stderr=b"No stash entries found."
    )

    # Should not raise an error
    git_operations.pop_stashed_changes()


@patch("subprocess.run")
def test_pop_stashed_changes_error(mock_run, git_operations):
    """Test error handling when popping stashed changes."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "git stash pop", stderr=b"fatal: not a git repository"
    )

    with pytest.raises(GitError, match="Failed to pop stashed changes"):
        git_operations.pop_stashed_changes()
