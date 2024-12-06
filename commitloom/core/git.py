"""Git operations and utilities."""

import subprocess
import logging
from typing import List, Optional
from dataclasses import dataclass
from fnmatch import fnmatch
import os

from ..config.settings import config

# Configure logger
logger = logging.getLogger(__name__)


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
            # Get status of files to handle deleted ones correctly
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()

            # Create a map of file statuses
            file_statuses = {line[3:]: line[:2].strip() for line in status}

            # Stage the specified files
            for file in files:
                if file in file_statuses:
                    try:
                        if file_statuses[file] == "D":
                            # For deleted files, use 'git rm'
                            result = subprocess.run(
                                ["git", "rm", file],
                                check=True,
                                capture_output=True,
                                text=True,
                            )
                        else:
                            # For other files, use 'git add'
                            result = subprocess.run(
                                ["git", "add", file],
                                check=True,
                                capture_output=True,
                                text=True,
                            )

                        if result.stderr:
                            if "warning:" in result.stderr.lower():
                                logger.warning(
                                    "Git warning while staging %s: %s",
                                    file,
                                    result.stderr.strip(),
                                )
                            elif "error:" in result.stderr.lower():
                                raise GitError(
                                    f"Error staging {file}: {result.stderr.strip()}"
                                )
                            else:
                                logger.info(
                                    "Git message while staging %s: %s",
                                    file,
                                    result.stderr.strip(),
                                )
                    except subprocess.CalledProcessError as e:
                        raise GitError(
                            f"Error staging {file}: {e.stderr.decode().strip()}"
                        )
                else:
                    logger.warning("File not found in git status: %s", file)

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            raise GitError(f"Failed to stage files: {error_msg}")

    @staticmethod
    def create_commit(
        title: str, message: str, files: Optional[List[str]] = None
    ) -> bool:
        """Create a git commit with the specified message."""
        try:
            if files:
                # Stage only the specified files
                GitOperations.stage_files(files)
            else:
                # Only check status when no files are explicitly provided
                status = subprocess.run(
                    ["git", "status"],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                if "nothing to commit" in status.stdout.lower():
                    logger.info("No changes to commit")
                    return False

            # Create the commit with the staged changes
            try:
                result = subprocess.run(
                    ["git", "commit", "-m", title, "-m", message],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Check for warnings in the output
                if result.stderr:
                    if "warning:" in result.stderr.lower():
                        logger.warning(
                            "Git warning during commit: %s", result.stderr.strip()
                        )
                    else:
                        logger.info(
                            "Git message during commit: %s", result.stderr.strip()
                        )

                return True

            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode() if e.stderr else str(e)
                if "nothing to commit" in error_msg.lower():
                    logger.info("No changes to commit")
                    return False
                raise GitError(f"Failed to create commit: {error_msg}")

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise GitError(f"Failed to create commit: {error_msg}")
        except GitError:
            # Re-raise GitError without modification
            raise

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
            subprocess.run(
                ["git", "stash", "-u"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to stash changes: {e.stderr.strip()}")

    @staticmethod
    def pop_stashed_changes() -> None:
        """Pop the most recent stashed changes."""
        try:
            subprocess.run(
                ["git", "stash", "pop"],
                check=True,
                capture_output=True,
                text=True,  # Changed from False to True to match test expectations
            )
        except subprocess.CalledProcessError as e:
            if b"No stash entries found" in e.stderr:
                return
            raise GitError(
                f"Failed to pop stashed changes: {e.stderr.decode().strip()}"
            )

    @staticmethod
    def get_staged_files() -> List[str]:
        """Get list of currently staged files."""
        try:
            return (
                subprocess.check_output(["git", "diff", "--staged", "--name-only"])
                .decode()
                .splitlines()
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get staged files: {str(e)}")
