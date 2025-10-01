"""CommitLoom - Weave perfect git commits with AI-powered intelligence."""

from .cli.cli_handler import CommitLoom
from .core.analyzer import CommitAnalysis, CommitAnalyzer, Warning, WarningLevel
from .core.git import GitError, GitFile, GitOperations
from .services.ai_service import AIService, CommitSuggestion, TokenUsage

__version__ = "1.6.4"
__author__ = "Petru Arakiss"
__email__ = "petruarakiss@gmail.com"

__all__ = [
    "CommitLoom",
    "GitOperations",
    "GitFile",
    "GitError",
    "CommitAnalyzer",
    "CommitAnalysis",
    "Warning",
    "WarningLevel",
    "AIService",
    "CommitSuggestion",
    "TokenUsage",
]
