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

    def process_files_in_batches(
        self, changed_files: list[GitFile], auto_commit: bool = False
    ) -> list[dict]:
        """Process files in batches if needed.

        This method implements a queue-based approach to process files in batches:
        1. First unstages all files to start from a clean state (only if multiple batches)
        2. Creates batches of files to process
        3. For each batch:
           - Stages only the files in the current batch
           - Processes the batch
           - If successful, keeps the commit and moves to next batch
           - If failed, unstages and stops
        """
        console.print_debug("Starting batch processing")

        # Create work queue
        console.print_debug(f"Creating batches from {len(changed_files)} files")
        batches = self._create_batches(changed_files)
        if not batches:
            console.print_debug("No valid files to process")
            return []

        # Print batch processing plan
        total_files = len(changed_files)
        total_batches = len(batches)
        console.print_info("\nProcessing files in batches...")
        console.print_batch_summary(total_files, total_batches)

        # Start with a clean state only if we have multiple batches
        if total_batches > 1:
            console.print_debug("Multiple batches detected, resetting staged changes")
            self.git.reset_staged_changes()
        else:
            console.print_debug("Single batch detected, proceeding without reset")

        # Process each batch atomically
        results = []
        for batch_num, batch in enumerate(batches, 1):
            try:
                # 1. Stage current batch
                batch_files = [f.path for f in batch]
                console.print_debug(
                    f"Staging files for batch {batch_num}: {', '.join(batch_files)}"
                )
                self.git.stage_files(batch_files)
                console.print_batch_start(batch_num, total_batches, batch)

                # 2. Process batch
                console.print_debug(f"Processing batch {batch_num}/{total_batches}")
                result = self._handle_batch(
                    batch=batch,
                    batch_num=batch_num,
                    total_batches=total_batches,
                    auto_commit=auto_commit,
                    combine_commits=False,
                )

                # 3. Handle result
                if result:
                    # Batch processed successfully
                    console.print_debug(f"Batch {batch_num} processed successfully")
                    results.append(result)
                    # Clean staged files if more batches pending
                    if batch_num < total_batches:
                        console.print_debug("Cleaning staged files for next batch")
                        self.git.reset_staged_changes()
                else:
                    # Batch processing was cancelled or failed
                    console.print_debug(f"Batch {batch_num} processing cancelled or failed")
                    # _handle_batch already called reset_staged_changes
                    break

            except GitError as e:
                console.print_error(f"Error processing batch {batch_num}: {str(e)}")
                console.print_debug(f"Stack trace for batch {batch_num} error:", exc_info=True)
                self.git.reset_staged_changes()
                if not auto_commit and not console.confirm_action(
                    "Continue with remaining batches?"
                ):
                    console.print_debug("User chose to stop batch processing after error")
                    break
                console.print_debug("Continuing with next batch after error")

        console.print_debug(
            f"Batch processing completed. Processed {len(results)}/{total_batches} batches"
        )
        return results

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
        """Run the commit creation process.

        Args:
            auto_commit: Whether to skip confirmation prompts
            combine_commits: Whether to combine all changes into a single commit
            debug: Whether to enable debug logging
        """
        try:
            # Setup logging
            console.setup_logging(debug)
            console.print_debug("Starting CommitLoom")

            # Get and validate changed files
            console.print_info("Analyzing your changes...")
            changed_files = self.git.get_changed_files()
            if not changed_files:
                console.print_error("No changes detected in the staging area.")
                return

            # Get diff and analyze complexity
            console.print_debug("Getting diff and analyzing complexity")
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
                console.print_debug("Processing files in batches")
                batches = self.process_files_in_batches(changed_files, auto_commit)
                if not batches:
                    return

                if combine_commits:
                    console.print_debug("Combining commits")
                    self._create_combined_commit(batches)
            else:
                # Process as single commit
                console.print_debug("Processing as single commit")
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
            if debug:
                console.print_debug("Git error details:", exc_info=True)
        except KeyboardInterrupt:
            console.print_warning("\nOperation cancelled by user")
            self.git.reset_staged_changes()
        except Exception as e:
            console.print_error(f"An unexpected error occurred: {str(e)}")
            if debug:
                console.print_debug("Unexpected error details:", exc_info=True)
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
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
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
