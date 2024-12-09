"""Batch processing module."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from .git import GitError, GitFile, GitOperations

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int  # Maximum number of files per batch


class BatchProcessor:
    """Handles processing of files in batches."""

    def __init__(self, config: BatchConfig):
        self.config = config
        self.git = GitOperations()
        self._processing_queue: List[GitFile] = []
        self._processed_files: List[GitFile] = []

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

        # Take up to batch_size files
        batch = self._processing_queue[: self.config.batch_size]
        self._processing_queue = self._processing_queue[self.config.batch_size :]

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
        Process files in batches.

        This method handles the core batch processing logic:
        1. Reset staged changes
        2. Process files in small batches
        3. Track processed files

        Args:
            files: List of files to process
        """
        if not files:
            return

        try:
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
            raise
