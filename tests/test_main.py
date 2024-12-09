"""Tests for CLI handler module."""

import subprocess
import sys
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from commitloom.__main__ import main
from commitloom.cli.cli_handler import CommitLoom
from commitloom.core.analyzer import CommitAnalysis, Warning, WarningLevel
from commitloom.core.git import GitError, GitFile
from commitloom.services.ai_service import CommitSuggestion


@pytest.fixture
def commit_loom():
    """Fixture for CommitLoom instance with mocked dependencies."""
    with (
        patch("commitloom.cli.cli_handler.GitOperations") as mock_git,
        patch("commitloom.cli.cli_handler.CommitAnalyzer") as mock_analyzer,
        patch("commitloom.cli.cli_handler.AIService") as mock_ai,
        patch("commitloom.cli.cli_handler.load_dotenv"),
    ):
        instance = CommitLoom()
        instance.git = mock_git.return_value
        instance.analyzer = mock_analyzer.return_value
        instance.ai_service = mock_ai.return_value
        return instance


@patch("subprocess.run")
@patch("commitloom.cli.console.confirm_action")
def test_process_files_in_batches_single_batch(mock_confirm, mock_run, commit_loom):
    """Test processing files when they fit in a single batch."""
    # Setup test data
    files = [
        GitFile(path="file1.py", status="M"),
        GitFile(path="file2.py", status="M"),
    ]

    # Mock git status and ignore check
    def mock_git_status(cmd, **kwargs):
        if "status" in cmd and "--porcelain" in cmd:
            # Return both files as modified in a single line
            return MagicMock(stdout="M  file1.py\nM  file2.py\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    mock_run.side_effect = mock_git_status
    commit_loom.git.should_ignore_file.return_value = False  # Don't ignore test files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.estimate_tokens_and_cost.return_value = (100, 0.01)
    commit_loom.analyzer.config.token_limit = 1000
    commit_loom.analyzer.config.max_files_threshold = 5  # Ensure we can fit both files in one batch

    # Create a properly configured TokenUsage mock
    token_usage_mock = MagicMock()
    token_usage_mock.prompt_tokens = 100
    token_usage_mock.completion_tokens = 50
    token_usage_mock.total_tokens = 150
    token_usage_mock.input_cost = 0.01
    token_usage_mock.output_cost = 0.02
    token_usage_mock.total_cost = 0.03

    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        token_usage_mock,
    )
    mock_confirm.return_value = True

    commit_loom.process_files_in_batches(files)
    assert commit_loom.git.create_commit.called


@patch("subprocess.run")
@patch("commitloom.cli.console.confirm_action")
def test_process_files_in_batches_multiple_batches(mock_confirm, mock_run, commit_loom):
    """Test processing files that need to be split into multiple batches."""
    # Setup test data
    files = [GitFile(path=f"file{i}.py", status="M") for i in range(10)]

    # Mock git status and ignore check
    def mock_git_status(cmd, **kwargs):
        if "status" in cmd and "--porcelain" in cmd:
            # Return all files as modified
            status_lines = [f" M file{i}.py" for i in range(10)]
            return MagicMock(stdout="\n".join(status_lines) + "\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    mock_run.side_effect = mock_git_status
    commit_loom.git.should_ignore_file.return_value = False  # Don't ignore test files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.estimate_tokens_and_cost.return_value = (1000, 0.01)
    commit_loom.analyzer.config.token_limit = 1000  # Set lower to force batching

    # Create a properly configured TokenUsage mock
    token_usage_mock = MagicMock()
    token_usage_mock.prompt_tokens = 100
    token_usage_mock.completion_tokens = 50
    token_usage_mock.total_tokens = 150
    token_usage_mock.input_cost = 0.01
    token_usage_mock.output_cost = 0.02
    token_usage_mock.total_cost = 0.03

    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        token_usage_mock,
    )
    mock_confirm.return_value = True

    # Set max_files_threshold to 5 to force multiple batches
    commit_loom.analyzer.config.max_files_threshold = 5

    commit_loom.process_files_in_batches(files)
    assert commit_loom.git.create_commit.call_count == 4  # Should create 4 commits for 10 files


@patch("commitloom.cli.console.print_success")
def test_create_combined_commit(mock_print_success, commit_loom):
    """Test creating a combined commit from multiple batches."""
    # Mock format_commit_message to return a formatted string
    commit_loom.ai_service.format_commit_message.return_value = (
        "📦 chore: combine multiple changes\n\n" "✨ Features:\n"
    )

    batches = [
        {
            "files": [GitFile(path="file1.py", status="M")],
            "commit_data": CommitSuggestion(
                title="feat: first change",
                body={"Features": {"emoji": "✨", "changes": ["Change 1"]}},
                summary="First summary",
            ),
        },
        {
            "files": [GitFile(path="file2.py", status="M")],
            "commit_data": CommitSuggestion(
                title="fix: second change",
                body={"Fixes": {"emoji": "🐛", "changes": ["Fix 1"]}},
                summary="Second summary",
            ),
        },
    ]

    commit_loom._create_combined_commit(batches)

    # Verify that git.create_commit was called with the correct arguments
    commit_loom.git.create_commit.assert_called_once()
    args = commit_loom.git.create_commit.call_args[0]

    assert args[0] == "📦 chore: combine multiple changes"
    assert "Features" in args[1]
    assert "Fixes" in args[1]
    assert "Change 1" in args[1]
    assert "Fix 1" in args[1]
    assert "First summary Second summary" in args[1]

    # Verify success message was printed
    mock_print_success.assert_called_once_with("Combined commit created successfully!")


