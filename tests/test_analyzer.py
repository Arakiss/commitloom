"""Tests for commit analyzer module."""

import pytest

from commitloom.config.settings import config
from commitloom.core.analyzer import CommitAnalysis, CommitAnalyzer


@pytest.fixture
def analyzer():
    """Fixture for CommitAnalyzer instance."""
    return CommitAnalyzer()


def test_estimate_tokens_and_cost(analyzer):
    """Test token and cost estimation."""
    diff = "Small change"
    tokens, cost = analyzer.estimate_tokens_and_cost(diff)

    assert tokens > 0
    assert cost > 0


def test_analyze_diff_complexity_small_change(analyzer, mock_git_file):
    """Test analysis of a small, simple change."""
    diff = "Small change"
    files = [mock_git_file("test.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert isinstance(analysis, CommitAnalysis)
    assert analysis.estimated_tokens > 0
    assert analysis.estimated_cost > 0
    assert analysis.num_files == 1
    assert not analysis.is_complex
    assert not analysis.warnings


def test_analyze_diff_complexity_token_limit_exceeded(analyzer, mock_git_file):
    """Test analysis when token limit is exceeded."""
    # Create a diff that will exceed token limit
    diff = "x" * (config.token_limit * config.token_estimation_ratio + 1)
    files = [mock_git_file("large.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.is_complex
    assert any("token limit" in w for w in analysis.warnings)


def test_analyze_diff_complexity_many_files(analyzer, mock_git_file):
    """Test analysis when many files are changed."""
    diff = "Multiple file changes"
    files = [mock_git_file(f"file{i}.py") for i in range(config.max_files_threshold + 1)]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.is_complex
    assert any("files changed" in w for w in analysis.warnings)


def test_analyze_diff_complexity_expensive_change(analyzer, mock_git_file):
    """Test analysis of an expensive change."""
    # Create a diff that will be expensive (>0.10€)
    tokens_for_10_cents = int(
        (0.10 * 1_000_000) / config.model_costs[config.default_model].input
    )
    diff = "diff --git a/expensive.py b/expensive.py\n" + (
        "+" + "x" * tokens_for_10_cents * config.token_estimation_ratio + "\n"
    )
    files = [mock_git_file("expensive.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.is_complex
    assert any("expensive" in w for w in analysis.warnings)


def test_analyze_diff_complexity_moderate_cost(analyzer, mock_git_file):
    """Test analysis of a moderately expensive change."""
    # Create a diff that will cost between 0.05€ and 0.10€
    tokens_for_7_cents = int(
        (0.07 * 1_000_000) / config.model_costs[config.default_model].input
    )
    diff = "x" * (tokens_for_7_cents * config.token_estimation_ratio)
    files = [mock_git_file("moderate.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert not analysis.is_complex
    assert any("cost" in w for w in analysis.warnings)


def test_analyze_diff_complexity_large_file(analyzer, mock_git_file):
    """Test analysis when a single file is very large."""
    # Create a diff that will exceed half the token limit
    diff = "diff --git a/large.py b/large.py\n" + (
        "+"
        + "x" * ((config.token_limit // 2) * config.token_estimation_ratio + 1)
        + "\n"
    )
    files = [mock_git_file("large.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.is_complex
    assert any("large" in w for w in analysis.warnings)


def test_format_cost_for_humans():
    """Test cost formatting."""
    assert CommitAnalyzer.format_cost_for_humans(0.001) == "0.10¢"
    assert CommitAnalyzer.format_cost_for_humans(0.01) == "1.00¢"
    assert CommitAnalyzer.format_cost_for_humans(0.1) == "10.00¢"
    assert CommitAnalyzer.format_cost_for_humans(1.0) == "€1.00"


def test_get_cost_context():
    """Test cost context descriptions."""
    assert "very cheap" in CommitAnalyzer.get_cost_context(0.001)
    assert "cheap" in CommitAnalyzer.get_cost_context(0.01)
    assert "moderate" in CommitAnalyzer.get_cost_context(0.05)
    assert "expensive" in CommitAnalyzer.get_cost_context(0.1)
    assert "very expensive" in CommitAnalyzer.get_cost_context(1.0)
