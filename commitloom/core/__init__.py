"""Core modules for CommitLoom.

This module contains the core functionality including:
- Git operations
- Commit analysis
- Batch processing
- Smart file grouping
"""

from .analyzer import ChangeNature, CommitAnalysis, CommitAnalyzer, Warning, WarningLevel
from .batch import BatchProcessor
from .git import GitError, GitFile, GitOperations
from .smart_grouping import ChangeType, FileGroup, FileRelationship, SmartGrouper

__all__ = [
    "CommitAnalyzer",
    "CommitAnalysis",
    "Warning",
    "WarningLevel",
    "ChangeNature",
    "GitOperations",
    "GitFile",
    "GitError",
    "BatchProcessor",
    "SmartGrouper",
    "ChangeType",
    "FileGroup",
    "FileRelationship",
]
