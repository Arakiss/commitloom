#!/usr/bin/env python3
"""Main CLI module for CommitLoom."""

import logging
import os
import subprocess
import sys

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


class CommitLoom:
    """Main application class."""

    def __init__(self):
        """Initialize CommitLoom."""
        self.git = GitOperations()
        self.analyzer = CommitAnalyzer()
        self.ai_service = AIService()
        self.auto_commit = False
        self.combine_commits = False

    def _handle_batch(
        self,
        batch: list[GitFile],
        batch_num: int,
        total_batches: int,
        auto_commit: bool,
        combine_commits: bool,
    ) -> dict | None:
        """Handle a single batch of files."""
        try:
            # Stage files
            self.git.stage_files([f.path for f in batch])

            # Get diff and analyze
            diff = self.git.get_diff(batch)
            analysis = self.analyzer.analyze_diff_complexity(diff, batch)

            # Print analysis
            console.print_warnings(analysis)

            if analysis.is_complex and not auto_commit:
                if not console.confirm_action("Continue despite warnings?"):
                    self.git.reset_staged_changes()
                    return None

            # Generate commit message
            suggestion, usage = self.ai_service.generate_commit_message(diff, batch)
            console.print_info("\nGenerated Commit Message:")
            console.print_commit_message(suggestion.format_body())
            console.print_token_usage(usage)

            if not auto_commit and not console.confirm_action("Create this commit?"):
                self.git.reset_staged_changes()
                return None

            # Create commit if not combining
            if not combine_commits:
                if not self.git.create_commit(suggestion.title, suggestion.format_body()):
                    console.print_warning(
                        "No changes were committed. Files may already be committed."
                    )
                    return None
                console.print_batch_complete(batch_num, total_batches)

            return {"files": batch, "commit_data": suggestion}

        except (GitError, ValueError) as e:
            console.print_error(str(e))
            self.git.reset_staged_changes()
            return None

    def _handle_combined_commit(
        self, suggestions: list[CommitSuggestion], auto_commit: bool
    ) -> None:
        """Handle creating a combined commit from multiple suggestions."""
        try:
            combined_message = self.ai_service.format_commit_message(suggestions)
            console.print_commit_message(combined_message)

            if not auto_commit and not console.confirm_action("Create this commit?"):
                self.git.reset_staged_changes()
                return

            self.git.create_commit(combined_message.title, combined_message.format_body())
            console.print_success("Combined commit created successfully!")

        except (GitError, ValueError) as e:
            console.print_error(str(e))
            self.git.reset_staged_changes()

    def _create_batches(self, changed_files: list[GitFile]) -> list[list[GitFile]]:
        """Create batches of files for processing."""
        if not changed_files:
            return []

        try:
            # Separate valid and invalid files
            valid_files = []
            invalid_files = []

            for file in changed_files:
                if self.git.should_ignore_file(file.path):
                    invalid_files.append(file)
                    console.print_warning(f"Ignoring file: {file.path}")
                else:
                    valid_files.append(file)

            if not valid_files:
                console.print_warning("No valid files to process.")
                return []

            # Create batches from valid files
            batches = []
            batch_size = config.max_files_threshold
            for i in range(0, len(valid_files), batch_size):
                batch = valid_files[i : i + batch_size]
                batches.append(batch)

            return batches

        except subprocess.CalledProcessError as e:
            console.print_error(f"Error getting git status: {e}")
            return []

    def process_files_in_batches(self, files: list[GitFile], auto_commit: bool = False) -> None:
        """Process files in batches."""
        if not files:
            return

        # Configure batch processor
        config = BatchConfig(
            batch_size=5,
            auto_commit=auto_commit,
            combine_commits=self.combine_commits
        )
        processor = BatchProcessor(config)
        processor.load_files(files)

        # Only use batches if we have more than 4 files
        if len(files) <= 4:
            try:
                # Process normally
                file_paths = [f.path for f in files]
                self.git.stage_files(file_paths)
                self._handle_batch(files, 1, 1, auto_commit, self.combine_commits)
            except GitError as e:
                self.console.print_error(str(e))
            return

        # Process in batches
        total_batches = (len(files) + config.batch_size - 1) // config.batch_size
        self.console.print_batch_summary(len(files), total_batches, config.batch_size)

        try:
            processor.process_all()
        except GitError as e:
            self.console.print_error(str(e))
            return

    def _create_combined_commit(self, batches: list[dict]) -> None:
        """Create a combined commit from all batches."""
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

        combined_commit = CommitSuggestion(
            title="📦 chore: combine multiple changes",
            body=all_changes,
            summary=" ".join(summary_points),
        )

        try:
            # Stage and commit all files
            self.git.stage_files(all_files)
            if not self.git.create_commit(
                combined_commit.title,
                combined_commit.format_body(),
            ):
                console.print_warning("No changes were committed. Files may already be committed.")
                return
            console.print_success("Combined commit created successfully!")
        except GitError as e:
            console.print_error(f"Failed to create commit: {str(e)}")

    def run(
        self, auto_commit: bool = False, combine_commits: bool = False, debug: bool = False
    ) -> None:
        """Run the main application logic."""
        try:
            # Configure logging
            console.setup_logging(debug)

            # Get changed files
            changed_files = self.git.get_staged_files()
            if not changed_files:
                console.print_error("No changes detected in the staging area.")
                return

            # Print changed files
            console.print_changed_files(changed_files)

            # Process files in batches
            batches = self.process_files_in_batches(changed_files, auto_commit)
            if not batches:
                return

            # Handle combined commit if requested
            if combine_commits and len(batches) > 1:
                suggestions = [batch["commit_data"] for batch in batches]
                self._handle_combined_commit(suggestions, auto_commit)

        except GitError as e:
            console.print_error(str(e))
            if debug:
                console.print_debug("Git error details:", exc_info=True)
            sys.exit(1)
        except Exception as e:
            console.print_error(f"An unexpected error occurred: {str(e)}")
            if debug:
                console.print_debug("Error details:", exc_info=True)
            sys.exit(1)


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
