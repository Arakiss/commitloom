"""Tests for CommitLoom functionality."""

from unittest.mock import MagicMock, patch

import pytest

from commitloom.cli.cli_handler import CommitLoom
from commitloom.core.analyzer import CommitAnalysis
from commitloom.core.git import GitError, GitFile
from commitloom.services.ai_service import CommitSuggestion, TokenUsage


@pytest.fixture
def mock_token_usage():
    """Mock token usage."""
    return TokenUsage(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        input_cost=0.01,
        output_cost=0.02,
        total_cost=0.03,
    )


@pytest.fixture
def mock_deps():
    """Fixture for mocked dependencies."""
    with patch("commitloom.cli.cli_handler.GitOperations", autospec=True) as mock_git, patch(
        "commitloom.cli.cli_handler.CommitAnalyzer", autospec=True
    ) as mock_analyzer, patch(
        "commitloom.cli.cli_handler.AIService", autospec=True
    ) as mock_ai, patch("commitloom.cli.cli_handler.load_dotenv"):
        mock_git_instance = mock_git.return_value
        mock_git_instance.stage_files = MagicMock()
        mock_git_instance.reset_staged_changes = MagicMock()

        mock_analyzer_instance = mock_analyzer.return_value
        mock_analyzer_instance.analyze_diff_complexity = MagicMock(
            return_value=CommitAnalysis(
                estimated_tokens=100,
                estimated_cost=0.01,
                num_files=1,
                warnings=[],
                is_complex=False,
            )
        )

        mock_ai_instance = mock_ai.return_value
        mock_ai_instance.generate_commit_message = MagicMock()

        return {
            "git": mock_git_instance,
            "analyzer": mock_analyzer_instance,
            "ai": mock_ai_instance,
        }


class TestBasicOperations:
    """Test basic CommitLoom operations."""

    def test_no_changes(self, mock_deps):
        """Test behavior when there are no changes."""
        mock_deps["git"].get_staged_files.return_value = []

        with patch("commitloom.cli.cli_handler.console") as mock_console:
            loom = CommitLoom(test_mode=True)
            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 0
            mock_console.print_warning.assert_called_once_with("No files staged for commit.")

    def test_simple_commit(self, mock_deps, mock_token_usage):
        """Test a simple commit operation."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [GitFile(path="test.py", status="M")]
            mock_deps["git"].get_staged_files.return_value = files
            mock_deps["git"].get_diff.return_value = "test diff"

            # Setup AI service mock
            mock_deps["ai"].generate_commit_message.return_value = (
                CommitSuggestion(
                    title="test commit",
                    body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
                    summary="test summary",
                ),
                mock_token_usage,
            )

            # Setup successful commit
            mock_deps["git"].create_commit.return_value = True

            loom = CommitLoom(test_mode=True)
            loom.run()

            mock_deps["git"].create_commit.assert_called_once()
            mock_console.print_success.assert_called_once_with("Changes committed successfully!")


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_git_error(self, mock_deps):
        """Test handling of git errors."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_deps["git"].get_staged_files.side_effect = GitError("Git error")

            loom = CommitLoom(test_mode=True)
            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 1
            mock_console.print_error.assert_called_with("Git error: Git error")

    def test_commit_error(self, mock_deps, mock_token_usage):
        """Test handling of commit creation errors."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [GitFile(path="test.py", status="M")]
            mock_deps["git"].get_staged_files.return_value = files
            mock_deps["git"].get_diff.return_value = "test diff"

            # Setup AI service mock
            mock_deps["ai"].generate_commit_message.return_value = (
                CommitSuggestion(
                    title="test commit",
                    body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
                    summary="test summary",
                ),
                mock_token_usage,
            )

            # Setup git error
            mock_deps["git"].create_commit.side_effect = GitError("Failed to create commit")

            loom = CommitLoom(test_mode=True)
            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 1
            mock_console.print_error.assert_called_with("Git error: Failed to create commit")
            mock_deps["git"].reset_staged_changes.assert_called_once()

    def test_api_error(self, mock_deps):
        """Test handling of API errors."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [GitFile(path="test.py", status="M")]
            mock_deps["git"].get_staged_files.return_value = files
            mock_deps["git"].get_diff.return_value = "test diff"

            # Setup API error
            mock_deps["ai"].generate_commit_message.side_effect = Exception("API error")

            loom = CommitLoom(test_mode=True)
            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 1
            mock_console.print_error.assert_called_with("API error: API error")
            mock_deps["git"].reset_staged_changes.assert_called_once()

    def test_user_abort(self, mock_deps, mock_token_usage):
        """Test user aborting the commit."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_console.confirm_action.return_value = False

            # Setup test data
            files = [GitFile(path="test.py", status="M")]
            mock_deps["git"].get_staged_files.return_value = files
            mock_deps["git"].get_diff.return_value = "test diff"

            # Setup AI service mock
            mock_deps["ai"].generate_commit_message.return_value = (
                CommitSuggestion(
                    title="test commit",
                    body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
                    summary="test summary",
                ),
                mock_token_usage,
            )

            loom = CommitLoom(test_mode=True)
            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 0
            mock_console.print_warning.assert_called_with("Commit cancelled by user.")
            mock_deps["git"].reset_staged_changes.assert_called_once()
