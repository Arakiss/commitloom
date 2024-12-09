"""Tests for CLI main module."""

import pytest
from click.testing import CliRunner

from commitloom.__main__ import main


@pytest.fixture
def runner():
    """Fixture for CLI runner."""
    return CliRunner()


class TestCliBasic:
    """Test basic CLI functionality."""

    def test_help_text(self, runner):
        """Test help text is displayed."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_basic_run(self, runner, mock_loom, mocker):
        """Test basic run without arguments."""
        # Mock the CommitLoom class
        mock_commit_loom = mocker.patch("commitloom.__main__.CommitLoom")
        mock_commit_loom.return_value = mock_loom

        result = runner.invoke(main)
        assert result.exit_code == 0
        mock_loom.run.assert_called_once_with(auto_commit=False, combine_commits=False, debug=False)

    def test_all_flags(self, runner, mock_loom, mocker):
        """Test run with all flags enabled."""
        # Mock the CommitLoom class
        mock_commit_loom = mocker.patch("commitloom.__main__.CommitLoom")
        mock_commit_loom.return_value = mock_loom

        result = runner.invoke(main, ["-y", "-c", "-d"])
        assert result.exit_code == 0
        mock_loom.run.assert_called_once_with(auto_commit=True, combine_commits=True, debug=True)


class TestCliErrors:
    """Test CLI error handling."""

    def test_keyboard_interrupt(self, runner, mock_loom, mocker):
        """Test handling of keyboard interrupt."""
        # Mock the CommitLoom class
        mock_commit_loom = mocker.patch("commitloom.__main__.CommitLoom")
        mock_commit_loom.return_value = mock_loom
        mock_loom.run.side_effect = KeyboardInterrupt()

        result = runner.invoke(main)
        assert result.exit_code == 1
        assert "Operation cancelled by user" in result.output

    def test_general_error(self, runner, mock_loom, mocker):
        """Test handling of general errors."""
        # Mock the CommitLoom class
        mock_commit_loom = mocker.patch("commitloom.__main__.CommitLoom")
        mock_commit_loom.return_value = mock_loom
        mock_loom.run.side_effect = Exception("Test error")

        result = runner.invoke(main)
        assert result.exit_code == 1
        assert "Test error" in result.output
