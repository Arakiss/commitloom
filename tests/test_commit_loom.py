"""Tests for CommitLoom functionality."""

from unittest.mock import MagicMock

import pytest

from commitloom.cli.cli_handler import CommitLoom
from commitloom.core.analyzer import CommitAnalysis
from commitloom.core.git import GitError, GitFile
from commitloom.services.ai_service import CommitSuggestion


@pytest.fixture
def mock_deps(mocker):
    """Fixture for mocked dependencies."""
    mock_git = mocker.patch("commitloom.cli.cli_handler.GitOperations", autospec=True)
    mock_analyzer = mocker.patch("commitloom.cli.cli_handler.CommitAnalyzer", autospec=True)
    mock_ai = mocker.patch("commitloom.cli.cli_handler.AIService", autospec=True)
    mocker.patch("commitloom.cli.cli_handler.load_dotenv")

    return {
        "git": mock_git.return_value,
        "analyzer": mock_analyzer.return_value,
        "ai": mock_ai.return_value,
    }


class TestBasicOperations:
    """Test basic CommitLoom operations."""

    def test_no_changes(self, mock_deps, mocker):
        """Test behavior when there are no changes."""
        mock_deps["git"].get_staged_files.return_value = []
        mock_console = mocker.patch("commitloom.cli.cli_handler.console")

        loom = CommitLoom()
        loom.run()

        mock_console.print_warning.assert_called_once_with("No files staged for commit.")

    def test_simple_commit(self, mock_deps, mocker):
        """Test a simple commit operation."""
        mock_console = mocker.patch("commitloom.cli.cli_handler.console")
        mock_console.confirm_action.return_value = True

        # Setup test data
        files = [GitFile(path="test.py", status="M")]
        mock_deps["git"].get_staged_files.return_value = files
        mock_deps["git"].get_diff.return_value = "test diff"
        mock_deps["analyzer"].analyze_diff_complexity.return_value = CommitAnalysis(
            estimated_tokens=100,
            estimated_cost=0.01,
            num_files=1,
            warnings=[],
            is_complex=False,
        )

        # Setup AI service mock
        mock_deps["ai"].generate_commit_message.return_value = (
            CommitSuggestion(
                title="test commit",
                body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
                summary="test summary",
            ),
            MagicMock(),
        )

        loom = CommitLoom()
        loom.run()

        mock_deps["git"].create_commit.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_git_error(self, mock_deps, mocker):
        """Test handling of git errors."""
        mock_console = mocker.patch("commitloom.cli.cli_handler.console")
        mock_deps["git"].get_staged_files.side_effect = GitError("Git error")

        loom = CommitLoom()
        loom.run()

        mock_console.print_error.assert_called_with("An unexpected error occurred: Git error")

    def test_commit_error(self, mock_deps, mocker):
        """Test handling of commit creation errors."""
        mock_console = mocker.patch("commitloom.cli.cli_handler.console")
        mock_console.confirm_action.return_value = True

        # Setup test data
        files = [GitFile(path="test.py", status="M")]
        mock_deps["git"].get_staged_files.return_value = files
        mock_deps["git"].get_diff.return_value = "test diff"
        mock_deps["analyzer"].analyze_diff_complexity.return_value = CommitAnalysis(
            estimated_tokens=100,
            estimated_cost=0.01,
            num_files=1,
            warnings=[],
            is_complex=False,
        )

        # Setup AI service mock
        mock_deps["ai"].generate_commit_message.return_value = (
            CommitSuggestion(
                title="test commit",
                body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
                summary="test summary",
            ),
            MagicMock(),
        )

        # Setup git error
        mock_deps["git"].create_commit.side_effect = GitError("Failed to create commit")

        loom = CommitLoom()
        loom.run()

        mock_console.print_error.assert_called()
