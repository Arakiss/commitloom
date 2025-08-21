"""Tests for CLI handler module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from commitloom.cli.cli_handler import CommitLoom
from commitloom.core.analyzer import CommitAnalysis
from commitloom.core.git import GitError, GitFile
from commitloom.services.ai_service import TokenUsage


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
def mock_ai_service():
    """Mock AIService."""
    with patch("commitloom.cli.cli_handler.AIService") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def cli(mock_ai_service, mock_token_usage):
    """Fixture for CommitLoom instance."""
    instance = CommitLoom(test_mode=True)
    # Mock git operations
    instance.git.stage_files = MagicMock()  # type: ignore
    instance.git.reset_staged_changes = MagicMock()  # type: ignore
    instance.git.get_diff = MagicMock(return_value="test diff")  # type: ignore
    instance.ai_service.generate_commit_message = MagicMock(  # type: ignore
        return_value=(
            MagicMock(title="test", body={}, format_body=lambda: "test"),
            mock_token_usage,
        )
    )
    return instance


def test_handle_commit_no_changes(cli):
    """Test handling commit with no changes."""
    cli.git.get_staged_files = MagicMock(return_value=[])

    with pytest.raises(SystemExit) as exc:
        cli.run()

    assert exc.value.code == 0


def test_handle_commit_git_error(cli):
    """Test handling git error."""
    cli.git.get_staged_files = MagicMock(side_effect=GitError("Git error"))

    with pytest.raises(SystemExit) as exc:
        cli.run()

    assert exc.value.code == 1


def test_handle_commit_success(cli):
    """Test successful commit."""
    mock_file = GitFile("test.py", "A", old_path=None, size=100, hash="abc123")
    cli.git.get_staged_files = MagicMock(return_value=[mock_file])
    cli.git.create_commit = MagicMock(return_value=True)

    cli.run(auto_commit=True)

    cli.git.create_commit.assert_called_once()


def test_handle_commit_complex_changes(cli):
    """Test handling complex changes."""
    mock_files = [GitFile(f"test{i}.py", "A", old_path=None, size=100, hash="abc123") for i in range(4)]
    cli.git.get_staged_files = MagicMock(return_value=mock_files)
    cli.git.create_commit = MagicMock(return_value=True)

    cli.run(auto_commit=True)

    assert cli.git.create_commit.call_count > 0


def test_handle_commit_user_abort(cli):
    """Test user aborting commit."""
    mock_file = GitFile("test.py", "A", old_path=None, size=100, hash="abc123")
    cli.git.get_staged_files = MagicMock(return_value=[mock_file])
    with patch("commitloom.cli.cli_handler.console") as mock_console:
        mock_console.confirm_action.return_value = False

        with pytest.raises(SystemExit) as exc:
            cli.run()

        assert exc.value.code == 0
        mock_console.print_warning.assert_called_with("Commit cancelled by user.")


def test_handle_commit_with_flags(cli):
    """Test commit with various flags."""
    mock_file = GitFile("test.py", "A", old_path=None, size=100, hash="abc123")
    cli.git.get_staged_files = MagicMock(return_value=[mock_file])
    cli.git.create_commit = MagicMock(return_value=True)

    cli.run(auto_commit=True, combine_commits=True, debug=True)

    cli.git.create_commit.assert_called_once()


def test_handle_commit_api_error(cli):
    """Test handling API error."""
    mock_file = GitFile("test.py", "A", old_path=None, size=100, hash="abc123")
    cli.git.get_staged_files = MagicMock(return_value=[mock_file])
    cli.ai_service.generate_commit_message = MagicMock(side_effect=Exception("API error"))

    with pytest.raises(SystemExit) as exc:
        cli.run(auto_commit=True)

    assert exc.value.code == 1


def test_create_batches_with_ignored_files(cli):
    """Test batch creation with ignored files."""
    mock_files = [
        GitFile("test.py", "A", old_path=None, size=100, hash="abc123"),
        GitFile("node_modules/test.js", "A", old_path=None, size=100, hash="def456"),
        GitFile("test2.py", "A", old_path=None, size=100, hash="ghi789"),
    ]
    batches = cli._create_batches(mock_files)

    assert len(batches) == 1
    assert len(batches[0]) == 2
    assert all("node_modules" not in f.path for f in batches[0])


def test_create_batches_git_error(cli):
    """Test batch creation with git error."""
    cli.git.get_staged_files = MagicMock(side_effect=subprocess.CalledProcessError(1, "git"))

    batches = cli._create_batches([])

    assert len(batches) == 0


def test_handle_batch_no_changes(cli):
    """Test handling batch with no changes."""
    mock_files = [GitFile("test.py", "A", old_path=None, size=100, hash="abc123")]
    cli.git.create_commit = MagicMock(return_value=False)

    result = cli._handle_batch(mock_files, 1, 1)

    assert result is None


def test_create_combined_commit_success(cli):
    """Test successful creation of combined commit."""
    batches = [
        {
            "files": [GitFile("test1.py", "A", old_path=None, size=100, hash="abc123")],
            "commit_data": MagicMock(
                title="test1",
                body={"feat": {"emoji": "✨", "changes": ["change1"]}},
                summary="summary1",
            ),
        },
        {
            "files": [GitFile("test2.py", "A", old_path=None, size=100, hash="def456")],
            "commit_data": MagicMock(
                title="test2",
                body={"fix": {"emoji": "🐛", "changes": ["change2"]}},
                summary="summary2",
            ),
        },
    ]
    cli.git.create_commit = MagicMock(return_value=True)
    cli._create_combined_commit(batches)
    cli.git.create_commit.assert_called_once()
    args, _ = cli.git.create_commit.call_args
    assert args[0] == "📦 chore: combine multiple changes"
    assert not args[1].startswith("📦 chore: combine multiple changes")


def test_create_combined_commit_no_changes(cli):
    """Test combined commit with no changes."""
    batches = [
        {
            "files": [GitFile("test1.py", "A", old_path=None, size=100, hash="abc123")],
            "commit_data": MagicMock(
                title="test1",
                body={"feat": {"emoji": "✨", "changes": ["change1"]}},
                summary="summary1",
            ),
        },
    ]
    cli.git.create_commit = MagicMock(return_value=False)

    with pytest.raises(SystemExit) as exc:
        cli._create_combined_commit(batches)

    assert exc.value.code == 0


def test_debug_mode(cli):
    """Test debug mode functionality."""
    cli.git.get_staged_files = MagicMock(side_effect=Exception("Test error"))

    with pytest.raises(SystemExit) as exc:
        cli.run(debug=True)

    assert exc.value.code == 1


def test_process_files_in_batches_error(cli):
    """Test error handling in batch processing."""
    mock_files = [GitFile(f"test{i}.py", "A", old_path=None, size=100, hash="abc123") for i in range(4)]
    cli.git.get_diff = MagicMock(side_effect=GitError("Git error"))

    with pytest.raises(SystemExit) as exc:
        cli.process_files_in_batches(mock_files)

    assert exc.value.code == 1


def test_handle_batch_value_error(cli):
    """Test handling value error in batch processing."""
    mock_files = [GitFile("test.py", "A", old_path=None, size=100, hash="abc123")]
    cli.git.get_diff = MagicMock(side_effect=ValueError("Invalid value"))

    result = cli._handle_batch(mock_files, 1, 1)

    assert result is None


def test_handle_batch_git_error(cli):
    """Test handling git error in batch processing."""
    mock_files = [GitFile("test.py", "A", old_path=None, size=100, hash="abc123")]
    cli.git.get_diff = MagicMock(side_effect=GitError("Git error"))

    result = cli._handle_batch(mock_files, 1, 1)

    assert result is None


def test_maybe_create_branch(cli):
    """Ensure branch is created when commit is complex."""
    analysis = CommitAnalysis(
        estimated_tokens=2000,
        estimated_cost=0.2,
        num_files=10,
        warnings=[],
        is_complex=True,
    )
    cli.git.create_and_checkout_branch = MagicMock()
    with patch("commitloom.cli.cli_handler.console") as mock_console:
        mock_console.confirm_branch_creation.return_value = True
        cli._maybe_create_branch(analysis)
        cli.git.create_and_checkout_branch.assert_called_once()


def test_maybe_create_branch_not_complex(cli):
    """Ensure no branch is created when commit is simple."""
    analysis = CommitAnalysis(
        estimated_tokens=10,
        estimated_cost=0.0,
        num_files=1,
        warnings=[],
        is_complex=False,
    )
    cli.git.create_and_checkout_branch = MagicMock()
    with patch("commitloom.cli.cli_handler.console") as mock_console:
        mock_console.confirm_branch_creation.return_value = True
        cli._maybe_create_branch(analysis)
        cli.git.create_and_checkout_branch.assert_not_called()
