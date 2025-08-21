"""Tests for batch processing module."""

from unittest.mock import MagicMock, patch

import pytest

from commitloom.core.batch import BatchConfig, BatchProcessor
from commitloom.services.ai_service import TokenUsage


@pytest.fixture
def batch_config():
    """Fixture for batch configuration."""
    return BatchConfig(batch_size=5)


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
        patch("commitloom.core.batch.GitOperations", autospec=True) as mock_git,
        patch("commitloom.cli.cli_handler.CommitAnalyzer", autospec=True) as mock_analyzer,
    ):
        mock_git_instance = mock_git.return_value
        mock_git_instance.stage_files = MagicMock()
        mock_git_instance.reset_staged_changes = MagicMock()
        mock_git_instance.get_diff = MagicMock(return_value="test diff")

        mock_analyzer_instance = mock_analyzer.return_value
        mock_analyzer_instance.estimate_tokens_and_cost = MagicMock(return_value=(100, 0.01))

        return {
            "git": mock_git_instance,
            "analyzer": mock_analyzer_instance,
        }


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_single_batch(self, mock_deps, mock_git_file, batch_config, mock_token_usage):
        """Test processing a single batch of files."""
        with patch("commitloom.core.batch.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [mock_git_file(f"file{i}.py") for i in range(2)]

            # Process batch
            processor = BatchProcessor(batch_config)
            processor.git = mock_deps["git"]  # Use mocked git operations
            processor.process_files(files)

            # Verify files were staged
            mock_deps["git"].stage_files.assert_called_once()

    def test_multiple_batches(self, mock_deps, mock_git_file, batch_config, mock_token_usage):
        """Test processing multiple batches of files."""
        with patch("commitloom.core.batch.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [mock_git_file(f"file{i}.py") for i in range(10)]

            # Process batches
            processor = BatchProcessor(batch_config)
            processor.git = mock_deps["git"]  # Use mocked git operations
            processor.process_files(files)

            # Verify files were staged in batches
            assert mock_deps["git"].stage_files.call_count == 2


class TestBatchEdgeCases:
    """Test edge cases in batch processing."""

    def test_empty_batch(self, mock_deps, batch_config):
        """Test handling of empty batch."""
        processor = BatchProcessor(batch_config)
        processor.git = mock_deps["git"]  # Use mocked git operations
        processor.process_files([])

        # Verify no operations were performed
        mock_deps["git"].stage_files.assert_not_called()

    def test_user_cancellation(self, mock_deps, mock_git_file, batch_config):
        """Test handling of user cancellation."""
        with patch("commitloom.core.batch.console") as mock_console:
            mock_console.confirm_action.return_value = False

            # Setup test data
            files = [mock_git_file("test.py")]

            # Process batch
            processor = BatchProcessor(batch_config)
            processor.git = mock_deps["git"]  # Use mocked git operations
            processor.process_files(files)

            # Verify no files were staged
            mock_deps["git"].stage_files.assert_not_called()

    def test_git_error_handling(self, mock_deps, mock_git_file, batch_config):
        """Test handling of git errors."""
        with patch("commitloom.core.batch.console") as mock_console:
            mock_console.confirm_action.return_value = True

            # Setup test data
            files = [mock_git_file("test.py")]
            mock_deps["git"].stage_files.side_effect = Exception("Git error")

            processor = BatchProcessor(batch_config)
            processor.git = mock_deps["git"]  # Use mocked git operations
            with pytest.raises(Exception) as exc_info:
                processor.process_files(files)

            assert "Git error" in str(exc_info.value)
