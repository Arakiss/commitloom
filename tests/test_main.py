"""Tests for main CLI module."""

import pytest
from unittest.mock import patch, MagicMock, call

from commitloom.cli.main import CommitLoom
from commitloom.core.git import GitFile, GitError
from commitloom.services.ai_service import CommitSuggestion
from commitloom.core.analyzer import CommitAnalysis, Warning, WarningLevel


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


def test_process_files_in_batches_single_batch(commit_loom):
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

    result = commit_loom.process_files_in_batches(files)

    assert len(result) == 1
    assert len(result[0]["files"]) == 2
    assert isinstance(result[0]["commit_data"], CommitSuggestion)
    assert isinstance(result[0]["usage"], MagicMock)


def test_process_files_in_batches_multiple_batches(commit_loom):
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

    result = commit_loom.process_files_in_batches(files, batch_size=5)

    assert len(result) == 2  # Should be split into 2 batches of 5 files each
    assert len(result[0]["files"]) == 5
    assert len(result[1]["files"]) == 5


def test_combine_commit_suggestions(commit_loom):
    """Test combining multiple commit suggestions into one."""
    suggestions = [
        {
            "commit_data": CommitSuggestion(
                title="feat: first change",
                body={"Features": {"emoji": "✨", "changes": ["Change 1"]}},
                summary="First summary",
            )
        },
        {
            "commit_data": CommitSuggestion(
                title="fix: second change",
                body={"Fixes": {"emoji": "🐛", "changes": ["Fix 1"]}},
                summary="Second summary",
            )
        },
    ]

    result = commit_loom.combine_commit_suggestions(suggestions)

    assert isinstance(result, CommitSuggestion)
    assert result.title == "📦 chore: combine multiple changes"
    assert "Features" in result.body
    assert "Fixes" in result.body
    assert result.body["Features"]["changes"] == ["Change 1"]
    assert result.body["Fixes"]["changes"] == ["Fix 1"]
    assert "First summary Second summary" in result.summary


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

    mock_console.print_info.assert_called_with(
        "Process cancelled. Please review your changes."
    )


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
