"""Metrics and statistics collection for CommitLoom."""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CommitMetrics:
    """Metrics for a single commit generation."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    files_changed: int = 0
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_in_eur: float = 0.0
    time_taken_seconds: float = 0.0
    model_used: str = ""
    repository: str | None = None
    batch_processing: bool = False
    batch_number: int | None = None
    batch_total: int | None = None


@dataclass
class UsageStatistics:
    """High-level usage statistics for the application."""

    total_commits: int = 0
    total_tokens: int = 0
    total_cost_in_eur: float = 0.0
    total_files_processed: int = 0
    total_time_saved_seconds: float = 0.0
    first_used_at: str | None = None
    last_used_at: str | None = None
    most_active_repository: str | None = None
    repositories: dict[str, int] = field(default_factory=dict)
    model_usage: dict[str, int] = field(default_factory=dict)
    batch_commits: int = 0
    single_commits: int = 0


class MetricsManager:
    """Manages collection and storage of metrics for CommitLoom."""

    def __init__(self):
        """Initialize the metrics manager."""
        self._base_dir = self._get_metrics_directory()
        self._metrics_file = self._base_dir / "commit_metrics.json"
        self._stats_file = self._base_dir / "usage_statistics.json"
        self._ensure_directories()
        self._current_commit_start_time: float | None = None
        self._current_metrics: CommitMetrics | None = None
        self._statistics: UsageStatistics = self._load_statistics()

    def _get_metrics_directory(self) -> Path:
        """Get the metrics directory path."""
        # Use the XDG_DATA_HOME environment variable if available, otherwise use ~/.local/share
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base_dir = Path(xdg_data_home)
        else:
            base_dir = Path.home() / ".local" / "share"

        return base_dir / "commitloom" / "metrics"

    def _ensure_directories(self) -> None:
        """Ensure metrics directories exist."""
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _load_statistics(self) -> UsageStatistics:
        """Load usage statistics from file."""
        if not self._stats_file.exists():
            return UsageStatistics()

        try:
            with open(self._stats_file) as f:
                data = json.load(f)
                # Ensure valid JSON structure
                if not isinstance(data, dict):
                    logger.warning("Invalid statistics file format, creating new file")
                    return UsageStatistics()
                stats = UsageStatistics(**data)
                return stats
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to load statistics, creating new file: {str(e)}")
            return UsageStatistics()

    def _save_statistics(self) -> None:
        """Save usage statistics to file."""
        try:
            # Ensure valid data structure before saving
            stats_dict = asdict(self._statistics)

            # Fix any potential problematic values
            if 'repositories' in stats_dict and not isinstance(stats_dict['repositories'], dict):
                stats_dict['repositories'] = {}

            if 'model_usage' in stats_dict and not isinstance(stats_dict['model_usage'], dict):
                stats_dict['model_usage'] = {}

            with open(self._stats_file, "w") as f:
                json.dump(stats_dict, f, indent=2)

        except (OSError, TypeError) as e:
            logger.warning(f"Failed to save statistics: {str(e)}")

    def _save_metrics(self, metrics: CommitMetrics) -> None:
        """Save commit metrics to file."""
        metrics_list: list[dict[str, Any]] = []

        # Load existing metrics if file exists
        if self._metrics_file.exists():
            try:
                with open(self._metrics_file) as f:
                    metrics_list = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Failed to load metrics, creating new file: {str(e)}")
                metrics_list = []

        # Add new metrics and save
        metrics_list.append(asdict(metrics))

        # Limit to last 1000 commits to keep file size reasonable
        metrics_list = metrics_list[-1000:]

        try:
            with open(self._metrics_file, "w") as f:
                json.dump(metrics_list, f, indent=2)
        except (OSError, TypeError) as e:
            logger.warning(f"Failed to save metrics: {str(e)}")

    def start_commit_tracking(self, repository: str | None = None) -> None:
        """Start tracking a commit generation.

        Args:
            repository: Optional repository name/path
        """
        self._current_commit_start_time = time.time()
        self._current_metrics = CommitMetrics()
        if repository:
            self._current_metrics.repository = repository

    def finish_commit_tracking(
        self,
        files_changed: int,
        tokens_used: int,
        prompt_tokens: int,
        completion_tokens: int,
        cost_in_eur: float,
        model_used: str,
        batch_processing: bool = False,
        batch_number: int | None = None,
        batch_total: int | None = None,
    ) -> None:
        """Finish tracking a commit and record metrics.

        Args:
            files_changed: Number of files changed in this commit
            tokens_used: Total number of tokens used for this commit
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            cost_in_eur: Cost in EUR for this commit
            model_used: Name of the model used
            batch_processing: Whether this commit was part of batch processing
            batch_number: Batch number (if batch processing)
            batch_total: Total number of batches (if batch processing)
        """
        if not self._current_metrics or not self._current_commit_start_time:
            logger.warning("finish_commit_tracking called without starting tracking first")
            return

        # Calculate time taken
        time_taken = time.time() - self._current_commit_start_time

        # Update metrics
        self._current_metrics.files_changed = files_changed
        self._current_metrics.tokens_used = tokens_used
        self._current_metrics.prompt_tokens = prompt_tokens
        self._current_metrics.completion_tokens = completion_tokens
        self._current_metrics.cost_in_eur = cost_in_eur
        self._current_metrics.time_taken_seconds = time_taken
        self._current_metrics.model_used = model_used
        self._current_metrics.batch_processing = batch_processing
        self._current_metrics.batch_number = batch_number
        self._current_metrics.batch_total = batch_total

        # Save metrics
        self._save_metrics(self._current_metrics)

        # Update statistics
        self._update_statistics(self._current_metrics)

        # Reset current metrics
        self._current_metrics = None
        self._current_commit_start_time = None

    def _update_statistics(self, metrics: CommitMetrics) -> None:
        """Update overall statistics with new metrics.

        Args:
            metrics: Metrics from the latest commit
        """
        stats = self._statistics

        # Update basic counters
        stats.total_commits += 1
        stats.total_tokens += metrics.tokens_used
        stats.total_cost_in_eur += metrics.cost_in_eur
        stats.total_files_processed += metrics.files_changed

        # Update time saved (assuming average manual commit takes 3 minutes)
        estimated_manual_time = 180.0  # 3 minutes in seconds
        time_saved = estimated_manual_time - metrics.time_taken_seconds
        if time_saved > 0:
            stats.total_time_saved_seconds += time_saved

        # Update timestamps
        current_time = metrics.timestamp
        if not stats.first_used_at:
            stats.first_used_at = current_time
        stats.last_used_at = current_time

        # Update repository statistics
        if metrics.repository:
            repo = metrics.repository
            stats.repositories[repo] = stats.repositories.get(repo, 0) + 1

            # Find most active repository
            most_active = max(stats.repositories.items(), key=lambda x: x[1], default=(None, 0))
            stats.most_active_repository = most_active[0]

        # Update model usage
        model = metrics.model_used
        stats.model_usage[model] = stats.model_usage.get(model, 0) + 1

        # Update batch statistics
        if metrics.batch_processing:
            stats.batch_commits += 1
        else:
            stats.single_commits += 1

        # Save updated statistics
        self._save_statistics()

    def get_statistics(self) -> dict[str, Any]:
        """Get usage statistics with additional computed metrics.

        Returns:
            Dictionary with all statistics
        """
        stats = asdict(self._statistics)

        # Add computed statistics
        if stats["total_time_saved_seconds"] > 0:
            saved_time = timedelta(seconds=stats["total_time_saved_seconds"])
            stats["time_saved_formatted"] = self._format_timedelta(saved_time)

        if stats["first_used_at"] and stats["last_used_at"]:
            try:
                first = datetime.fromisoformat(stats["first_used_at"])
                last = datetime.fromisoformat(stats["last_used_at"])
                days_active = (last - first).days + 1
                stats["days_active"] = days_active

                if days_active > 0:
                    stats["avg_commits_per_day"] = stats["total_commits"] / days_active
                    stats["avg_cost_per_day"] = stats["total_cost_in_eur"] / days_active
            except (ValueError, TypeError):
                pass

        return stats

    def get_recent_metrics(self, days: int = 30) -> list[dict[str, Any]]:
        """Get metrics from recent commits.

        Args:
            days: Number of days to look back

        Returns:
            List of commit metrics from the specified period
        """
        metrics_list: list[dict[str, Any]] = []

        if not self._metrics_file.exists():
            return metrics_list

        try:
            with open(self._metrics_file) as f:
                all_metrics = json.load(f)

            # Filter metrics by date
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()

            metrics_list = [m for m in all_metrics if m.get("timestamp", "") >= cutoff_str]

            return metrics_list
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to load metrics: {str(e)}")
            return []

    def get_summary_by_day(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily summary of metrics.

        Args:
            days: Number of days to look back

        Returns:
            List of daily summaries with tokens, cost, files, and commits
        """
        recent_metrics = self.get_recent_metrics(days)
        daily_summaries = {}

        for metric in recent_metrics:
            try:
                timestamp = metric.get("timestamp", "")
                date_part = timestamp.split("T")[0]

                if date_part not in daily_summaries:
                    daily_summaries[date_part] = {
                        "date": date_part,
                        "commits": 0,
                        "tokens": 0,
                        "cost": 0.0,
                        "files": 0,
                    }

                daily_summaries[date_part]["commits"] += 1
                daily_summaries[date_part]["tokens"] += metric.get("tokens_used", 0)
                daily_summaries[date_part]["cost"] += metric.get("cost_in_eur", 0.0)
                daily_summaries[date_part]["files"] += metric.get("files_changed", 0)
            except (KeyError, ValueError, IndexError):
                continue

        # Convert to list and sort by date
        result = list(daily_summaries.values())
        result.sort(key=lambda x: x["date"])

        return result

    def get_model_usage_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics about model usage.

        Returns:
            Dictionary with model usage statistics
        """
        model_stats: dict[str, dict[str, Any]] = {}

        if not self._metrics_file.exists():
            return model_stats

        try:
            with open(self._metrics_file) as f:
                all_metrics = json.load(f)

            for metric in all_metrics:
                model_name = metric.get("model_used", "unknown")

                if model_name not in model_stats:
                    model_stats[model_name] = {
                        "commits": 0,
                        "tokens": 0,
                        "cost": 0.0,
                        "avg_tokens_per_commit": 0,
                    }

                model_stats[model_name]["commits"] += 1
                model_stats[model_name]["tokens"] += metric.get("tokens_used", 0)
                model_stats[model_name]["cost"] += metric.get("cost_in_eur", 0.0)

            # Calculate averages
            for _, stats in model_stats.items():
                if stats["commits"] > 0:
                    stats["avg_tokens_per_commit"] = stats["tokens"] / stats["commits"]

            return model_stats
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to load metrics for model usage stats: {str(e)}")
            return {}

    def get_repository_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics about repository usage.

        Returns:
            Dictionary with repository usage statistics
        """
        repo_stats: dict[str, dict[str, Any]] = {}

        if not self._metrics_file.exists():
            return repo_stats

        try:
            with open(self._metrics_file) as f:
                all_metrics = json.load(f)

            for metric in all_metrics:
                repo = metric.get("repository", "unknown")
                if not repo:
                    repo = "unknown"

                if repo not in repo_stats:
                    repo_stats[repo] = {
                        "commits": 0,
                        "tokens": 0,
                        "cost": 0.0,
                        "files": 0,
                    }

                repo_stats[repo]["commits"] += 1
                repo_stats[repo]["tokens"] += metric.get("tokens_used", 0)
                repo_stats[repo]["cost"] += metric.get("cost_in_eur", 0.0)
                repo_stats[repo]["files"] += metric.get("files_changed", 0)

            return repo_stats
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to load metrics for repository stats: {str(e)}")
            return {}

    @staticmethod
    def _format_timedelta(td: timedelta) -> str:
        """Format a timedelta into a readable string.

        Args:
            td: Timedelta object to format

        Returns:
            Formatted string representing the timedelta
        """
        total_seconds = int(td.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 and not parts:  # Only show seconds if no larger units
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        return ", ".join(parts)


# Singleton instance
metrics_manager = MetricsManager()
