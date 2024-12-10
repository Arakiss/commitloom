"""Git operations module."""

import logging
import os
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Git operation error."""

    pass


@dataclass
class GitFile:
    """Represents a file in git."""

    path: str
    status: str
    old_path: str | None = None
    size: int | None = None
    hash: str | None = None

    @property
    def is_binary(self) -> bool:
        """Check if file is binary."""
        return bool(self.size is not None and self.hash is not None)

    @property
    def is_renamed(self) -> bool:
        """Check if file was renamed."""
        return self.status == "R" and self.old_path is not None


class GitOperations:
    """Basic git operations handler."""

    @staticmethod
    def _handle_git_output(result: subprocess.CompletedProcess, context: str = "") -> None:
        """Handle git command output and log messages."""
        if result.stderr:
            if result.stderr.startswith("warning:"):
                logger.warning("Git warning%s: %s", f" {context}" if context else "", result.stderr)
            else:
                logger.info("Git message%s: %s", f" {context}" if context else "", result.stderr)

    @staticmethod
    def _is_binary_file(path: str) -> tuple[bool, int | None, str | None]:
        """Check if a file is binary and get its size and hash."""
        try:
            # Check if file exists
            if not os.path.exists(path):
                return False, None, None

            # Get file size
            size = os.path.getsize(path)

            # Get file hash
            result = subprocess.run(
                ["git", "hash-object", path], capture_output=True, text=True, check=True
            )
            file_hash = result.stdout.strip()

            # Check if file is binary using git's internal mechanism
            result = subprocess.run(
                ["git", "diff", "--numstat", "--cached", path],
                capture_output=True,
                text=True,
                check=True,
            )
            # Binary files show up as "-" in numstat output
            is_binary = "-\t-\t" in result.stdout

            return is_binary, size if is_binary else None, file_hash if is_binary else None
        except (subprocess.CalledProcessError, OSError):
            return False, None, None

    @staticmethod
    def reset_staged_changes() -> None:
        """Reset all staged changes."""
        try:
            result = subprocess.run(["git", "reset"], capture_output=True, text=True, check=True)
            GitOperations._handle_git_output(result)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to reset staged changes: {error_msg}")

    @staticmethod
    def stage_files(files: list[str]) -> None:
        """Stage a list of files."""
        if not files:
            return

        try:
            for file in files:
                result = subprocess.run(
                    ["git", "add", "--", file],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if result.stderr:
                    if result.stderr.startswith("warning:"):
                        logger.warning("Git warning while staging %s: %s", file, result.stderr)
                    else:
                        logger.info("Git message while staging %s: %s", file, result.stderr)
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
                path_info = line[3:].strip()

                # Skip ignored files
                if status == "!!":
                    continue

                # Handle renamed files
                if status[0] == "R" or status[1] == "R":
                    if " -> " in path_info:
                        old_path, new_path = path_info.split(" -> ")
                        # Remove quotes if present
                        if old_path.startswith('"') and old_path.endswith('"'):
                            old_path = old_path[1:-1]
                        if new_path.startswith('"') and new_path.endswith('"'):
                            new_path = new_path[1:-1]
                        files.append(GitFile(path=new_path, status="R", old_path=old_path))
                        continue

                # Remove quotes if present
                if path_info.startswith('"') and path_info.endswith('"'):
                    path_info = path_info[1:-1]

                # Include both staged and modified files
                # First character is staged status, second is unstaged
                if status[0] != " " and status[0] != "?":
                    is_binary, size, file_hash = GitOperations._is_binary_file(path_info)
                    files.append(
                        GitFile(path=path_info, status=status[0], size=size, hash=file_hash)
                    )
                if status[1] != " " and status[1] != "?":
                    # Only add if not already added with staged status
                    if not any(f.path == path_info for f in files):
                        is_binary, size, file_hash = GitOperations._is_binary_file(path_info)
                        files.append(
                            GitFile(path=path_info, status=status[1], size=size, hash=file_hash)
                        )

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
                logger.info("Nothing to commit")
                return False

            # Create commit
            cmd = ["git", "commit", "-m", title]
            if message:
                cmd.extend(["-m", message])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.stderr:
                if result.stderr.startswith("warning:"):
                    logger.warning("Git warning during commit: %s", result.stderr)
                else:
                    logger.info("Git message during commit: %s", result.stderr)
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
                # Only include paths that exist (new paths for renames, skip deleted files)
                valid_paths = []
                for f in files:
                    if f.status == "R" and f.old_path:
                        # For renames, use the new path
                        valid_paths.append(f.path)
                    elif f.status != "D":  # Skip deleted files
                        valid_paths.append(f.path)

                if valid_paths:
                    cmd.extend(["--"] + valid_paths)

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

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            GitOperations._handle_git_output(result, "during stash save")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to save stash: {error_msg}")

    @staticmethod
    def stash_pop() -> None:
        """Pop most recent stash."""
        try:
            result = subprocess.run(
                ["git", "stash", "pop"], capture_output=True, text=True, check=True
            )
            GitOperations._handle_git_output(result, "during stash pop")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to pop stash: {error_msg}")

    @staticmethod
    def unstage_file(file: str) -> None:
        """Unstage a specific file."""
        try:
            result = subprocess.run(
                ["git", "reset", "--", file],
                capture_output=True,
                text=True,
                check=True,
            )
            GitOperations._handle_git_output(result, f"while unstaging {file}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitError(f"Failed to unstage file: {error_msg}")
