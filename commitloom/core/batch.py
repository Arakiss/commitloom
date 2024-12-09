"""Batch processing module for handling multiple files."""

from dataclasses import dataclass

from ..cli.cli_handler import console
from ..core.git import GitOperations


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = 5


class BatchProcessor:
    """Processor for handling files in batches."""

    def __init__(self, config: BatchConfig):
        """Initialize the batch processor."""
        self.config = config
        self.git = GitOperations()

    def process_files(self, files: list[str]) -> None:
        """
        Process a list of files in batches.

        Args:
            files: List of files to process
        """
        if not files:
            return

        # Split files into batches
        batches = [
            files[i : i + self.config.batch_size]
            for i in range(0, len(files), self.config.batch_size)
        ]

        # Process each batch
        for i, batch in enumerate(batches, 1):
            try:
                self._process_batch(batch)
            except Exception as e:
                console.print_error(f"Failed to process batch: {str(e)}")
                raise

    def _process_batch(self, files: list[str]) -> None:
        """
        Process a single batch of files.

        Args:
            files: List of files in the batch
        """
        # Get confirmation before staging files
        if not console.confirm_action("Stage these files?"):
            return

        # Stage files
        self.git.stage_files(files)
