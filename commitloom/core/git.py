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
            if files:
                # Get diff only for specified files
                file_paths = [f.path for f in files]
                return subprocess.check_output(
                    ["git", "diff", "--staged", "--"] + file_paths
                ).decode("utf-8")
            else:
                return subprocess.check_output(
                    ["git", "diff", "--staged", "--"]
                ).decode("utf-8")
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
    def stage_files(files: List[str]) -> None:
        """Stage specific files for commit."""
        try:
            # First unstage everything
            subprocess.run(["git", "reset"], check=True)
            
            # Then stage only the specified files
            for file in files:
                subprocess.run(
                    ["git", "add", file],
                    check=True,
                    capture_output=True,
                    text=True,
                )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to stage files: {str(e)}")

    @staticmethod
    def create_commit(
        title: str,
        message: str,
        files: Optional[List[str]] = None
    ) -> bool:
        """Create a git commit with the specified message."""
        try:
            if files:
                # Stage only the specified files
                GitOperations.stage_files(files)
            
            # Create the commit with the staged changes
            result = subprocess.run(
                ["git", "commit", "-m", title, "-m", message],
                check=True,
                capture_output=True,
                text=True,
            )
            
            # Return True if commit was created successfully
            return "nothing to commit" not in result.stdout.lower()

        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to create commit: {str(e)}")

    @staticmethod
    def reset_staged_changes() -> None:
        """Reset any staged changes."""
        try:
            subprocess.run(["git", "reset"], check=True)
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to reset staged changes: {str(e)}")

    @staticmethod
    def stash_changes() -> None:
        """Stash any uncommitted changes."""
        try:
            subprocess.run(["git", "stash", "-u"], check=True)
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to stash changes: {str(e)}")

    @staticmethod
    def pop_stashed_changes() -> None:
        """Pop the most recent stashed changes."""
        try:
            subprocess.run(["git", "stash", "pop"], check=True)
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to pop stashed changes: {str(e)}")

    @staticmethod
    def get_staged_files() -> List[str]:
        """Get list of currently staged files."""
        try:
            return subprocess.check_output(
                ["git", "diff", "--staged", "--name-only"]
            ).decode().splitlines()
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get staged files: {str(e)}")
