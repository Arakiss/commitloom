"""Analyzer module for commit complexity and cost estimation."""

from dataclasses import dataclass
from typing import List
from enum import Enum

from ..config.settings import config
from .git import GitFile


class WarningLevel(Enum):
    """Warning severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Warning:
    """Represents a warning about commit complexity or cost."""

    level: WarningLevel
    message: str


@dataclass
class CommitAnalysis:
    """Results of analyzing a commit's complexity and cost."""

    estimated_tokens: int
    estimated_cost: float
    num_files: int
    warnings: List[Warning]
    is_complex: bool


class CommitAnalyzer:
    """Analyzes commit complexity and provides warnings."""

    @staticmethod
    def estimate_tokens_and_cost(
        text: str, model: str = config.default_model
    ) -> tuple[int, float]:
        """
        Estimate the number of tokens and cost for a given text.

        Args:
            text: The text to analyze
            model: The AI model to use for estimation

        Returns:
            Tuple of (estimated_tokens, estimated_cost)
        """
        estimated_tokens = len(text) // config.token_estimation_ratio
        cost_per_token = config.model_costs[model].input / 1_000_000
        estimated_cost = estimated_tokens * cost_per_token

        return estimated_tokens, estimated_cost

    @staticmethod
    def analyze_diff_complexity(
        diff: str, changed_files: List[GitFile]
    ) -> CommitAnalysis:
        """
        Analyzes the complexity of changes and returns warnings if necessary.

        Args:
            diff: The git diff to analyze
            changed_files: List of changed files

        Returns:
            CommitAnalysis object containing analysis results
        """
        warnings: List[Warning] = []
        estimated_tokens, estimated_cost = CommitAnalyzer.estimate_tokens_and_cost(diff)

        # Check token limit
        if estimated_tokens >= config.token_limit:
            warnings.append(
                Warning(
                    level=WarningLevel.HIGH,
                    message=(
                        f"The diff is too large ({estimated_tokens:,} estimated tokens). "
                        f"Exceeds recommended limit of {config.token_limit:,} tokens."
                    ),
                )
            )

        # Check cost thresholds
        if estimated_cost >= 0.10:  # more than 10 cents
            warnings.append(
                Warning(
                    level=WarningLevel.HIGH,
                    message=(
                        f"This commit could be expensive (€{estimated_cost:.4f}). "
                        f"Consider splitting it into smaller commits."
                    ),
                )
            )
        elif estimated_cost >= config.cost_warning_threshold:  # configurable threshold
            warnings.append(
                Warning(
                    level=WarningLevel.MEDIUM,
                    message=(
                        f"This commit has a moderate cost (€{estimated_cost:.4f}). "
                        f"Consider if it can be optimized."
                    ),
                )
            )

        # Check number of files
        if len(changed_files) > config.max_files_threshold:
            warnings.append(
                Warning(
                    level=WarningLevel.MEDIUM,
                    message=(
                        f"You're modifying {len(changed_files)} files. "
                        f"For atomic commits, consider limiting to {config.max_files_threshold} files per commit."
                    ),
                )
            )

        # Analyze individual files
        for file in changed_files:
            try:
                file_diff = diff.split(f"diff --git a/{file.path} b/{file.path}")[1]
                file_diff = file_diff.split("diff --git")[0]
                file_tokens, file_cost = CommitAnalyzer.estimate_tokens_and_cost(
                    file_diff
                )

                if file_tokens >= config.token_limit // 2:
                    warnings.append(
                        Warning(
                            level=WarningLevel.HIGH,
                            message=(
                                f"File {file.path} has too many changes ({file_tokens:,} estimated tokens). "
                                f"Consider splitting these changes across multiple commits."
                            ),
                        )
                    )

                if file_cost >= 0.05:  # More than 5 cents per file
                    warnings.append(
                        Warning(
                            level=WarningLevel.HIGH,
                            message=(
                                f"File {file.path} has expensive changes (€{file_cost:.4f}). "
                                f"Consider splitting these changes across multiple commits."
                            ),
                        )
                    )
            except IndexError:
                # File might be binary or newly added
                pass

        return CommitAnalysis(
            estimated_tokens=estimated_tokens,
            estimated_cost=estimated_cost,
            num_files=len(changed_files),
            warnings=warnings,
            is_complex=any(w.level == WarningLevel.HIGH for w in warnings),
        )

    @staticmethod
    def format_cost_for_humans(cost: float) -> str:
        """Convert cost to human readable format with appropriate unit."""
        if cost >= 1.0:
            return f"€{cost:.2f} (euros)"
        elif cost >= 0.01:
            return f"{cost*100:.2f}¢ (cents)"
        elif cost >= 0.0001:  # Adjusted threshold for millicents
            return f"{cost*1000:.2f}m¢ (millicents)"
        else:
            return f"{cost*1000000:.2f}µ¢ (microcents)"

    @staticmethod
    def get_cost_context(total_cost: float) -> tuple[str, str]:
        """
        Get contextual message about the cost.
        Returns tuple of (message, color)
        """
        if total_cost >= 0.10:  # more than 10 cents
            return (
                "⚠️ Significant cost. Consider splitting changes into smaller commits.",
                "yellow",
            )
        elif total_cost >= 0.05:  # more than 5 cents
            return "ℹ️ Moderate cost. Within reasonable limits.", "blue"
        elif total_cost >= 0.01:  # more than 1 cent
            return "✅ Low cost. Perfectly acceptable.", "green"
        else:
            return "👍 Minimal cost. No concerns.", "green"
