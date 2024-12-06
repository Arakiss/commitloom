"""Tests for main CLI module."""

import pytest
from unittest.mock import patch, MagicMock, call

from commitloom.cli.main import CommitLoom, main, create_parser
from commitloom.core.git import GitFile, GitError
from commitloom.services.ai_service import CommitSuggestion
from commitloom.core.analyzer import CommitAnalysis, Warning, WarningLevel
import argparse
import sys


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


@patch("commitloom.cli.console.confirm_action")
def test_process_files_in_batches_single_batch(mock_confirm, commit_loom):
    """Test processing files when they fit in a single batch."""
    # Setup test data
    files = [
        GitFile(path="file1.py"),
        GitFile(path="file2.py"),
    ]
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.estimate_tokens_and_cost.return_value = (100, 0.01)
    commit_loom.analyzer.config.token_limit = 1000
    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        MagicMock(),  # TokenUsage mock
    )
    mock_confirm.return_value = True

    result = commit_loom.process_files_in_batches(files)

    assert len(result) == 1
    assert result[0]["files"] == files


@patch("commitloom.cli.console.confirm_action")
def test_process_files_in_batches_multiple_batches(mock_confirm, commit_loom):
    """Test processing files that need to be split into multiple batches."""
    # Setup test data
    files = [GitFile(path=f"file{i}.py") for i in range(10)]
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.estimate_tokens_and_cost.return_value = (1000, 0.01)
    commit_loom.analyzer.config.token_limit = 1000  # Set lower to force batching
    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        MagicMock(),
    )
    mock_confirm.return_value = True

    # Set max_files_threshold to 5 to force multiple batches
    commit_loom.analyzer.config.max_files_threshold = 5

    result = commit_loom.process_files_in_batches(files)

    assert len(result) == 2  # Should split into 2 batches of 5 files each
    assert len(result[0]["files"]) == 5
    assert len(result[1]["files"]) == 5


@patch("commitloom.cli.console.print_success")
def test_create_combined_commit(mock_print_success, commit_loom):
    """Test creating a combined commit from multiple batches."""
    # Mock format_commit_message to return a formatted string
    commit_loom.ai_service.format_commit_message.return_value = """📦 chore: combine multiple changes

✨ Features:
- Change 1

🐛 Fixes:
- Fix 1

First summary Second summary"""

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


@patch("commitloom.cli.main.console")
def test_batch_processing(mock_console, commit_loom):
    """Test processing files in batches."""
    # Setup test data with more files than threshold
    files = [GitFile(path=f"test{i}.py") for i in range(6)]  # 6 files
    commit_loom.analyzer.config.max_files_threshold = 5  # Set threshold to 5

    commit_loom.git.get_changed_files.return_value = files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.analyze_diff_complexity.return_value = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=6,
        warnings=[],
        is_complex=False,
    )

    # Mock AI service responses for each batch
    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        MagicMock(),
    )

    # User confirms individual commits
    mock_console.confirm_action.side_effect = [True, True, True]
    mock_console.confirm_batch_continue.return_value = True

    commit_loom.run()

    # Verify batch processing occurred
    assert mock_console.print_batch_info.call_count > 0
    assert commit_loom.git.create_commit.call_count > 0


@patch("commitloom.cli.main.console")
def test_combined_commits(mock_console, commit_loom):
    """Test combining multiple commits into one."""
    # Setup test data with more files than threshold
    files = [GitFile(path=f"test{i}.py") for i in range(6)]
    commit_loom.analyzer.config.max_files_threshold = 5

    commit_loom.git.get_changed_files.return_value = files
    commit_loom.git.get_diff.return_value = "test diff"
    commit_loom.analyzer.analyze_diff_complexity.return_value = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=6,
        warnings=[],
        is_complex=False,
    )

    # Mock AI service responses for batches
    commit_loom.ai_service.generate_commit_message.return_value = (
        CommitSuggestion(
            title="test commit",
            body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
            summary="test summary",
        ),
        MagicMock(),
    )

    # User chooses to combine commits
    mock_console.confirm_action.side_effect = [
        True,
        False,
        True,
    ]  # Continue, Don't create individual, Create combined
    mock_console.confirm_batch_continue.return_value = True

    # Run with combine_commits=True to force combined commit
    commit_loom.run(combine_commits=True)

    # Verify only one combined commit was created
    commit_loom.git.create_commit.assert_called_once()
    assert (
        commit_loom.git.create_commit.call_args[0][0]
        == "📦 chore: combine multiple changes"
    )


def test_cli_arguments():
    """Test CLI argument parsing."""
    parser = create_parser()

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
def test_main_keyboard_interrupt(mock_commit_loom, mock_console):
    """Test handling of KeyboardInterrupt in main."""
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
