"""Batch processing module."""

import logging
from collections import deque
from dataclasses import dataclass

from .git import GitError, GitFile, GitOperations

logger = logging.getLogger(__name__)

BATCH_THRESHOLD = 4  # Minimum number of files to activate batch processing


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = 5
    auto_commit: bool = False
    combine_commits: bool = False


class BatchProcessor:
    """Handles processing of files in batches."""

    def __init__(self, config: BatchConfig):
        self.config = config
        self.git = GitOperations()
        self.queue: deque[GitFile] = deque()

    def load_files(self, files: list[GitFile]) -> None:
        """Load files into the processing queue."""
        self.queue.extend(files)

    def should_batch(self) -> bool:
        """Check if batch processing should be used."""
        return len(self.queue) > BATCH_THRESHOLD

    def process_all(self) -> None:
        """Process all files."""
        if not self.should_batch():
            # Process normally if fewer than threshold
            try:
                files = [f.path for f in self.queue]
                self.git.stage_files(files)
            except GitError as e:
                logger.error(f"Failed to process files: {str(e)}")
                raise
            return

        try:
            # Save initial state
            self.git.stash_save("commitloom_temp_stash")

            # Process in batches
            while batch := self.get_next_batch():
                self.process_batch(batch)

        finally:
            # Always restore state
            self.git.stash_pop()

    def get_next_batch(self) -> list[GitFile] | None:
        """Get next batch of files from the queue."""
        if not self.queue:
            return None

        batch = []
        while self.queue and len(batch) < self.config.batch_size:
            batch.append(self.queue.popleft())
        return batch

    def process_batch(self, batch: list[GitFile]) -> None:
        """Process a single batch of files."""
        if not batch:
            return

        try:
            # Reset to clean state
            self.git.reset_staged_changes()

            # Stage all files in batch
            files_to_stage = [f.path for f in batch]
            self.git.stage_files(files_to_stage)

        except GitError as e:
            logger.error(f"Failed to process batch: {str(e)}")
            raise
