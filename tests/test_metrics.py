import json
from datetime import timedelta

from commitloom.services.metrics import metrics_manager, CommitMetrics


def test_save_metrics_with_invalid_file(tmp_path, monkeypatch):
    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text("{}")  # invalid structure (dict instead of list)
    monkeypatch.setattr(metrics_manager, "_metrics_file", metrics_file)

    metric = CommitMetrics(files_changed=1)
    # Should not raise even though existing file is invalid
    metrics_manager._save_metrics(metric)

    data = json.loads(metrics_file.read_text())
    assert isinstance(data, list)
    assert data[0]["files_changed"] == 1


def test_format_timedelta_outputs():
    td = timedelta(days=1, hours=2, minutes=30)
    result = metrics_manager._format_timedelta(td)
    assert "1 day" in result
    assert "2 hours" in result
    assert "30 minutes" in result


def test_get_statistics(tmp_path, monkeypatch):
    metrics_file = tmp_path / "metrics.json"
    stats_file = tmp_path / "stats.json"
    monkeypatch.setattr(metrics_manager, "_metrics_file", metrics_file)
    monkeypatch.setattr(metrics_manager, "_stats_file", stats_file)

    metrics_manager.start_commit_tracking("repo")
    metrics_manager.finish_commit_tracking(
        files_changed=1,
        tokens_used=10,
        prompt_tokens=5,
        completion_tokens=5,
        cost_in_eur=0.01,
        model_used="gpt-test",
    )

    stats = metrics_manager.get_statistics()
    assert stats["total_commits"] >= 1

