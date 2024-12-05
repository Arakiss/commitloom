"""Git operations and utilities."""

import subprocess
from typing import List, Optional
from dataclasses import dataclass
from fnmatch import fnmatch

from ..config.settings import config


@dataclass
class GitFile:
    """Represents a git file with its metadata."""

    path: str
    size: Optional[int] = None
    hash: Optional[str] = None


class GitError(Exception):
    """Base exception for git-related errors."""

    pass


class GitOperations:
    """Handles all git-related operations."""

    @staticmethod
    def should_ignore_file(file_path: str) -> bool:
        """Determine if a file should be ignored based on configured patterns."""
        normalized_path = file_path.replace("\\", "/")
        return any(
            fnmatch(normalized_path, pattern) for pattern in config.ignored_patterns
        )

    @staticmethod
    def get_changed_files() -> List[GitFile]:
        """Get list of staged files, excluding ignored files."""
        try:
            files = (
                subprocess.check_output(
                    ["git", "diff", "--staged", "--name-only", "--"]
                )
                .decode("utf-8")
                .splitlines()
            )

            git_files = []
            for file in files:
                if not GitOperations.should_ignore_file(file):
                    try:
                        ls_file_output = (
                            subprocess.check_output(
                                ["git", "ls-files", "-s", file],
                                stderr=subprocess.DEVNULL,
                            )
                            .decode()
                            .strip()
                            .split()
                        )

                        if len(ls_file_output) >= 4:
                            file_hash = ls_file_output[1]
                            size_output = (
                                subprocess.check_output(
                                    ["git", "cat-file", "-s", file_hash],
                                    stderr=subprocess.DEVNULL,
                                )
                                .decode()
                                .strip()
                            )
                            git_files.append(
                                GitFile(
                                    path=file, size=int(size_output), hash=file_hash
                                )
                            )
                        else:
                            git_files.append(GitFile(path=file))
                    except (subprocess.CalledProcessError, ValueError, IndexError):
                        git_files.append(GitFile(path=file))

            return git_files
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get changed files: {str(e)}")

    @staticmethod
    def get_diff(files: Optional[List[GitFile]] = None) -> str:
        """Get the staged diff, handling binary files."""
        try:
            if files is None:
                files = GitOperations.get_changed_files()

            # Check for binary files using --numstat
            numstat = (
                subprocess.check_output(["git", "diff", "--staged", "--numstat"])
                .decode("utf-8")
                .strip()
            )

            # If we have binary files (shown as "-" in numstat)
            if "-\t-\t" in numstat:
                diff_message = "Binary files changed:\n"
                for file in files:
                    if file.size is not None:
                        diff_message += f"- {file.path} ({GitOperations.format_file_size(file.size)})\n"
                    else:
                        diff_message += f"- {file.path} (size unknown)\n"
                return diff_message

            # For text files, proceed with normal diff
            return subprocess.check_output(["git", "diff", "--staged", "--"]).decode(
                "utf-8"
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get diff: {str(e)}")

    @staticmethod
    def format_file_size(size: int) -> str:
        """Format file size in human readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    @staticmethod
    def create_commit(
        title: str, message: str, files: Optional[List[str]] = None
    ) -> bool:
        """
        Create a git commit with the specified message.

        Args:
            title: The commit title
            message: The detailed commit message
            files: Optional list of specific files to commit

        Returns:
            bool: True if commit was successful, False otherwise
        """
        try:
            if files:
                # Add specific files to the commit
                for file in files:
                    subprocess.run(
                        ["git", "add", file],
                        check=True,
                        capture_output=True,
                        text=True,
                    )

            # Create the commit
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    title,
                    "-m",
                    message,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return True

        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to create commit: {str(e)}")

    @staticmethod
    def reset_staged_changes() -> None:
        """Reset any staged changes."""
        try:
            subprocess.run(["git", "reset"], check=True)
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to reset staged changes: {str(e)}")
