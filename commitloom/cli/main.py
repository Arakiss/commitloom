#!/usr/bin/env python3
"""Main CLI module for CommitLoom."""

import argparse
import logging
import os
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
    ) -> CommitSuggestion | None:
        """Handle a single batch of files."""
        try:
            # Stage files
            self.git.stage_files([f.path for f in batch])

            # Get diff and analyze
            diff = self.git.get_diff(batch)
            analysis = self.analyzer.analyze_diff_complexity(diff, batch)

            # Print analysis
            console.print_analysis(analysis, batch)

            if analysis.is_complex and not auto_commit:
                if not console.confirm_proceed():
                    self.git.reset_staged_changes()
                    return None

            # Generate commit message
            suggestion, usage = self.ai_service.generate_commit_message(diff, batch)
            console.print_suggestion(suggestion)
            console.print_usage(usage)

            if not auto_commit and not console.confirm_commit(suggestion):
                self.git.reset_staged_changes()
                return None

            # Create commit if not combining
            if not combine_commits:
                self.git.create_commit(suggestion.title, suggestion.format_body())
                console.print_batch_completion(batch_num, total_batches)

            return suggestion

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
            console.print_suggestion(combined_message)

            if not auto_commit and not console.confirm_commit(combined_message):
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

        batches = []
        for i in range(0, len(changed_files), config.max_files_threshold):
            batch = changed_files[i : i + config.max_files_threshold]
            batches.append(batch)

        return batches

    def process_files_in_batches(
        self, changed_files: list[GitFile], auto_commit: bool = False
    ) -> list[dict]:
        """Process files in batches for better commit organization."""
        batches = self._create_batches(changed_files)
        if not batches:
            return []

        processed_batches = []
        for i, batch in enumerate(batches, 1):
            try:
                # Get diff and analyze
                diff = self.git.get_diff(batch)
                analysis = self.analyzer.analyze_diff_complexity(diff, batch)

                # Print analysis
                console.print_analysis(analysis, batch)

                if analysis.is_complex and not auto_commit:
                    if not console.confirm_action("Continue despite warnings?"):
                        continue

                # Generate commit message
                suggestion, usage = self.ai_service.generate_commit_message(diff, batch)
                processed_batches.append({
                    "files": batch,
                    "commit_data": suggestion,
                    "usage": usage
                })

                if auto_commit:
                    self.git.create_commit(suggestion.title, suggestion.format_body())

            except (GitError, ValueError) as e:
                console.print_error(f"Failed to process batch {i}: {str(e)}")
                if not auto_commit and not console.confirm_action("Try next batch?"):
                    break

        return processed_batches

    def _create_combined_commit(self, batches: list[dict]) -> None:
        """Create a combined commit from all batches."""
        all_changes = {}
        summary_points = []
        all_files = []

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
            "AI-powered intelligence"
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
