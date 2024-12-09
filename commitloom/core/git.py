"""Git operations module."""

import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Git operation error."""

    pass


@dataclass
class GitFile:
    """Represents a file tracked by git with its status."""

    path: str
    status: str


class GitOperations:
    """Basic git operations handler."""

    @staticmethod
    def reset_staged_changes() -> None:
        """Reset all staged changes."""
        try:
            subprocess.run(["git", "reset"], capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to reset staged changes: {error_msg}")

    @staticmethod
    def stage_files(files: list[str]) -> None:
        """Stage a list of files."""
        if not files:
            return

        try:
            # Stage files directly
            subprocess.run(
                ["git", "add", "--"] + files,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to stage files: {error_msg}")

    @staticmethod
    def get_staged_files() -> list[GitFile]:
        """Get list of staged files."""
        try:
            # Get status in porcelain format for both staged and unstaged changes
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
            )

            files = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                status = line[:2]
                path = line[3:].strip()

                # Skip ignored files
                if status == "!!":
                    continue

                # Remove quotes if present
                if path.startswith('"') and path.endswith('"'):
                    path = path[1:-1]

                # Include both staged and modified files
                # First character is staged status, second is unstaged
                if status[0] != " " and status[0] != "?":
                    files.append(GitFile(path=path, status=status[0]))
                if status[1] != " " and status[1] != "?":
                    # Only add if not already added with staged status
                    if not any(f.path == path for f in files):
                        files.append(GitFile(path=path, status=status[1]))

            return files

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to get staged files: {error_msg}")

    @staticmethod
    def get_file_status(file: str) -> str:
        """Get git status for a specific file."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", file], capture_output=True, text=True, check=True
            )
            return result.stdout[:2] if result.stdout else "  "
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to get file status: {error_msg}")

    @staticmethod
    def create_commit(title: str, message: str | None = None) -> bool:
        """Create a commit with the given title and message."""
        try:
            # First verify we have staged changes
            status = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                capture_output=True,
                text=True,
            )

            if status.returncode == 0:
                # No staged changes
                return False

            # Create commit
            cmd = ["git", "commit", "-m", title]
            if message:
                cmd.extend(["-m", message])

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to create commit: {error_msg}")

    @staticmethod
    def get_diff(files: list[GitFile] | None = None) -> str:
        """Get git diff for specified files or all staged changes."""
        try:
            cmd = ["git", "diff", "--staged"]
            if files:
                cmd.extend(f.path for f in files)

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to get diff: {error_msg}")

    @staticmethod
    def stash_save(message: str = "") -> None:
        """Save current changes to stash."""
        try:
            cmd = ["git", "stash", "push", "--include-untracked"]
            if message:
                cmd.extend(["-m", message])

            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to save stash: {error_msg}")

    @staticmethod
    def stash_pop() -> None:
        """Pop most recent stash."""
        try:
            subprocess.run(["git", "stash", "pop"], capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to pop stash: {error_msg}")

    @staticmethod
    def unstage_file(file: str) -> None:
        """Unstage a specific file."""
        try:
            subprocess.run(
                ["git", "reset", "--", file],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to unstage file: {error_msg}")
