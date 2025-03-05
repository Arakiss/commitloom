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
from ..services.metrics import metrics_manager
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

    def __init__(self, test_mode: bool = False, api_key: str | None = None):
        """Initialize CommitLoom.

        Args:
            test_mode: If True, initialize services in test mode.
            api_key: OpenAI API key to use for AI service.
        """
        # Get current repository path
        try:
            self.repo_path = os.path.basename(os.getcwd())
        except Exception:
            self.repo_path = "unknown_repo"
            
        self.git = GitOperations()
        self.analyzer = CommitAnalyzer()
        self.ai_service = AIService(api_key=api_key, test_mode=test_mode)
        self.auto_commit = False
        self.combine_commits = False
        self.console = console

    def _process_single_commit(self, files: list[GitFile]) -> None:
        """Process files as a single commit."""
        try:
            # Start tracking metrics
            metrics_manager.start_commit_tracking(repository=self.repo_path)
            
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
                metrics_manager.finish_commit_tracking(
                    files_changed=0,  # No files committed
                    tokens_used=usage.total_tokens,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    cost_in_eur=usage.total_cost,
                    model_used=self.ai_service.model_name
                )
                sys.exit(0)

            # Create commit
            commit_success = self.git.create_commit(suggestion.title, suggestion.format_body())
            if commit_success:
                console.print_success("Changes committed successfully!")
                
                # Record metrics
                metrics_manager.finish_commit_tracking(
                    files_changed=len(files),
                    tokens_used=usage.total_tokens,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    cost_in_eur=usage.total_cost,
                    model_used=self.ai_service.model_name
                )
            else:
                console.print_warning("No changes were committed. Files may already be committed.")
                self.git.reset_staged_changes()
                
                # Record metrics with 0 files
                metrics_manager.finish_commit_tracking(
                    files_changed=0,
                    tokens_used=usage.total_tokens,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    cost_in_eur=usage.total_cost,
                    model_used=self.ai_service.model_name
                )
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
            # Start tracking metrics
            metrics_manager.start_commit_tracking(repository=self.repo_path)
            
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
            commit_success = self.git.create_commit(suggestion.title, suggestion.format_body())
            if not commit_success:
                console.print_warning("No changes were committed. Files may already be committed.")
                self.git.reset_staged_changes()
                
                # Record metrics with 0 files
                metrics_manager.finish_commit_tracking(
                    files_changed=0,
                    tokens_used=usage.total_tokens,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    cost_in_eur=usage.total_cost,
                    model_used=self.ai_service.model_name,
                    batch_processing=True,
                    batch_number=batch_num,
                    batch_total=total_batches
                )
                return None

            # Record metrics
            metrics_manager.finish_commit_tracking(
                files_changed=len(batch),
                tokens_used=usage.total_tokens,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cost_in_eur=usage.total_cost,
                model_used=self.ai_service.model_name,
                batch_processing=True,
                batch_number=batch_num,
                batch_total=total_batches
            )

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

    def stats_command(self) -> None:
        """Display usage statistics."""
        # Get usage statistics
        stats = metrics_manager.get_statistics()
        
        console.console.print("\n[bold blue]📊 CommitLoom Usage Statistics[/bold blue]")
        
        # Display basic stats
        console.console.print("\n[bold cyan]Basic Statistics:[/bold cyan]")
        console.console.print(f"  • Total commits generated: {stats['total_commits']:,}")
        console.console.print(f"  • Total tokens used: {stats['total_tokens']:,}")
        console.console.print(f"  • Total cost: €{stats['total_cost_in_eur']:.4f}")
        console.console.print(f"  • Total files processed: {stats['total_files_processed']:,}")
        
        # Display time saved if available
        if 'time_saved_formatted' in stats:
            console.console.print(f"  • Total time saved: {stats['time_saved_formatted']}")
        
        # Display activity period if available
        if 'first_used_at' in stats and stats['first_used_at'] and 'days_active' in stats:
            console.console.print(f"  • Active since: {stats['first_used_at'].split('T')[0]}")
            console.console.print(f"  • Days active: {stats['days_active']}")
            
            if 'avg_commits_per_day' in stats:
                console.console.print(f"  • Average commits per day: {stats['avg_commits_per_day']:.2f}")
                console.console.print(f"  • Average cost per day: €{stats['avg_cost_per_day']:.4f}")
        
        # Display repository stats if available
        if stats['repositories']:
            console.console.print("\n[bold cyan]Repository Activity:[/bold cyan]")
            console.console.print(f"  • Most active repository: {stats['most_active_repository']}")
            console.console.print(f"  • Repositories used: {len(stats['repositories'])}")
        
        # Display model usage if available
        if stats['model_usage']:
            console.console.print("\n[bold cyan]Model Usage:[/bold cyan]")
            for model, count in stats['model_usage'].items():
                console.console.print(f"  • {model}: {count} commits")
        
        # Display batch vs single commits
        console.console.print("\n[bold cyan]Processing Methods:[/bold cyan]")
        console.console.print(f"  • Batch commits: {stats['batch_commits']}")
        console.console.print(f"  • Single commits: {stats['single_commits']}")
        
        # Get more detailed stats if commits exist
        if stats['total_commits'] > 0:
            model_stats = metrics_manager.get_model_usage_stats()
            if model_stats:
                console.console.print("\n[bold cyan]Detailed Model Stats:[/bold cyan]")
                for model, model_data in model_stats.items():
                    console.console.print(f"  • {model}:")
                    console.console.print(f"    - Total tokens: {model_data['tokens']:,}")
                    console.console.print(f"    - Total cost: €{model_data['cost']:.4f}")
                    console.console.print(f"    - Avg tokens per commit: {model_data['avg_tokens_per_commit']:.1f}")
    
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
