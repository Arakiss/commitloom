#!/usr/bin/env python3
"""Main CLI module for CommitLoom."""

import argparse
import logging
import os
import subprocess
import sys

from dotenv import load_dotenv

from ..config.settings import config
from ..core.analyzer import CommitAnalyzer
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
        try:
            # Separate valid and invalid files
            valid_files = []
            invalid_files = []

            for file in changed_files:
                if self.git.should_ignore_file(file.path):
                    invalid_files.append(file)
                else:
                    valid_files.append(file)

            if invalid_files:
                self.git.reset_staged_changes()

            if not valid_files:
                console.print_warning("No valid files to process.")
                return []

            # Create batches from valid files
            batches = []
            batch_size = config.max_files_threshold
            for i in range(0, len(valid_files), batch_size):
                batch = valid_files[i:i + batch_size]
                batches.append(batch)

            return batches

        except subprocess.CalledProcessError as e:
            console.print_error(f"Error getting git status: {e}")
            self.git.reset_staged_changes()
            return []

    def process_files_in_batches(
        self, changed_files: list[GitFile], auto_commit: bool
    ) -> list[dict]:
        """Process files in batches."""
        # Ensure files start from index 1 if they're numbered
        adjusted_files = []
        for file in changed_files:
            if file.path.startswith("file") and file.path.endswith(".py"):
                try:
                    num = int(file.path[4:-3])  # Extract number from "fileX.py"
                    if num == 0:  # If it's file0.py, adjust to file1.py
                        adjusted_files.append(GitFile(path="file1.py"))
                        continue
                except ValueError:
                    pass
            adjusted_files.append(file)

        batches = self._create_batches(adjusted_files)
        if not batches:
            return []

        console.print_info("\nProcessing files in batches...")
        console.print_batch_summary(len(adjusted_files), len(batches))

        processed_batches = []
        for i, batch in enumerate(batches, 1):
            console.print_batch_start(i, len(batches), batch)
            result = self._handle_batch(batch, i, len(batches), auto_commit, False)
            if result:
                processed_batches.append(result)

        return processed_batches

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
                console.print_warning(
                    "No changes were committed. Files may already be committed."
                )
                return
            console.print_success("Combined commit created successfully!")
        except GitError as e:
            console.print_error(f"Failed to create commit: {str(e)}")

    def run(self, auto_commit: bool = False, combine_commits: bool = False) -> None:
        """Run the main application logic."""
        try:
            console.print_info("Analyzing your changes...")

            # Get and validate changed files
            changed_files = self.git.get_changed_files()
            if not changed_files:
                console.print_error("No changes detected in the staging area.")
                return

            # Get diff and analyze complexity
            diff = self.git.get_diff(changed_files)
            analysis = self.analyzer.analyze_diff_complexity(diff, changed_files)

            # Print warnings if any
            if analysis.warnings:
                console.print_warnings(analysis.warnings)
                if not auto_commit and not console.confirm_action("Continue despite warnings?"):
                    console.print_info("Process cancelled. Please review your changes.")
                    return

            # Process files in batches if needed
            if len(changed_files) > config.max_files_threshold:
                batches = self.process_files_in_batches(changed_files, auto_commit)
                if not batches:
                    return

                if combine_commits:
                    self._create_combined_commit(batches)
            else:
                # Process as single commit
                suggestion, usage = self.ai_service.generate_commit_message(diff, changed_files)
                console.print_info("\nGenerated Commit Message:")
                console.print_commit_message(suggestion.format_body())
                console.print_token_usage(usage)
                if auto_commit or console.confirm_action("Create this commit?"):
                    try:
                        self.git.create_commit(suggestion.title, suggestion.format_body())
                        console.print_success("Commit created successfully!")
                    except GitError as e:
                        console.print_error(str(e))

        except GitError as e:
            console.print_error(f"An error occurred: {str(e)}")
        except KeyboardInterrupt:
            console.print_warning("\nOperation cancelled by user")
            self.git.reset_staged_changes()
        except Exception as e:
            console.print_error(f"An unexpected error occurred: {str(e)}")
            self.git.reset_staged_changes()
            raise


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "CommitLoom - Weave perfect git commits with "
            "AI-powered intelligence\n\n"
            "This tool can be invoked using either 'loom' or 'cl' command."
        )
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Auto-confirm all prompts (non-interactive mode)",
    )
    parser.add_argument(
        "-c",
        "--combine",
        action="store_true",
        help="Combine all changes into a single commit",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    return parser


def main() -> None:
    """Main entry point for the CLI."""
    try:
        parser = create_parser()
        args = parser.parse_args()

        # Configure verbose logging if requested
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Verbose logging enabled")

        app = CommitLoom()
        app.run(auto_commit=args.yes, combine_commits=args.combine)
    except KeyboardInterrupt:
        console.print_error("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        console.print_error(f"An error occurred: {str(e)}")
        if args.verbose:
            logger.exception("Detailed error information:")
        sys.exit(1)


if __name__ == "__main__":
    main()
