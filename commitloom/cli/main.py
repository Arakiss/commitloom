#!/usr/bin/env python3
"""Main CLI module for CommitLoom."""

import logging
import os
import subprocess
import sys
from typing import Optional

from dotenv import load_dotenv

from ..config.settings import config
from ..core.analyzer import CommitAnalyzer
from ..core.batch import BatchConfig, BatchProcessor
from ..core.git import GitError, GitFile, GitOperations
from ..services.ai_service import AIService, CommitSuggestion
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

    def __init__(self):
        """Initialize CommitLoom."""
        self.git = GitOperations()
        self.analyzer = CommitAnalyzer()
        self.ai_service = AIService()
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

            # Generate commit message
            suggestion, usage = self.ai_service.generate_commit_message(diff, files)
            console.print_info("\nGenerated Commit Message:")
            console.print_commit_message(suggestion.format_body())
            console.print_token_usage(usage)

            # Create commit
            if self.git.create_commit(suggestion.title, suggestion.format_body()):
                console.print_success("Changes committed successfully!")
            else:
                console.print_warning("No changes were committed. Files may already be committed.")

        except (GitError, ValueError) as e:
            console.print_error(str(e))
            self.git.reset_staged_changes()

    def _handle_batch(
        self,
        batch: list[GitFile],
        batch_num: int,
        total_batches: int,
    ) -> Optional[dict]:
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

            # Generate commit message
            suggestion, usage = self.ai_service.generate_commit_message(diff, batch)
            console.print_info("\nGenerated Commit Message:")
            console.print_commit_message(suggestion.format_body())
            console.print_token_usage(usage)

            # Create commit
            if not self.git.create_commit(suggestion.title, suggestion.format_body()):
                console.print_warning("No changes were committed. Files may already be committed.")
                return None

            console.print_batch_complete(batch_num, total_batches)
            return {"files": batch, "commit_data": suggestion}

        except (GitError, ValueError) as e:
            console.print_error(str(e))
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

    def process_files_in_batches(self, files: list[GitFile]) -> None:
        """Process files in batches if needed."""
        if not files:
            return

        try:
            # Only use batch processing if we have more than BATCH_THRESHOLD files
            if len(files) <= BATCH_THRESHOLD:
                self._process_single_commit(files)
                return

            # Configure batch processor
            config = BatchConfig(batch_size=BATCH_THRESHOLD)
            processor = BatchProcessor(config)

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

        except GitError as e:
            self.console.print_error(str(e))
            return

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
                return

            self.console.print_changed_files(changed_files)

            # Process files (in batches if needed)
            self.process_files_in_batches(changed_files)

        except Exception as e:
            self.console.print_error(f"An unexpected error occurred: {str(e)}")
            if debug:
                self.console.print_debug("Error details:", exc_info=True)


def main() -> None:
    """Main entry point for the CLI."""
    try:
        app = CommitLoom()
        app.run()
    except KeyboardInterrupt:
        console.print_error("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        console.print_error(f"An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
