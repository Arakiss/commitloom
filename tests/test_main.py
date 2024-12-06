"""Tests for main CLI module."""

import argparse
import subprocess
import sys
from unittest.mock import MagicMock, call, patch

import pytest

from commitloom.cli.main import CommitLoom, create_parser, main
from commitloom.core.analyzer import CommitAnalysis, Warning, WarningLevel
from commitloom.core.git import GitError, GitFile
from commitloom.services.ai_service import CommitSuggestion


@pytest.fixture
def commit_loom():
    """Fixture for CommitLoom instance with mocked dependencies."""
    with patch("commitloom.cli.main.GitOperations") as mock_git, patch(
        "commitloom.cli.main.CommitAnalyzer"
    ) as mock_analyzer, patch("commitloom.cli.main.AIService") as mock_ai, patch(
        "commitloom.cli.main.load_dotenv"
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
        GitFile(path="file1.py"),
        GitFile(path="file2.py"),
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

    result = commit_loom.process_files_in_batches(files, auto_commit=False)
    assert len(result) == 1
    assert len(result[0]["files"]) == 2
    assert result[0]["files"][0].path == "file1.py"
    assert result[0]["files"][1].path == "file2.py"


@patch("subprocess.run")
@patch("commitloom.cli.console.confirm_action")
def test_process_files_in_batches_multiple_batches(mock_confirm, mock_run, commit_loom):
    """Test processing files that need to be split into multiple batches."""
    # Setup test data
    files = [GitFile(path=f"file{i}.py") for i in range(10)]

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

    result = commit_loom.process_files_in_batches(files, auto_commit=False)
    assert len(result) == 2  # Should be split into 2 batches of 5 files each
    assert len(result[0]["files"]) == 5
    assert len(result[1]["files"]) == 5


@patch("commitloom.cli.console.print_success")
def test_create_combined_commit(mock_print_success, commit_loom):
    """Test creating a combined commit from multiple batches."""
    # Mock format_commit_message to return a formatted string
    commit_loom.ai_service.format_commit_message.return_value = (
        "📦 chore: combine multiple changes\n\n"
        "✨ Features:\n"
    )

    batches = [
        {
            "files": [GitFile(path="file1.py")],
            "commit_data": CommitSuggestion(
                title="feat: first change",
                body={"Features": {"emoji": "✨", "changes": ["Change 1"]}},
                summary="First summary",
            ),
        },
        {
            "files": [GitFile(path="file2.py")],
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


@patch("commitloom.cli.main.console")
def test_run_no_changes(mock_console, commit_loom):
    """Test run when there are no changes."""
    commit_loom.git.get_changed_files.return_value = []

    commit_loom.run()

    mock_console.print_error.assert_called_once_with(
        "No changes detected in the staging area."
    )


@patch("commitloom.cli.main.console")
def test_run_simple_change(mock_console, commit_loom):
    """Test run with a simple change."""
    # Setup test data
    files = [GitFile(path="test.py")]
    commit_loom.git.get_changed_files.return_value = files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.analyze_diff_complexity.return_value = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=1,
        warnings=[],
        is_complex=False,
    )
    commit_loom.analyzer.config.max_files_threshold = (
        5  # Set higher than number of files
    )
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


@patch("commitloom.cli.main.console")
def test_run_with_warnings(mock_console, commit_loom):
    """Test run with complexity warnings."""
    # Setup test data
    files = [GitFile(path="test.py")]
    commit_loom.git.get_changed_files.return_value = files
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
    mock_console.print_info.assert_has_calls(
        [
            call("Analyzing your changes..."),
            call("Process cancelled. Please review your changes."),
        ]
    )
    mock_console.print_warnings.assert_called_once()


@patch("commitloom.cli.main.console")
def test_run_with_warnings_continue(mock_console, commit_loom):
    """Test run with warnings when user chooses to continue."""
    # Setup test data
    files = [GitFile(path="test.py")]
    commit_loom.git.get_changed_files.return_value = files
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
    mock_console.print_info.assert_has_calls(
        [call("Analyzing your changes..."), call("\nGenerated Commit Message:")]
    )
    commit_loom.git.create_commit.assert_called_once()


@patch("commitloom.cli.main.console")
def test_run_commit_error(mock_console, commit_loom):
    """Test run when commit creation fails."""
    # Setup test data
    files = [GitFile(path="test.py")]
    commit_loom.git.get_changed_files.return_value = files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.analyze_diff_complexity.return_value = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=1,
        warnings=[],
        is_complex=False,
    )
    commit_loom.analyzer.config.max_files_threshold = (
        5  # Set higher than number of files
    )
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


@patch("commitloom.cli.main.console")
def test_run_with_exception(mock_console, commit_loom):
    """Test run when an exception occurs."""
    commit_loom.git.get_changed_files.side_effect = GitError("Test error")

    commit_loom.run()

    mock_console.print_error.assert_called_with("An error occurred: Test error")


def test_cli_arguments():
    """Test CLI argument parsing."""
    parser = create_parser()

    # Test command names in help text
    help_text = parser.format_help()
    assert "loom" in help_text and "cl" in help_text, "Help text should mention both command names"

    # Test default values
    args = parser.parse_args([])
    assert not args.yes
    assert not args.combine
    assert not args.verbose

    # Test setting all flags
    args = parser.parse_args(["-y", "-c", "-v"])
    assert args.yes
    assert args.combine
    assert args.verbose

    # Test long form arguments
    args = parser.parse_args(["--yes", "--combine", "--verbose"])
    assert args.yes
    assert args.combine
    assert args.verbose


@patch("commitloom.cli.main.console")
@patch("commitloom.cli.main.CommitLoom")
@patch("commitloom.cli.main.create_parser")
def test_main_keyboard_interrupt(mock_create_parser, mock_commit_loom, mock_console):
    """Test handling of KeyboardInterrupt in main."""
    # Setup mock parser that always returns empty args
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = argparse.Namespace(
        yes=False, combine=False, verbose=False
    )
    mock_create_parser.return_value = mock_parser

    mock_commit_loom.return_value.run.side_effect = KeyboardInterrupt()

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    mock_console.print_error.assert_called_with("\nOperation cancelled by user.")


@patch("commitloom.cli.main.console")
@patch("commitloom.cli.main.CommitLoom")
def test_main_exception_verbose(mock_commit_loom, mock_console):
    """Test handling of exceptions in main with verbose logging."""
    mock_commit_loom.return_value.run.side_effect = Exception("Test error")

    # Mock sys.argv to include verbose flag
    with patch.object(sys, "argv", ["commitloom", "-v"]):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    mock_console.print_error.assert_called_with("An error occurred: Test error")


def test_process_files_in_batches_with_commit_error(commit_loom):
    """Test handling of commit creation error."""
    # Setup test data
    files = [GitFile(path="file1.py")]
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

    result = commit_loom.process_files_in_batches(files, auto_commit=True)
    assert len(result) == 0


def test_process_files_in_batches_with_git_error(commit_loom):
    """Test handling of git error during batch processing."""
    # Setup test data
    files = [GitFile(path="file1.py")]
    commit_loom.git.stage_files.side_effect = GitError("Git error")

    result = commit_loom.process_files_in_batches(files, auto_commit=True)
    assert len(result) == 0


@patch("subprocess.run")
@patch("commitloom.cli.console.confirm_action")
def test_process_files_in_batches_user_cancel(mock_confirm, mock_run, commit_loom):
    """Test user cancellation during batch processing."""
    # Setup test data
    files = [GitFile(path="file1.py")]

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

    result = commit_loom.process_files_in_batches(files, auto_commit=False)
    assert len(result) == 0
    commit_loom.git.reset_staged_changes.assert_called_once()


def test_process_files_in_batches_empty_input(commit_loom):
    """Test processing with no files."""
    result = commit_loom.process_files_in_batches([], auto_commit=True)
    assert len(result) == 0


@patch("subprocess.run")
def test_create_batches_with_invalid_files(mock_run, commit_loom):
    """Test batch creation with invalid files."""
    # Mock git status to return empty for invalid file
    mock_run.return_value = MagicMock(
        stdout="",
        returncode=0
    )

    files = [GitFile(path="invalid.py")]
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

    files = [
        GitFile(path="valid.py"),
        GitFile(path="invalid.py")
    ]
    batches = commit_loom._create_batches(files)
    assert len(batches) == 1
    assert len(batches[0]) == 1
    assert batches[0][0].path == "valid.py"


@patch("subprocess.run")
def test_create_batches_with_git_error(mock_run, commit_loom):
    """Test batch creation when git command fails."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git status", stderr=b"error")

    files = [GitFile(path="file.py")]
    batches = commit_loom._create_batches(files)
    assert len(batches) == 0
