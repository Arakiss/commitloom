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


class BatchProcessor:
    """Handles processing of files in batches."""

    def __init__(self, config: BatchConfig):
        self.config = config
        self.git = GitOperations()

    def process_files(self, files: list[GitFile]) -> None:
        """Process files in batches or normally."""
        if len(files) <= BATCH_THRESHOLD:
            # Process normally if fewer than threshold
            try:
                file_paths = [f.path for f in files]
                self.git.stage_files(file_paths)
            except GitError as e:
                logger.error(f"Failed to process files: {str(e)}")
                raise
            return

        # Process in batches
        total_batches = (len(files) + self.config.batch_size - 1) // self.config.batch_size
        batches = []
        
        # Create batches
        for i in range(total_batches):
            start = i * self.config.batch_size
            end = min(start + self.config.batch_size, len(files))
            batches.append(files[start:end])

        # Process each batch
        for i, batch in enumerate(batches, 1):
            try:
                # Stage files in this batch
                file_paths = [f.path for f in batch]
                self.git.stage_files(file_paths)

                # Create commit for this batch
                title = f"feat: batch {i}/{total_batches} - {len(file_paths)} files"
                message = "Files in this batch:\n" + "\n".join(f"- {f}" for f in file_paths)
                self.git.create_commit(title, message)

            except GitError as e:
                logger.error(f"Failed to process batch {i}: {str(e)}")
                raise
