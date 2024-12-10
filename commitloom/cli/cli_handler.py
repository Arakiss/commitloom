#!/usr/bin/env python3
"""Main CLI handler module for CommitLoom."""

import logging
import os
import subprocess
import sys

from dotenv import load_dotenv

from ..core.analyzer import CommitAnalyzer
from ..core.git import GitError, GitFile, GitOperations
from ..services.ai_service import AIService
from . import console

env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Minimum number of files to activate batch processing
BATCH_THRESHOLD = 3


class CommitLoom:
    """Main application class."""

    def __init__(self, test_mode: bool = False):
        """Initialize CommitLoom.

        Args:
            test_mode: If True, initialize services in test mode.
        """
        self.git = GitOperations()
        self.analyzer = CommitAnalyzer()
        self.ai_service = AIService(test_mode=test_mode)
        self.auto_commit = False
        self.combine_commits = False
        self.console = console

    def _process_single_commit(self, files: list[GitFile]) -> None:
        """Process files as a single commit."""
        try:
            # Stage files
            file_paths = [f.path for f in files]
            self.git.stage_files(file_paths)

            # Get diff and analyze
            diff = self.git.get_diff(files)
            analysis = self.analyzer.analyze_diff_complexity(diff, files)

            # Print analysis
            console.print_warnings(analysis)

            try:
                # Generate commit message
                suggestion, usage = self.ai_service.generate_commit_message(diff, files)
                console.print_info("\nGenerated Commit Message:")
                console.print_commit_message(suggestion.format_body())
                console.print_token_usage(usage)
            except Exception as e:
                # Handle API errors specifically
                console.print_error(f"API error: {str(e)}")
                self.git.reset_staged_changes()
                sys.exit(1)

            # Confirm commit if not in auto mode
            if not self.auto_commit and not console.confirm_action("Proceed with commit?"):
                console.print_warning("Commit cancelled by user.")
                self.git.reset_staged_changes()
                sys.exit(0)

            # Create commit
            if self.git.create_commit(suggestion.title, suggestion.format_body()):
                console.print_success("Changes committed successfully!")
            else:
                console.print_warning("No changes were committed. Files may already be committed.")
                self.git.reset_staged_changes()
                sys.exit(0)

        except GitError as e:
            console.print_error(f"Git error: {str(e)}")
            self.git.reset_staged_changes()
            sys.exit(1)
        except ValueError as e:
            console.print_error(f"Value error: {str(e)}")
            self.git.reset_staged_changes()
            sys.exit(1)

    def _handle_batch(
        self,
        batch: list[GitFile],
        batch_num: int,
        total_batches: int,
    ) -> dict[str, object] | None:
        """Handle a single batch of files."""
        try:
            # Stage files
            file_paths = [f.path for f in batch]
            self.git.stage_files(file_paths)

            # Get diff and analyze
            diff = self.git.get_diff(batch)
            analysis = self.analyzer.analyze_diff_complexity(diff, batch)

            # Print analysis
            console.print_warnings(analysis)

            try:
                # Generate commit message
                suggestion, usage = self.ai_service.generate_commit_message(diff, batch)
                console.print_info("\nGenerated Commit Message:")
                console.print_commit_message(suggestion.format_body())
                console.print_token_usage(usage)
            except Exception as e:
                # Handle API errors specifically
                console.print_error(f"API error: {str(e)}")
                self.git.reset_staged_changes()
                return None

            # Create commit
            if not self.git.create_commit(suggestion.title, suggestion.format_body()):
                console.print_warning("No changes were committed. Files may already be committed.")
                self.git.reset_staged_changes()
                return None

            console.print_batch_complete(batch_num, total_batches)
            return {"files": batch, "commit_data": suggestion}

        except GitError as e:
            console.print_error(f"Git error: {str(e)}")
            self.git.reset_staged_changes()
            return None
        except ValueError as e:
            console.print_error(f"Value error: {str(e)}")
            self.git.reset_staged_changes()
            return None

    def _create_batches(self, changed_files: list[GitFile]) -> list[list[GitFile]]:
        """Create batches of files for processing."""
        if not changed_files:
            return []

        try:
            # Separate valid and invalid files
            valid_files = []
            invalid_files = []

            for file in changed_files:
                if hasattr(self.git, "should_ignore_file") and self.git.should_ignore_file(
                    file.path
                ):
                    invalid_files.append(file)
                    console.print_warning(f"Ignoring file: {file.path}")
                else:
                    valid_files.append(file)

            if not valid_files:
                console.print_warning("No valid files to process.")
                return []

            # Create batches from valid files
            batches = []
            batch_size = BATCH_THRESHOLD
            for i in range(0, len(valid_files), batch_size):
                batch = valid_files[i : i + batch_size]
                batches.append(batch)

            return batches

        except subprocess.CalledProcessError as e:
            console.print_error(f"Error getting git status: {e}")
            return []

    def _create_combined_commit(self, batches: list[dict]) -> None:
        """Create a combined commit from multiple batches."""
        try:
            # Extract commit data
            all_changes = {}
            summary_points = []
            all_files: list[str] = []

            for batch in batches:
                commit_data = batch["commit_data"]
                for category, content in commit_data.body.items():
                    if category not in all_changes:
                        all_changes[category] = {"emoji": content["emoji"], "changes": []}
                    all_changes[category]["changes"].extend(content["changes"])
                summary_points.append(commit_data.summary)
                all_files.extend(f.path for f in batch["files"])

            # Create combined commit message
            title = "📦 chore: combine multiple changes"
            body = "\n\n".join(
                [
                    title,
                    "\n".join(
                        f"{data['emoji']} {category}:" for category, data in all_changes.items()
                    ),
                    "\n".join(
                        f"- {change}" for data in all_changes.values() for change in data["changes"]
                    ),
                    " ".join(summary_points),
                ]
            )

            # Stage and commit all files
            self.git.stage_files(all_files)
            if not self.git.create_commit(title, body):
                console.print_warning("No changes were committed. Files may already be committed.")
                self.git.reset_staged_changes()
                sys.exit(0)

            console.print_success("Combined commit created successfully!")

        except GitError as e:
            console.print_error(f"Git error: {str(e)}")
            self.git.reset_staged_changes()
            sys.exit(1)
        except ValueError as e:
            console.print_error(f"Value error: {str(e)}")
            self.git.reset_staged_changes()
            sys.exit(1)

    def process_files_in_batches(self, files: list[GitFile]) -> None:
        """Process files in batches if needed."""
        if not files:
            return

        try:
            # Only use batch processing if we have more than BATCH_THRESHOLD files
            if len(files) <= BATCH_THRESHOLD:
                self._process_single_commit(files)
                return

            # Process files in batches
            batches = self._create_batches(files)
            processed_batches = []

            for i, batch in enumerate(batches, 1):
                # Reset any previous staged changes
                self.git.reset_staged_changes()

                # Process this batch
                result = self._handle_batch(batch, i, len(batches))
                if result:
                    processed_batches.append(result)
                else:
                    # If batch processing failed or was cancelled, reset and return
                    self.git.reset_staged_changes()
                    sys.exit(1)

            # If combining commits, create the combined commit
            if self.combine_commits and processed_batches:
                self._create_combined_commit(processed_batches)

        except GitError as e:
            console.print_error(f"Git error: {str(e)}")
            self.git.reset_staged_changes()
            sys.exit(1)
        except ValueError as e:
            console.print_error(f"Value error: {str(e)}")
            self.git.reset_staged_changes()
            sys.exit(1)

    def run(
        self, auto_commit: bool = False, combine_commits: bool = False, debug: bool = False
    ) -> None:
        """Run the commit process."""
        if debug:
            self.console.setup_logging(debug)

        # Set auto-confirm mode based on auto_commit flag
        console.set_auto_confirm(auto_commit)

        self.auto_commit = auto_commit
        self.combine_commits = combine_commits

        # Get changed files
        try:
            changed_files = self.git.get_staged_files()
            if not changed_files:
                console.print_warning("No files staged for commit.")
                sys.exit(0)

            self.console.print_changed_files(changed_files)

            # Process files (in batches if needed)
            self.process_files_in_batches(changed_files)

        except GitError as e:
            console.print_error(f"Git error: {str(e)}")
            if debug:
                self.console.print_debug("Error details:", exc_info=True)
            sys.exit(1)
        except Exception as e:
            console.print_error(f"An unexpected error occurred: {str(e)}")
            if debug:
                self.console.print_debug("Error details:", exc_info=True)
            sys.exit(1)
