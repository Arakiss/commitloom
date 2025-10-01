"""Analyzer module for commit complexity and cost estimation."""

from dataclasses import dataclass
from enum import Enum

from ..config.settings import config
from .git import GitFile

# Try to import tiktoken for precise token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


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


class ChangeNature(Enum):
    """Nature of changes in the diff."""

    ADDITIONS = "additions"
    MODIFICATIONS = "modifications"
    DELETIONS = "deletions"
    MIXED = "mixed"


class CommitAnalyzer:
    """Analyzes commit complexity and provides warnings."""

    @staticmethod
    def estimate_tokens_precise(text: str, model: str = config.default_model) -> int:
        """
        Estimate tokens using tiktoken if available, fallback to heuristic.

        Args:
            text: The text to tokenize
            model: The model name

        Returns:
            Estimated token count
        """
        if not TIKTOKEN_AVAILABLE:
            # Fallback to improved heuristic
            # Average token is ~4 characters for code, ~5 for natural language
            # Use conservative estimate of 3.5 characters per token
            return len(text) // 3

        try:
            # Map model names to tiktoken encodings
            encoding_map = {
                "gpt-4o": "o200k_base",
                "gpt-4o-mini": "o200k_base",
                "gpt-4.1": "o200k_base",
                "gpt-4.1-mini": "o200k_base",
                "gpt-4.1-nano": "o200k_base",
                "gpt-3.5-turbo": "cl100k_base",
                "gpt-4": "cl100k_base",
            }

            encoding_name = encoding_map.get(model, "cl100k_base")
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
        except Exception:
            # Fallback if tiktoken fails
            return len(text) // 3

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
        estimated_tokens = CommitAnalyzer.estimate_tokens_precise(text, model)
        if model in config.model_costs:
            cost_per_token = config.model_costs[model].input / 1_000_000
        else:
            print(f"[WARNING] Cost estimation is not available for model '{model}'.")
            cost_per_token = 0.0
        estimated_cost = estimated_tokens * cost_per_token
        return estimated_tokens, estimated_cost

    @staticmethod
    def analyze_change_nature(diff: str) -> ChangeNature:
        """
        Analyze the nature of changes in the diff.

        Args:
            diff: The git diff to analyze

        Returns:
            The nature of changes
        """
        lines = diff.split("\n")
        additions = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
        modifications = min(additions, deletions)

        total = additions + deletions

        if total == 0:
            return ChangeNature.MODIFICATIONS

        # Calculate percentages
        addition_ratio = (additions - modifications) / total if total > 0 else 0
        deletion_ratio = (deletions - modifications) / total if total > 0 else 0

        if addition_ratio > 0.7:
            return ChangeNature.ADDITIONS
        elif deletion_ratio > 0.7:
            return ChangeNature.DELETIONS
        else:
            return ChangeNature.MIXED

    @staticmethod
    def detect_dangerous_changes(changed_files: list[GitFile]) -> list[str]:
        """
        Detect potentially dangerous changes.

        Args:
            changed_files: List of changed files

        Returns:
            List of warning messages for dangerous changes
        """
        warnings = []

        dangerous_patterns = {
            "migration": "database migration",
            "schema": "database schema",
            ".env": "environment configuration",
            "secrets": "secrets file",
            "credentials": "credentials file",
            "production": "production configuration",
            "deploy": "deployment configuration",
        }

        for file in changed_files:
            for pattern, description in dangerous_patterns.items():
                if pattern in file.path.lower():
                    warnings.append(
                        f"Detected change in {description}: {file.path}. "
                        "Review carefully before committing."
                    )

        return warnings

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
        is_complex = False
        estimated_tokens, estimated_cost = CommitAnalyzer.estimate_tokens_and_cost(diff)

        # Analyze change nature for better warnings
        change_nature = CommitAnalyzer.analyze_change_nature(diff)

        # Check token limit
        if estimated_tokens >= config.token_limit:
            is_complex = True
            suggestion = "Consider splitting into smaller, focused commits"
            if change_nature == ChangeNature.ADDITIONS:
                suggestion = "Consider creating separate commits for new features/files"
            elif change_nature == ChangeNature.DELETIONS:
                suggestion = "Consider creating a cleanup/removal commit separately"

            warnings.append(
                Warning(
                    level=WarningLevel.HIGH,
                    message=(
                        f"The diff exceeds token limit ({estimated_tokens:,} tokens). "
                        f"Recommended limit is {config.token_limit:,} tokens. {suggestion}."
                    ),
                )
            )

        # Check number of files
        if len(changed_files) > config.max_files_threshold:
            is_complex = True
            # Provide specific suggestions based on file patterns
            file_types = {}
            for f in changed_files:
                ext = f.path.split(".")[-1] if "." in f.path else "other"
                file_types[ext] = file_types.get(ext, 0) + 1

            suggestion = "Consider splitting by file type or feature"
            if len(file_types) > 3:
                top_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:3]
                types_str = ", ".join(f"{t}({c})" for t, c in top_types)
                suggestion = f"Suggestion: Split by type - you have {types_str}"

            warnings.append(
                Warning(
                    level=WarningLevel.HIGH,
                    message=(
                        f"You're modifying {len(changed_files)} files. "
                        f"For atomic commits, consider limiting to {config.max_files_threshold} files. "
                        f"{suggestion}."
                    ),
                )
            )

        # Check cost thresholds
        if estimated_cost >= 0.10:  # more than 10 cents
            is_complex = True
            warnings.append(
                Warning(
                    level=WarningLevel.HIGH,
                    message=(
                        f"This commit could be expensive (€{estimated_cost:.4f}). "
                        f"Consider splitting it into smaller commits to reduce API costs."
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

        # Check for dangerous changes
        dangerous_warnings = CommitAnalyzer.detect_dangerous_changes(changed_files)
        for warning_msg in dangerous_warnings:
            warnings.append(
                Warning(
                    level=WarningLevel.HIGH,
                    message=warning_msg,
                )
            )

        # Check individual file sizes with better token estimation
        for file in changed_files:
            try:
                # Intenta extraer el diff específico del archivo
                if f"diff --git a/{file.path} b/{file.path}" in diff:
                    file_diff = diff.split(f"diff --git a/{file.path} b/{file.path}")[1]
                    file_diff = file_diff.split("diff --git")[0]
                    file_tokens = CommitAnalyzer.estimate_tokens_precise(file_diff)
                else:
                    # Si no encuentra el formato git diff, asume que es un archivo único
                    file_tokens = estimated_tokens

                if file_tokens > config.token_limit * 0.75:  # 75% del límite de tokens
                    is_complex = True
                    warnings.append(
                        Warning(
                            level=WarningLevel.HIGH,
                            message=(
                                f"File {file.path} has extensive changes ({file_tokens:,} tokens). "
                                "Consider committing this file separately."
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
            is_complex=is_complex,
        )

    @staticmethod
    def format_cost_for_humans(cost: float) -> str:
        """Convert cost to human readable format with appropriate unit."""
        if cost >= 1.0:
            return f"€{cost:.2f}"
        elif cost >= 0.01:
            return f"{cost * 100:.2f}¢"
        else:
            return f"{cost * 100:.2f}¢"

    @staticmethod
    def get_cost_context(total_cost: float) -> str:
        """Get contextual message about the cost."""
        if total_cost >= 1.0:  # more than €1
            return "very expensive"
        elif total_cost >= 0.1:  # more than 10 cents
            return "expensive"
        elif total_cost >= 0.05:  # more than 5 cents
            return "moderate"
        elif total_cost >= 0.01:  # more than 1 cent
            return "cheap"
        else:
            return "very cheap"
