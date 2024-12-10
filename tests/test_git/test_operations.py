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


def test_get_staged_files_with_spaces(git_operations):
    """Test getting staged files with spaces in paths."""
    mock_output = "M  path with spaces/file.py\n" "A  another path/with spaces.py\n"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_output, stderr="", returncode=0)
        files = git_operations.get_staged_files()

    assert len(files) == 2
    assert files[0].path == "path with spaces/file.py"
    assert files[1].path == "another path/with spaces.py"


def test_get_staged_files_with_special_chars(git_operations):
    """Test getting staged files with special characters."""
    mock_output = (
        "M  path/with-dashes.py\n" "A  path/with_underscores.py\n" "M  path/with.dots.py\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_output, stderr="", returncode=0)
        files = git_operations.get_staged_files()

    assert len(files) == 3
    assert files[0].path == "path/with-dashes.py"
    assert files[1].path == "path/with_underscores.py"
    assert files[2].path == "path/with.dots.py"


def test_get_staged_files_with_unicode(git_operations):
    """Test getting staged files with unicode characters."""
    mock_output = "M  path/with/émoji/🚀.py\n" "A  path/with/áccents/file.py\n"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_output, stderr="", returncode=0)
        files = git_operations.get_staged_files()

    assert len(files) == 2
    assert files[0].path == "path/with/émoji/🚀.py"
    assert files[1].path == "path/with/áccents/file.py"


def test_get_staged_files_with_warnings(git_operations):
    """Test getting staged files with git warnings."""
    mock_output = "M  file.py\n"
    mock_warning = "warning: CRLF will be replaced by LF in file.py"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_output, stderr=mock_warning, returncode=0)
        files = git_operations.get_staged_files()

    assert len(files) == 1
    assert files[0].path == "file.py"


def test_get_staged_files_with_binary_detection(git_operations):
    """Test getting staged files with binary file detection."""
    mock_output = "M  text.py\n" "M  image.png\n"

    def mock_run_side_effect(*args, **kwargs):
        if args[0][0] == "git" and args[0][1] == "status":
            return MagicMock(stdout=mock_output, stderr="", returncode=0)
        elif args[0][0] == "git" and args[0][1] == "diff":
            # Return binary file indicator for image.png
            if "image.png" in args[0]:
                return MagicMock(stdout="-\t-\timage.png\n", stderr="", returncode=0)
            return MagicMock(stdout="1\t1\ttext.py\n", stderr="", returncode=0)
        elif args[0][0] == "git" and args[0][1] == "hash-object":
            return MagicMock(stdout="abc123\n", stderr="", returncode=0)
        return MagicMock(stdout="", stderr="", returncode=0)

    with patch("subprocess.run", side_effect=mock_run_side_effect):
        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=1024):
                files = git_operations.get_staged_files()

    assert len(files) == 2
    assert not files[0].is_binary
    assert files[1].is_binary
    assert files[1].size == 1024
    assert files[1].hash == "abc123"


def test_get_staged_files_with_complex_renames(git_operations):
    """Test getting staged files with complex rename scenarios."""
    mock_output = (
        "R  old_name.py -> new_name.py\n"
        "R  old/path/file.py -> new/path/file.py\n"
        "R100  renamed_completely.py -> totally_different.py\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_output, stderr="", returncode=0)
        files = git_operations.get_staged_files()

    assert len(files) == 3
    assert all(f.status == "R" for f in files)
    assert files[0].path == "new_name.py"
    assert files[1].path == "new/path/file.py"
    assert files[2].path == "totally_different.py"


def test_get_staged_files_with_submodules(git_operations):
    """Test getting staged files with submodule changes."""
    mock_output = (
        "M  regular_file.py\n" "M  submodule\n"  # Submodule change
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_output, stderr="", returncode=0)
        files = git_operations.get_staged_files()

    assert len(files) == 2
    assert files[0].path == "regular_file.py"
    assert files[1].path == "submodule"


def test_get_staged_files_with_permission_changes(git_operations):
    """Test getting staged files with permission changes."""
    mock_output = "M  file_with_chmod.sh\n"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_output, stderr="", returncode=0)
        files = git_operations.get_staged_files()

    assert len(files) == 1
    assert files[0].path == "file_with_chmod.sh"
