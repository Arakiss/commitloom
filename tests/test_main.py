"""Tests for CLI main module."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from commitloom.__main__ import main


@pytest.fixture
def runner():
    """Fixture for CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_loom():
    """Fixture for mocked CommitLoom."""
    mock = MagicMock()
    mock.run = MagicMock()
    return mock


class TestCliBasic:
    """Test basic CLI functionality."""

    def test_help_text(self, runner):
        """Test help text is displayed."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_basic_run(self, runner, mock_loom):
        """Test basic run without arguments."""
        with patch("commitloom.__main__.CommitLoom") as mock_commit_loom:
            mock_commit_loom.return_value = mock_loom
            result = runner.invoke(main)

            assert result.exit_code == 0
            mock_commit_loom.assert_called_once_with(test_mode=True)
            mock_loom.run.assert_called_once_with(
                auto_commit=False, combine_commits=False, debug=False
            )

    def test_all_flags(self, runner, mock_loom):
        """Test run with all flags enabled."""
        with patch("commitloom.__main__.CommitLoom") as mock_commit_loom:
            mock_commit_loom.return_value = mock_loom
            result = runner.invoke(main, ["-y", "-c", "-d"])

            assert result.exit_code == 0
            mock_commit_loom.assert_called_once_with(test_mode=True)
            mock_loom.run.assert_called_once_with(
                auto_commit=True, combine_commits=True, debug=True
            )


class TestCliErrors:
    """Test CLI error handling."""

    def test_keyboard_interrupt(self, runner, mock_loom):
        """Test handling of keyboard interrupt."""
        with patch("commitloom.__main__.CommitLoom") as mock_commit_loom:
            mock_commit_loom.return_value = mock_loom
            mock_loom.run.side_effect = KeyboardInterrupt()

            result = runner.invoke(main)

            assert result.exit_code == 1
            mock_commit_loom.assert_called_once_with(test_mode=True)
            assert "Operation cancelled by user" in result.output

    def test_general_error(self, runner, mock_loom):
        """Test handling of general errors."""
        with patch("commitloom.__main__.CommitLoom") as mock_commit_loom:
            mock_commit_loom.return_value = mock_loom
            mock_loom.run.side_effect = Exception("Test error")

            result = runner.invoke(main)

            assert result.exit_code == 1
            mock_commit_loom.assert_called_once_with(test_mode=True)
            assert "Test error" in result.output
