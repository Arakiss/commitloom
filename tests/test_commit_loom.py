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
    with (
        patch("commitloom.cli.cli_handler.GitOperations", autospec=True) as mock_git,
        patch("commitloom.cli.cli_handler.CommitAnalyzer", autospec=True) as mock_analyzer,
        patch("commitloom.cli.cli_handler.AIService", autospec=True) as mock_ai,
        patch("commitloom.cli.cli_handler.load_dotenv"),
    ):
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


@pytest.fixture
def loom(mock_deps):
    """Fixture for CommitLoom instance."""
    instance = CommitLoom(test_mode=True)
    instance.git = mock_deps["git"]
    instance.analyzer = mock_deps["analyzer"]
    instance.ai_service = mock_deps["ai"]
    return instance


class TestBasicOperations:
    """Test basic CommitLoom operations."""

    def test_no_changes(self, loom):
        """Test behavior when there are no changes."""
        loom.git.get_staged_files.return_value = []

        with patch("commitloom.cli.cli_handler.console") as mock_console:
            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 0
            mock_console.print_warning.assert_called_once_with("No files staged for commit.")

    def test_simple_commit(self, loom, mock_token_usage):
        """Test a simple commit operation."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [GitFile(path="test.py", status="M")]
            loom.git.get_staged_files.return_value = files
            loom.git.get_diff.return_value = "test diff"

            # Setup AI service mock
            loom.ai_service.generate_commit_message.return_value = (
                CommitSuggestion(
                    title="test commit",
                    body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
                    summary="test summary",
                ),
                mock_token_usage,
            )

            # Setup successful commit
            loom.git.create_commit.return_value = True

            loom.run()

            loom.git.create_commit.assert_called_once()
            mock_console.print_success.assert_called_once_with("Changes committed successfully!")


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_git_error(self, loom):
        """Test handling of git errors."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            loom.git.get_staged_files.side_effect = GitError("Git error")

            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 1
            mock_console.print_error.assert_called_with("Git error: Git error")

    def test_commit_error(self, loom, mock_token_usage):
        """Test handling of commit creation errors."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [GitFile(path="test.py", status="M")]
            loom.git.get_staged_files.return_value = files
            loom.git.get_diff.return_value = "test diff"

            # Setup AI service mock
            loom.ai_service.generate_commit_message.return_value = (
                CommitSuggestion(
                    title="test commit",
                    body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
                    summary="test summary",
                ),
                mock_token_usage,
            )

            # Setup git error
            loom.git.create_commit.side_effect = GitError("Failed to create commit")

            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 1
            mock_console.print_error.assert_called_with("Git error: Failed to create commit")
            loom.git.reset_staged_changes.assert_called_once()

    def test_api_error(self, loom):
        """Test handling of API errors."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [GitFile(path="test.py", status="M")]
            loom.git.get_staged_files.return_value = files
            loom.git.get_diff.return_value = "test diff"

            # Setup API error
            loom.ai_service.generate_commit_message.side_effect = Exception("API error")

            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 1
            mock_console.print_error.assert_called_with("API error: API error")
            loom.git.reset_staged_changes.assert_called_once()

    def test_user_abort(self, loom, mock_token_usage):
        """Test user aborting the commit."""
        with patch("commitloom.cli.cli_handler.console") as mock_console:
            mock_console.confirm_action.return_value = False

            # Setup test data
            files = [GitFile(path="test.py", status="M")]
            loom.git.get_staged_files.return_value = files
            loom.git.get_diff.return_value = "test diff"

            # Setup AI service mock
            loom.ai_service.generate_commit_message.return_value = (
                CommitSuggestion(
                    title="test commit",
                    body={"Changes": {"emoji": "✨", "changes": ["test change"]}},
                    summary="test summary",
                ),
                mock_token_usage,
            )

            with pytest.raises(SystemExit) as exc_info:
                loom.run()

            assert exc_info.value.code == 0
            mock_console.print_warning.assert_called_with("Commit cancelled by user.")
            loom.git.reset_staged_changes.assert_called_once()
