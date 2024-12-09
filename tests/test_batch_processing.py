"""Tests for batch processing module."""

import pytest

from commitloom.core.batch import BatchConfig, BatchProcessor


@pytest.fixture
def batch_config():
    """Fixture for batch configuration."""
    return BatchConfig(batch_size=5)


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_single_batch(self, mock_deps, mocker, mock_git_file, batch_config):
        """Test processing a single batch of files."""
        mock_console = mocker.patch("commitloom.cli.cli_handler.console")
        mock_console.confirm_action.return_value = True

        # Setup test data
        files = [mock_git_file(f"file{i}.py") for i in range(2)]
        mock_deps["git"].get_diff.return_value = "test diff"
        mock_deps["analyzer"].estimate_tokens_and_cost.return_value = (100, 0.01)

        # Process batch
        processor = BatchProcessor(batch_config)
        processor.git = mock_deps["git"]  # Use mocked git operations
        processor.process_files(files)

        # Verify files were staged
        mock_deps["git"].stage_files.assert_called_once()

    def test_multiple_batches(self, mock_deps, mocker, mock_git_file, batch_config):
        """Test processing multiple batches of files."""
        mock_console = mocker.patch("commitloom.cli.cli_handler.console")
        mock_console.confirm_action.return_value = True

        # Setup test data
        files = [mock_git_file(f"file{i}.py") for i in range(10)]
        mock_deps["git"].get_diff.return_value = "test diff"
        mock_deps["analyzer"].estimate_tokens_and_cost.return_value = (1000, 0.01)

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

    def test_user_cancellation(self, mock_deps, mocker, mock_git_file, batch_config):
        """Test handling of user cancellation."""
        mock_console = mocker.patch("commitloom.cli.cli_handler.console")
        mock_console.confirm_action.return_value = False

        files = [mock_git_file("test.py")]
        processor = BatchProcessor(batch_config)
        processor.git = mock_deps["git"]  # Use mocked git operations
        processor.process_files(files)

        # Verify no files were staged
        mock_deps["git"].stage_files.assert_not_called()

    def test_git_error_handling(self, mock_deps, mock_git_file, batch_config):
        """Test handling of git errors."""
        files = [mock_git_file("test.py")]
        mock_deps["git"].stage_files.side_effect = Exception("Git error")

        processor = BatchProcessor(batch_config)
        processor.git = mock_deps["git"]  # Use mocked git operations
        with pytest.raises(Exception) as exc_info:
            processor.process_files(files)

        assert "Git error" in str(exc_info.value)
