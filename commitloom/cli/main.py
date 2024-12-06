#!/usr/bin/env python3
"""Main CLI module for CommitLoom."""

from typing import List, Dict
from dotenv import load_dotenv
import os
from pathlib import Path
import sys
import subprocess

# Load environment variables at module level
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from ..core.git import GitOperations, GitFile, GitError
from ..core.analyzer import CommitAnalyzer, CommitAnalysis
from ..services.ai_service import AIService, CommitSuggestion
from ..config.settings import config
from . import console

class CommitLoom:
    """Main application class."""

    def __init__(self):
        """Initialize CommitLoom."""
        self.git = GitOperations()
        self.analyzer = CommitAnalyzer()
        self.ai_service = AIService()

    def process_files_in_batches(self, changed_files: List[GitFile], auto_commit: bool = False) -> List[Dict]:
        """Process files in batches for better commit organization."""
        total_files = len(changed_files)
        total_batches = (total_files + config.max_files_threshold - 1) // config.max_files_threshold
        
        # Mostrar resumen inicial del proceso por lotes
        console.print_batch_summary(total_files, total_batches)
        
        batches = []
        for i in range(0, total_files, config.max_files_threshold):
            batch = changed_files[i:i + config.max_files_threshold]
            batch_num = len(batches) + 1
            
            # Mostrar inicio del lote actual
            console.print_batch_start(batch_num, total_batches, batch)
            
            try:
                # Get combined diff for batch
                batch_diff = self.git.get_diff(batch)
                
                # Generate commit message
                suggestion, usage = self.ai_service.generate_commit_message(batch_diff, batch)
                
                batches.append({
                    "files": batch,
                    "commit_data": suggestion,
                    "usage": usage
                })
                
                # Mostrar completado del lote
                console.print_batch_complete(batch_num, total_batches)
                console.print_token_usage(usage, batch_num)
                
                # Si estamos en modo automático, crear el commit inmediatamente
                if auto_commit:
                    self._create_individual_commit(batches[-1], auto_confirm=True)
                
                if batch_num < total_batches and not auto_commit:
                    if not console.confirm_batch_continue():
                        console.print_warning("Batch processing paused. Remaining files will be skipped.")
                        break
                
            except Exception as e:
                console.print_error(f"Failed to process batch {batch_num}: {str(e)}")
                if not auto_commit and not console.confirm_action("Try next batch?"):
                    break
        
        return batches

    def run(self) -> None:
        """Run the main application logic."""
        try:
            console.print_info("Analyzing your changes...")

            try:
                changed_files = self.git.get_changed_files()
            except GitError as e:
                console.print_error(f"An error occurred: {str(e)}")
                return

            if not changed_files:
                console.print_error("No changes detected in the staging area.")
                return

            # Print changed files
            console.print_changed_files(changed_files)

            # Get diff and analyze complexity
            diff = self.git.get_diff(changed_files)
            analysis = self.analyzer.analyze_diff_complexity(diff, changed_files)

            # Print warnings if any
            if analysis.warnings:
                console.print_warnings(analysis)

            # Si hay más archivos que el límite, iniciamos el proceso por lotes
            if len(changed_files) > config.max_files_threshold:
                # Preguntar si queremos automatizar todo el proceso
                auto_commit = console.confirm_action("Would you like to automate the entire process?")
                batches = self.process_files_in_batches(changed_files, auto_commit)
                
                if not batches:
                    console.print_error("No batches were processed successfully.")
                    return
                
                # Mostrar resumen de todos los batches
                console.print_info("\n📑 Batch Processing Summary:")
                for i, batch in enumerate(batches, 1):
                    console.print_batch_info(i, [f.path for f in batch["files"]])
                    console.print_commit_message(
                        self.ai_service.format_commit_message(batch["commit_data"])
                    )
                
                # Si no estamos en modo automático, preguntar cómo manejar los commits
                if not auto_commit:
                    if console.confirm_action("Would you like to create individual commits for each batch?"):
                        for batch in batches:
                            self._create_individual_commit(batch)
                    else:
                        self._create_combined_commit(batches)
                
            else:
                # Process as single commit for small changes
                suggestion, usage = self.ai_service.generate_commit_message(diff, changed_files)
                console.print_info("\nGenerated Commit Message:")
                console.print_commit_message(self.ai_service.format_commit_message(suggestion))
                console.print_token_usage(usage)
                
                if console.confirm_action("Create this commit?"):
                    try:
                        self.git.create_commit(
                            suggestion.title,
                            self.ai_service.format_commit_message(suggestion)
                        )
                        console.print_success("Commit created successfully!")
                    except GitError as e:
                        console.print_error(str(e))

        except GitError as e:
            console.print_error(str(e))
        except Exception as e:
            console.print_error(f"An error occurred: {str(e)}")

    def _create_individual_commit(self, batch: Dict, auto_confirm: bool = False) -> None:
        """Create an individual commit for a batch."""
        files = [f.path for f in batch["files"]]
        commit_data = batch["commit_data"]
        
        console.print_info("Creating commit for:")
        for file in files:
            console.print_info(f"  - {file}")
            
        console.print_info("With message:")
        console.print_commit_message(
            self.ai_service.format_commit_message(commit_data)
        )
        
        if auto_confirm or console.confirm_action("Create this commit?"):
            try:
                # Stage and commit the files
                self.git.stage_files(files)
                if not self.git.create_commit(
                    commit_data.title,
                    self.ai_service.format_commit_message(commit_data)
                ):
                    console.print_warning("No changes were committed. Files may already be committed.")
                    return
                console.print_success("Commit created successfully!")
            except GitError as e:
                console.print_error(f"Failed to create commit: {str(e)}")
                # Show git status for debugging
                try:
                    status = subprocess.run(
                        ["git", "status", "--short"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    if status.stdout:
                        console.print_info("\nCurrent git status:")
                        for line in status.stdout.splitlines():
                            console.print_info(f"  {line}")
                except Exception:
                    pass  # Ignore status check errors

    def _create_combined_commit(self, batches: List[Dict]) -> None:
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
            summary=" ".join(summary_points)
        )
        
        try:
            # Stage and commit all files
            self.git.stage_files(all_files)
            if not self.git.create_commit(
                combined_commit.title,
                self.ai_service.format_commit_message(combined_commit)
            ):
                console.print_warning("No changes were committed. Files may already be committed.")
                return
            console.print_success("Combined commit created successfully!")
        except GitError as e:
            console.print_error(f"Failed to create commit: {str(e)}")
            # Show git status for debugging
            try:
                status = subprocess.run(
                    ["git", "status", "--short"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                if status.stdout:
                    console.print_info("\nCurrent git status:")
                    for line in status.stdout.splitlines():
                        console.print_info(f"  {line}")
            except Exception:
                pass  # Ignore status check errors

def main():
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

if __name__ == '__main__':
    main()