@patch("commitloom.cli.cli_handler.console")
def test_run_no_changes(mock_console, commit_loom):
    """Test run when there are no changes."""
    commit_loom.git.get_staged_files.return_value = []

    commit_loom.run()

    mock_console.print_warning.assert_called_once_with("No files staged for commit.")


@patch("commitloom.cli.cli_handler.console")
def test_run_simple_change(mock_console, commit_loom):
    """Test run with a simple change."""
    # Setup test data
    files = [GitFile(path="test.py", status="M")]
    commit_loom.git.get_staged_files.return_value = files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.analyze_diff_complexity.return_value = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=1,
        warnings=[],
        is_complex=False,
    )
    commit_loom.analyzer.config.max_files_threshold = 5  # Set higher than number of files
    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        MagicMock(),
    )
    mock_console.confirm_action.return_value = True
    commit_loom.git.create_commit.return_value = True

    commit_loom.run()

    # Verify that success message was printed
    mock_console.print_success.assert_called()


@patch("commitloom.cli.cli_handler.console")
def test_run_with_warnings(mock_console, commit_loom):
    """Test run with complexity warnings."""
    # Setup test data
    files = [GitFile(path="test.py", status="M")]
    commit_loom.git.get_staged_files.return_value = files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.analyze_diff_complexity.return_value = CommitAnalysis(
        estimated_tokens=1000,
        estimated_cost=0.05,
        num_files=1,
        warnings=[Warning(level=WarningLevel.HIGH, message="Test warning")],
        is_complex=True,
    )

    # First confirm (for warnings) returns False
    mock_console.confirm_action.return_value = False

    commit_loom.run()

    # Verify all expected messages were printed
    mock_console.print_warnings.assert_called_once()


@patch("commitloom.cli.cli_handler.console")
def test_run_with_warnings_continue(mock_console, commit_loom):
    """Test run with warnings when user chooses to continue."""
    # Setup test data
    files = [GitFile(path="test.py", status="M")]
    commit_loom.git.get_staged_files.return_value = files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.analyze_diff_complexity.return_value = CommitAnalysis(
        estimated_tokens=1000,
        estimated_cost=0.05,
        num_files=1,
        warnings=[Warning(level=WarningLevel.HIGH, message="Test warning")],
        is_complex=True,
    )
    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        MagicMock(),
    )

    # User chooses to continue despite warnings
    mock_console.confirm_action.side_effect = [True, True]

    commit_loom.run()

    # Verify expected messages and actions
    mock_console.print_warnings.assert_called_once()
    commit_loom.git.create_commit.assert_called_once()


@patch("commitloom.cli.cli_handler.console")
def test_run_commit_error(mock_console, commit_loom):
    """Test run when commit creation fails."""
    # Setup test data
    files = [GitFile(path="test.py", status="M")]
    commit_loom.git.get_staged_files.return_value = files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.analyze_diff_complexity.return_value = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=1,
        warnings=[],
        is_complex=False,
    )
    commit_loom.analyzer.config.max_files_threshold = 5  # Set higher than number of files
    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        MagicMock(),
    )
    mock_console.confirm_action.return_value = True
    commit_loom.git.create_commit.side_effect = GitError("Failed to create commit")

    commit_loom.run()

    # Verify that error message was printed
    mock_console.print_error.assert_called()


@patch("commitloom.cli.cli_handler.console")
def test_run_with_exception(mock_console, commit_loom):
    """Test run when an exception occurs."""
    commit_loom.git.get_staged_files.side_effect = GitError("Test error")

    commit_loom.run()

    mock_console.print_error.assert_called_with("An unexpected error occurred: Test error")


@patch("commitloom.cli.cli_handler.CommitLoom")
def test_cli_arguments(mock_commit_loom):
    """Test CLI argument parsing using Click."""
    runner = CliRunner()

    # Test help text
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Create structured git commits" in result.output

    # Test with no arguments (default values)
    mock_commit_loom.return_value.run.return_value = None
    result = runner.invoke(main, [])
    assert result.exit_code == 0

    # Test with all flags
    result = runner.invoke(main, ["-y", "-c", "-d"])
    assert result.exit_code == 0

    # Test with long form arguments
    result = runner.invoke(main, ["--yes", "--combine", "--debug"])
    assert result.exit_code == 0

    # Verify CommitLoom was called with correct arguments
    mock_commit_loom.return_value.run.assert_called_with(auto_commit=True, combine_commits=True, debug=True)


