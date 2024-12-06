"""Tests for console output module."""

import pytest
from unittest.mock import patch, MagicMock
from rich.console import Console
from rich.panel import Panel

from commitloom.cli import console
from commitloom.core.git import GitFile
from commitloom.core.analyzer import CommitAnalysis, Warning, WarningLevel
from commitloom.services.ai_service import TokenUsage


@pytest.fixture
def mock_console():
    """Fixture for mocked Console instance."""
    with patch("commitloom.cli.console.console", new=MagicMock(spec=Console)) as mock:
        yield mock


def test_print_changed_files(mock_console):
    """Test printing changed files."""
    files = [
        GitFile(path="file1.py"),
        GitFile(path="file2.py"),
    ]

    console.print_changed_files(files)

    assert mock_console.print.call_count == 3  # Header + 2 files
    mock_console.print.assert_any_call(
        "\n[bold blue]📜 Changes detected in the following files:[/bold blue]"
    )
    mock_console.print.assert_any_call("  - [cyan]file1.py[/cyan]")
    mock_console.print.assert_any_call("  - [cyan]file2.py[/cyan]")


def test_print_warnings(mock_console):
    """Test printing analysis warnings."""
    warnings = [
        Warning(level=WarningLevel.HIGH, message="Critical warning"),
        Warning(level=WarningLevel.MEDIUM, message="Medium warning"),
    ]
    analysis = CommitAnalysis(
        estimated_tokens=1000,
        estimated_cost=0.05,
        num_files=2,
        warnings=warnings,
        is_complex=True,
    )

    console.print_warnings(analysis)

    mock_console.print.assert_any_call(
        "\n[bold yellow]⚠️ Commit Size Warnings:[/bold yellow]"
    )
    mock_console.print.assert_any_call("🔴 Critical warning")
    mock_console.print.assert_any_call("🟡 Medium warning")
    mock_console.print.assert_any_call("\n[cyan]📊 Commit Statistics:[/cyan]")
    mock_console.print.assert_any_call("  • Estimated tokens: 1,000")
    mock_console.print.assert_any_call("  • Estimated cost: €0.0500")
    mock_console.print.assert_any_call("  • Files changed: 2")


def test_print_warnings_no_warnings(mock_console):
    """Test printing analysis with no warnings."""
    analysis = CommitAnalysis(
        estimated_tokens=100,
        estimated_cost=0.01,
        num_files=1,
        warnings=[],
        is_complex=False,
    )

    console.print_warnings(analysis)

    # Should not print anything when there are no warnings
    mock_console.print.assert_not_called()


def test_print_token_usage(mock_console):
    """Test printing token usage summary."""
    usage = TokenUsage(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        input_cost=0.01,
        output_cost=0.02,
        total_cost=0.03,
    )

    console.print_token_usage(usage)

    # Should print token usage summary with all details
    mock_console.print.assert_called_once()
    call_args = mock_console.print.call_args[0][0]
    assert "Token Usage Summary" in call_args
    assert "Prompt Tokens: 100" in call_args
    assert "Completion Tokens: 50" in call_args
    assert "Total Tokens: 150" in call_args
    assert "Cost Breakdown" in call_args
    assert "Input Cost: €0.01000000" in call_args
    assert "Output Cost: €0.02000000" in call_args
    assert "Total Cost: €0.03000000" in call_args


def test_print_commit_message(mock_console):
    """Test printing formatted commit message."""
    message = "Test commit message"

    console.print_commit_message(message)

    mock_console.print.assert_called_once()
    args, kwargs = mock_console.print.call_args
    assert isinstance(args[0], Panel)
    assert args[0].renderable.plain == message


def test_print_batch_info(mock_console):
    """Test printing batch information."""
    files = ["file1.py", "file2.py"]

    console.print_batch_info(1, files)

    assert mock_console.print.call_count == 3  # Header + 2 files
    mock_console.print.assert_any_call("\n[bold blue]📑 Batch 1 Summary:[/bold blue]")
    mock_console.print.assert_any_call("  - [cyan]file1.py[/cyan]")
    mock_console.print.assert_any_call("  - [cyan]file2.py[/cyan]")


@patch("commitloom.cli.console.Confirm.ask")
def test_confirm_action(mock_ask, mock_console):
    """Test action confirmation."""
    mock_ask.return_value = True

    result = console.confirm_action("Proceed?")

    assert result is True
    mock_ask.assert_called_once_with("\nProceed?")


def test_print_success(mock_console):
    """Test printing success message."""
    console.print_success("Operation completed")

    mock_console.print.assert_called_once_with(
        "\n[bold green]✅ Operation completed[/bold green]"
    )


def test_print_error(mock_console):
    """Test printing error message."""
    console.print_error("Operation failed")

    mock_console.print.assert_called_once_with(
        "\n[bold red]❌ Operation failed[/bold red]"
    )


def test_print_info(mock_console):
    """Test printing info message."""
    console.print_info("Important information")

    mock_console.print.assert_called_once_with(
        "\n[bold blue]ℹ️ Important information[/bold blue]"
    )


def test_print_warning(mock_console):
    """Test printing warning message."""
    console.print_warning("Warning message")

    mock_console.print.assert_called_once_with(
        "\n[bold yellow]⚠️ Warning message[/bold yellow]"
    )
