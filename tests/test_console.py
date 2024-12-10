"""Tests for console module."""

from unittest.mock import MagicMock, patch

from rich.prompt import Confirm

from commitloom.cli import console
from commitloom.core.analyzer import Warning as AnalyzerWarning
from commitloom.core.analyzer import WarningLevel
from commitloom.core.git import GitFile
from commitloom.services.ai_service import TokenUsage


def test_print_changed_files():
    """Test printing changed files."""
    files = [GitFile(path="test.py", status="M")]
    console.print_changed_files(files)


def test_print_warnings():
    """Test printing warnings."""
    warnings = [
        AnalyzerWarning(level=WarningLevel.HIGH, message="Warning 1"),
        AnalyzerWarning(level=WarningLevel.MEDIUM, message="Warning 2"),
    ]
    console.print_warnings(warnings)


def test_print_warnings_no_warnings():
    """Test printing warnings when there are none."""
    console.print_warnings([])


def test_print_token_usage():
    """Test printing token usage."""
    usage = TokenUsage(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        input_cost=0.01,
        output_cost=0.02,
        total_cost=0.03,
    )
    console.print_token_usage(usage)


def test_print_token_usage_no_usage():
    """Test printing token usage when there is none."""
    usage = TokenUsage(
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        input_cost=0.0,
        output_cost=0.0,
        total_cost=0.0,
    )
    console.print_token_usage(usage)


def test_print_commit_message():
    """Test printing commit message."""
    console.print_commit_message("Test commit message")


def test_print_batch_info():
    """Test printing batch info."""
    files = ["file1.py", "file2.py"]
    console.print_batch_info(1, files)


def test_print_batch_info_empty():
    """Test printing batch info with empty batch."""
    console.print_batch_info(1, [])


def test_print_batch_info_with_files():
    """Test printing batch info with files."""
    files = [GitFile(path="test.py", status="M")]
    console.print_batch_info(1, [f.path for f in files])


def test_confirm_action():
    """Test action confirmation."""
    with patch.object(Confirm, "ask", return_value=True):
        console.set_auto_confirm(False)  # Ensure auto_confirm is off
        result = console.confirm_action("Test action?")
        assert result is True


def test_confirm_action_auto():
    """Test confirm action with auto-confirm enabled."""
    console.set_auto_confirm(True)
    result = console.confirm_action("Test?")
    assert result is True
    console.set_auto_confirm(False)  # Reset auto_confirm


def test_confirm_action_invalid_input():
    """Test confirm action with invalid input."""
    with patch.object(Confirm, "ask", side_effect=Exception("Invalid input")):
        console.set_auto_confirm(False)  # Ensure auto_confirm is off
        result = console.confirm_action("Test?")
        assert result is False


def test_print_success():
    """Test printing success message."""
    console.print_success("Success message")


def test_print_error():
    """Test printing error message."""
    console.print_error("Error message")


def test_print_info():
    """Test printing info message."""
    console.print_info("Info message")


def test_print_warning():
    """Test printing warning message."""
    console.print_warning("Warning message")


def test_print_changed_files_with_status():
    """Test printing changed files with different statuses."""
    files = [
        GitFile(path="added.py", status="A"),
        GitFile(path="modified.py", status="M"),
        GitFile(path="deleted.py", status="D"),
        GitFile(path="renamed.py", status="R", old_path="old.py"),
    ]
    console.print_changed_files(files)


def test_print_changed_files_with_binary():
    """Test printing changed files including binary files."""
    files = [
        GitFile(path="text.py", status="M"),
        GitFile(path="image.png", status="M", size=1024, hash="abc123"),
    ]
    console.print_changed_files(files)


def test_print_error_with_exception():
    """Test printing error with exception details."""
    try:
        raise ValueError("Test error")
    except Exception as e:
        console.print_error(str(e))


def test_print_warning_with_details():
    """Test printing warning with additional details."""
    console.print_warning("Warning message with details: test details")


def test_print_info_with_details():
    """Test printing info with additional details."""
    console.print_info("Info message with details: test details")


def test_print_success_with_details():
    """Test printing success with additional details."""
    console.print_success("Success message with details: test details")


def test_confirm_batch_continue_auto():
    """Test batch continuation with auto-confirm."""
    console.set_auto_confirm(True)
    result = console.confirm_batch_continue()
    assert result is True
    console.set_auto_confirm(False)  # Reset auto_confirm


def test_confirm_batch_continue():
    """Test batch continuation prompt."""
    with patch.object(Confirm, "ask", return_value=True):
        console.set_auto_confirm(False)  # Ensure auto_confirm is off
        result = console.confirm_batch_continue()
        assert result is True


def test_select_commit_strategy_auto():
    """Test commit strategy selection with auto-confirm."""
    console.set_auto_confirm(True)
    result = console.select_commit_strategy()
    assert result == "individual"
    console.set_auto_confirm(False)  # Reset auto_confirm


def test_select_commit_strategy():
    """Test commit strategy selection prompt."""
    with patch.object(Confirm, "ask", return_value=True):
        console.set_auto_confirm(False)  # Ensure auto_confirm is off
        result = console.select_commit_strategy()
        assert result == "individual"
