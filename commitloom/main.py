"""Main module for CommitLoom."""

import subprocess
from fnmatch import fnmatch
from typing import Dict, List, Tuple

from .config.settings import config
from .services.ai_service import TokenUsage

def estimate_tokens_and_cost(text: str, model: str = config.default_model) -> Tuple[int, float]:
    """Estimate the number of tokens and cost for a given text."""
    # Estimate tokens (characters / 4 is a rough approximation)
    estimated_tokens = len(text) // config.token_estimation_ratio

    # Calculate cost (assuming all tokens are input tokens for worst-case scenario)
    cost_per_token = config.model_costs[model].input / 1_000_000  # Convert from per million to per token
    estimated_cost = estimated_tokens * cost_per_token

    return estimated_tokens, estimated_cost

def analyze_diff_complexity(diff: str, changed_files: List[str]) -> List[Dict]:
    """Analyzes the complexity of the changes and returns warnings if necessary."""
    warnings = []

    # Estimate tokens and cost
    estimated_tokens, estimated_cost = estimate_tokens_and_cost(diff)

    # Check token limit
    if estimated_tokens > config.token_limit:
        warnings.append({
            "level": "high",
            "message": f"The diff is too large ({estimated_tokens:,} estimated tokens). "
                      f"Exceeds recommended limit of {config.token_limit:,} tokens.",
        })

    # Check cost thresholds
    if estimated_cost >= 0.10:  # more than 10 cents
        warnings.append({
            "level": "high",
            "message": f"This commit could be expensive (€{estimated_cost:.4f}). "
                      f"Consider splitting it into smaller commits.",
        })
    elif estimated_cost >= config.cost_warning_threshold:  # configurable threshold
        warnings.append({
            "level": "medium",
            "message": f"This commit has a moderate cost (€{estimated_cost:.4f}). "
                      f"Consider if it can be optimized.",
        })

    # Check number of files
    if len(changed_files) > config.max_files_threshold:
        warnings.append({
            "level": "medium",
            "message": f"You're modifying {len(changed_files)} files. "
                      f"For atomic commits, consider limiting to {config.max_files_threshold} files per commit.",
        })

    # Analyze individual files
    for file in changed_files:
        try:
            file_diff = subprocess.check_output(["git", "diff", "--staged", "--", file]).decode("utf-8")
            file_tokens, file_cost = estimate_tokens_and_cost(file_diff)

            if file_tokens > config.token_limit // 2:
                warnings.append({
                    "level": "high",
                    "message": f"File {file} has too many changes ({file_tokens:,} estimated tokens). "
                              f"Consider splitting these changes across multiple commits.",
                })
        except subprocess.CalledProcessError:
            warnings.append({
                "level": "medium",
                "message": f"File {file} could not be analyzed. It might be untracked or deleted.",
            })

    return warnings

def should_ignore_file(file_path: str) -> bool:
    """Determine if a file should be ignored based on configured patterns."""
    # Normalize path for consistency between operating systems
    file_path = file_path.replace("\\", "/")
    return any(fnmatch(file_path, pattern) for pattern in config.ignored_patterns)

def get_changed_files() -> List[str]:
    """Get list of staged files only, excluding ignored files."""
    try:
        # Get only staged files
        files = subprocess.check_output(
            ["git", "diff", "--staged", "--name-only", "--"]
        ).decode("utf-8").splitlines()

        # Filter ignored files
        return [f for f in files if not should_ignore_file(f)]
    except subprocess.CalledProcessError:
        return []

def format_file_size(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def get_diff() -> str:
    """Get the staged diff, handling binary files."""
    try:
        # First check if files are binary using --numstat
        numstat = subprocess.check_output(
            ["git", "diff", "--staged", "--numstat"]
        ).decode("utf-8")

        # If we have binary files (shown as "-" in numstat), use a different message
        if "-\t-\t" in numstat:
            files = get_changed_files()
            # Create a custom diff message for binary files
            diff_message = "Binary files changed:\n"
            for file in files:
                try:
                    # Get object hash and mode from git
                    ls_file_output = subprocess.check_output(
                        ["git", "ls-files", "-s", file],
                        stderr=subprocess.DEVNULL
                    ).decode().strip().split()

                    if len(ls_file_output) >= 4:
                        # Format: <mode> <hash> <stage> <file>
                        file_hash = ls_file_output[1]
                        # Get object size using cat-file
                        size_output = subprocess.check_output(
                            ["git", "cat-file", "-s", file_hash],
                            stderr=subprocess.DEVNULL
                        ).decode().strip()
                        file_size = int(size_output)
                        diff_message += f"- {file} ({format_file_size(file_size)})\n"
                    else:
                        diff_message += f"- {file} (size unknown)\n"
                except (subprocess.CalledProcessError, ValueError, IndexError):
                    diff_message += f"- {file} (size unknown)\n"
            return diff_message

        # For text files, proceed with normal diff
        return subprocess.check_output(["git", "diff", "--staged", "--"]).decode("utf-8")
    except subprocess.CalledProcessError:
        return ""