@patch("sys.exit")
@patch("commitloom.cli.cli_handler.console")
@patch("commitloom.cli.cli_handler.CommitLoom")
def test_main_keyboard_interrupt(mock_commit_loom, mock_console, mock_exit):
    """Test handling of KeyboardInterrupt in main."""
    runner = CliRunner()
    mock_commit_loom.return_value.run.side_effect = KeyboardInterrupt()

    result = runner.invoke(main)
    mock_console.print_error.assert_called_with("\nOperation cancelled by user.")
    mock_exit.assert_called_with(1)


@patch("sys.exit")
@patch("commitloom.cli.cli_handler.console")
@patch("commitloom.cli.cli_handler.CommitLoom")
def test_main_exception_verbose(mock_commit_loom, mock_console, mock_exit):
    """Test handling of exceptions in main with verbose logging."""
    runner = CliRunner()
    mock_commit_loom.return_value.run.side_effect = Exception("Test error")

    result = runner.invoke(main, ["-d"])
    mock_console.print_error.assert_called_with("An error occurred: Test error")
    mock_exit.assert_called_with(1)


@patch("commitloom.cli.console.confirm_action", return_value=False)
def test_process_files_in_batches_with_commit_error(mock_confirm, commit_loom):
    """Test handling of commit creation error."""
    # Setup test data
    files = [GitFile(path="file1.py", status="M")]
    commit_loom.git.get_diff.return_value = "test diff"

    # Mock token usage
    token_usage_mock = MagicMock()
    token_usage_mock.prompt_tokens = 100
    token_usage_mock.completion_tokens = 50
    token_usage_mock.total_tokens = 150
    token_usage_mock.input_cost = 0.01
    token_usage_mock.output_cost = 0.02
    token_usage_mock.total_cost = 0.03

    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        token_usage_mock,
    )

    # Mock create_commit to return False (indicating no changes)
    commit_loom.git.create_commit.return_value = False

    commit_loom.process_files_in_batches(files)
    assert commit_loom.git.reset_staged_changes.called


def test_process_files_in_batches_with_git_error(commit_loom):
    """Test handling of git error during batch processing."""
    # Setup test data
    files = [GitFile(path="file1.py", status="M")]
    commit_loom.git.stage_files.side_effect = GitError("Git error")

    commit_loom.process_files_in_batches(files)
    assert commit_loom.git.reset_staged_changes.called


@patch("subprocess.run")
@patch("commitloom.cli.console.confirm_action")
def test_process_files_in_batches_user_cancel(mock_confirm, mock_run, commit_loom):
    """Test user cancellation during batch processing."""
    # Setup test data
    files = [GitFile(path="file1.py", status="M")]

    # Mock git status and ignore check
    def mock_git_status(cmd, **kwargs):
        if "status" in cmd and "--porcelain" in cmd:
            return MagicMock(stdout=" M file1.py\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    mock_run.side_effect = mock_git_status
    commit_loom.git.should_ignore_file.return_value = False  # Don't ignore test files
    commit_loom.git.get_diff.return_value = "test diff"

    # Mock token usage
    token_usage_mock = MagicMock()
    token_usage_mock.prompt_tokens = 100
    token_usage_mock.completion_tokens = 50
    token_usage_mock.total_tokens = 150
    token_usage_mock.input_cost = 0.01
    token_usage_mock.output_cost = 0.02
    token_usage_mock.total_cost = 0.03

    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        token_usage_mock,
    )

    # Mock user cancellation
    mock_confirm.return_value = False

    commit_loom.process_files_in_batches(files)
    assert commit_loom.git.reset_staged_changes.called


def test_process_files_in_batches_empty_input(commit_loom):
    """Test processing with no files."""
    commit_loom.process_files_in_batches([])
    assert not commit_loom.git.create_commit.called


@patch("subprocess.run")
def test_create_batches_with_invalid_files(mock_run, commit_loom):
    """Test batch creation with invalid files."""
    # Mock git status to return empty for invalid file
    mock_run.return_value = MagicMock(stdout="", returncode=0)

    files = [GitFile(path="invalid.py", status="M")]
    batches = commit_loom._create_batches(files)
    assert len(batches) == 0


@patch("subprocess.run")
def test_create_batches_with_mixed_files(mock_run, commit_loom):
    """Test batch creation with mix of valid and invalid files."""

    def mock_git_status(cmd, **kwargs):
        if "status" in cmd and "--porcelain" in cmd:
            # Return a properly formatted git status output with a modified file
            return MagicMock(stdout="M  valid.py\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    mock_run.side_effect = mock_git_status
    commit_loom.git.should_ignore_file.side_effect = lambda x: x == "invalid.py"

    files = [GitFile(path="valid.py", status="M"), GitFile(path="invalid.py", status="M")]
    batches = commit_loom._create_batches(files)
    assert len(batches) == 1
    assert len(batches[0]) == 1
    assert batches[0][0].path == "valid.py"


@patch("subprocess.run")
def test_create_batches_with_git_error(mock_run, commit_loom):
    """Test batch creation when git command fails."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git status", stderr=b"error")

    files = [GitFile(path="file.py", status="M")]
    batches = commit_loom._create_batches(files)
    assert len(batches) == 0
