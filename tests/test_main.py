"""Tests for CLI functionality."""

import pytest
from click.testing import CliRunner

from commitloom.__main__ import main
from commitloom.cli.cli_handler import CommitLoom


@pytest.fixture
def runner():
    """Fixture for CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_loom(mocker):
    """Fixture for mocked CommitLoom instance."""
    mock = mocker.patch("commitloom.cli.cli_handler.CommitLoom", autospec=True)
    return mock.return_value


class TestCliBasic:
    """Basic CLI functionality tests."""

    def test_help_text(self, runner):
        """Test help command shows correct output."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Create structured git commits" in result.output

    def test_basic_run(self, runner, mock_loom):
        """Test basic run without arguments."""
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        mock_loom.run.assert_called_once_with(
            auto_commit=False, combine_commits=False, debug=False
        )

    def test_all_flags(self, runner, mock_loom):
        """Test run with all flags enabled."""
        result = runner.invoke(main, ["-y", "-c", "-d"])
        assert result.exit_code == 0
        mock_loom.run.assert_called_once_with(
            auto_commit=True, combine_commits=True, debug=True
        )


class TestCliErrors:
    """Error handling tests."""

    def test_keyboard_interrupt(self, runner, mock_loom, capsys):
        """Test handling of keyboard interrupt."""
        mock_loom.run.side_effect = KeyboardInterrupt()
        result = runner.invoke(main)
        assert result.exit_code == 1
        captured = capsys.readouterr()
        assert "Operation cancelled" in captured.err

    def test_general_error(self, runner, mock_loom, capsys):
        """Test handling of general errors."""
        mock_loom.run.side_effect = Exception("Test error")
        result = runner.invoke(main)
        assert result.exit_code == 1
        captured = capsys.readouterr()
        assert "Test error" in captured.err
