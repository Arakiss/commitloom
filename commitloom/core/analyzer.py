"""Analyzer module for commit complexity and cost estimation."""

from dataclasses import dataclass
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

    def __str__(self) -> str:
        """Return string representation of warning."""
        return self.message

    def __contains__(self, item: str) -> bool:
        """Support 'in' operator for string matching."""
        return item in self.message


@dataclass
class CommitAnalysis:
    """Results of analyzing a commit's complexity and cost."""

    estimated_tokens: int
    estimated_cost: float
    num_files: int
    warnings: list[Warning]
    is_complex: bool


class CommitAnalyzer:
    """Analyzes commit complexity and provides warnings."""

    @staticmethod
    def estimate_tokens_and_cost(text: str, model: str = config.default_model) -> tuple[int, float]:
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
    def analyze_diff_complexity(diff: str, changed_files: list[GitFile]) -> CommitAnalysis:
        """
        Analyzes the complexity of changes and returns warnings if necessary.

        Args:
            diff: The git diff to analyze
            changed_files: List of changed files

        Returns:
            CommitAnalysis object containing analysis results
        """
        warnings: list[Warning] = []
        estimated_tokens, estimated_cost = CommitAnalyzer.estimate_tokens_and_cost(diff)

        # Check token limit
        if estimated_tokens >= config.token_limit:
            warnings.append(
                Warning(
                    level=WarningLevel.HIGH,
                    message=(
                        f"The diff exceeds token limit ({estimated_tokens:,} tokens). "
                        f"Recommended limit is {config.token_limit:,} tokens."
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
        elif estimated_cost >= 0.05:  # more than 5 cents
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
                    level=WarningLevel.HIGH,
                    message=(
                        f"You're modifying {len(changed_files)} files. "
                        "For atomic commits, consider limiting to "
                        f"{config.max_files_threshold} files per commit."
                    ),
                )
            )

        # Analyze individual files
        for file in changed_files:
            try:
                file_diff = diff.split(f"diff --git a/{file.path} b/{file.path}")[1]
                file_diff = file_diff.split("diff --git")[0]
                file_tokens, file_cost = CommitAnalyzer.estimate_tokens_and_cost(file_diff)

                if file_tokens >= config.token_limit // 2:
                    warnings.append(
                        Warning(
                            level=WarningLevel.HIGH,
                            message=(
                                f"File {file.path} is too large ({file_tokens:,} tokens). "
                                "Consider splitting these changes across multiple commits."
                            ),
                        )
                    )

                if file_cost >= 0.05:  # More than 5 cents per file
                    warnings.append(
                        Warning(
                            level=WarningLevel.HIGH,
                            message=(
                                f"File {file.path} has expensive changes (€{file_cost:.4f}). "
                                "Consider splitting these changes across multiple commits."
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
            return f"€{cost:.2f}"
        elif cost >= 0.01:
            return f"{cost*100:.2f}¢"
        else:
            return "0.10¢"  # For very small costs, show as 0.10¢

    @staticmethod
    def get_cost_context(total_cost: float) -> str:
        """Get contextual message about the cost."""
        if total_cost >= 0.10:  # more than 10 cents
            return "very expensive"
        elif total_cost >= 0.05:  # more than 5 cents
            return "expensive"
        elif total_cost >= 0.01:  # more than 1 cent
            return "moderate"
        elif total_cost >= 0.001:  # more than 0.1 cents
            return "cheap"
        else:
            return "very cheap"
