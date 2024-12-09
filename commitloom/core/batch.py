"""Batch processing module."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from .git import GitError, GitFile, GitOperations

logger = logging.getLogger(__name__)

BATCH_THRESHOLD = 4  # Maximum number of files per batch for atomic commits


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = BATCH_THRESHOLD  # Default to BATCH_THRESHOLD for atomic commits


class BatchProcessor:
    """Handles processing of files in batches."""

    def __init__(self, config: BatchConfig):
        self.config = config
        self.git = GitOperations()
        self._processing_queue: List[GitFile] = []
        self._processed_files: List[GitFile] = []

    def _save_current_state(self) -> None:
        """Save current git state to stash."""
        try:
            self.git.stash_save("commitloom_batch_processing_temp")
        except GitError as e:
            logger.error(f"Failed to save state: {str(e)}")
            raise

    def _restore_state(self) -> None:
        """Restore previously saved git state."""
        try:
            self.git.stash_pop()
        except GitError as e:
            logger.error(f"Failed to restore state: {str(e)}")
            raise

    def _prepare_batch(self, files: List[GitFile]) -> None:
        """Prepare files for batch processing."""
        # Reset any staged changes
        self.git.reset_staged_changes()

        # Add files to processing queue
        self._processing_queue.extend(files)

    def _get_next_batch(self) -> Optional[List[GitFile]]:
        """Get next batch of files to process."""
        if not self._processing_queue:
            return None

        # Take up to BATCH_THRESHOLD files
        batch = self._processing_queue[:BATCH_THRESHOLD]
        self._processing_queue = self._processing_queue[BATCH_THRESHOLD:]

        return batch

    def _process_batch(self, batch: List[GitFile]) -> None:
        """Process a single batch of files."""
        try:
            # Stage only the files in this batch
            file_paths = [f.path for f in batch]
            self.git.stage_files(file_paths)

            # Mark files as processed
            self._processed_files.extend(batch)

        except GitError as e:
            logger.error(f"Failed to process batch: {str(e)}")
            raise

    def process_files(self, files: List[GitFile]) -> None:
        """
        Process files in atomic batches.

        This method handles the case where files may already be staged.
        It will:
        1. Save current state (stash)
        2. Reset staged changes
        3. Process files in small batches (3-4 files)
        4. Restore original state

        Args:
            files: List of files to process
        """
        if not files:
            return

        try:
            # Save current state
            self._save_current_state()

            # Prepare files for processing
            self._prepare_batch(files)

            # Process files in batches
            while batch := self._get_next_batch():
                self._process_batch(batch)

            # Cleanup
            self._processing_queue = []
            self._processed_files = []

        except GitError as e:
            logger.error(f"Batch processing failed: {str(e)}")
            # Try to restore state
            try:
                self._restore_state()
            except GitError:
                pass  # Already logged in _restore_state
            raise
        finally:
            # Always try to restore state
            try:
                self._restore_state()
            except GitError:
                pass  # Already logged in _restore_state
