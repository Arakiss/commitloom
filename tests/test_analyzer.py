"""Tests for analyzer module."""

import pytest
from commitloom.core.analyzer import (
    CommitAnalyzer,
    CommitAnalysis,
    WarningLevel,
)
from commitloom.core.git import GitFile
from commitloom.config.settings import config


@pytest.fixture
def analyzer():
    """Fixture for CommitAnalyzer instance."""
    return CommitAnalyzer()


def test_estimate_tokens_and_cost(analyzer):
    """Test token and cost estimation."""
    text = "x" * 1000  # 1000 characters
    estimated_tokens, estimated_cost = analyzer.estimate_tokens_and_cost(text)

    # Should be roughly 250 tokens (1000 chars / 4)
    assert estimated_tokens == 250
    # Cost should be calculated correctly
    expected_cost = (estimated_tokens / 1_000_000) * config.model_costs[
        config.default_model
    ].input
    assert estimated_cost == expected_cost


def test_analyze_diff_complexity_small_change(analyzer):
    """Test analysis of a small, simple change."""
    diff = "Small change"
    files = [GitFile(path="test.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert isinstance(analysis, CommitAnalysis)
    assert len(analysis.warnings) == 0
    assert analysis.is_complex is False
    assert analysis.num_files == 1


def test_analyze_diff_complexity_token_limit_exceeded(analyzer):
    """Test analysis when token limit is exceeded."""
    # Create a diff that will exceed token limit
    diff = "x" * (config.token_limit * config.token_estimation_ratio + 1)
    files = [GitFile(path="large.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert len(analysis.warnings) > 0
    assert any(w.level == WarningLevel.HIGH for w in analysis.warnings)
    assert analysis.is_complex is True


def test_analyze_diff_complexity_many_files(analyzer):
    """Test analysis when many files are changed."""
    diff = "Multiple file changes"
    files = [GitFile(path=f"file{i}.py") for i in range(config.max_files_threshold + 1)]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert len(analysis.warnings) > 0
    assert any(
        w.level == WarningLevel.MEDIUM and "files" in w.message
        for w in analysis.warnings
    )


def test_analyze_diff_complexity_expensive_change(analyzer):
    """Test analysis of an expensive change."""
    # Create a diff that will be expensive (>0.10€)
    tokens_for_10_cents = int(
        (0.10 * 1_000_000) / config.model_costs[config.default_model].input
    )
    diff = "diff --git a/expensive.py b/expensive.py\n" + (
        "+" + "x" * tokens_for_10_cents * config.token_estimation_ratio + "\n"
    )
    files = [GitFile(path="expensive.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert len(analysis.warnings) > 0
    assert any(
        w.level == WarningLevel.HIGH and "expensive" in w.message.lower()
        for w in analysis.warnings
    )


def test_analyze_diff_complexity_moderate_cost(analyzer):
    """Test analysis of a moderately expensive change."""
    # Create a diff that will cost between 0.05€ and 0.10€
    tokens_for_7_cents = int(
        (0.07 * 1_000_000) / config.model_costs[config.default_model].input
    )
    diff = "x" * (tokens_for_7_cents * config.token_estimation_ratio)
    files = [GitFile(path="moderate.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert len(analysis.warnings) > 0
    assert any(
        w.level == WarningLevel.MEDIUM and "moderate" in w.message.lower()
        for w in analysis.warnings
    )


def test_analyze_diff_complexity_large_file(analyzer):
    """Test analysis when a single file is very large."""
    # Create a diff that will exceed half the token limit
    diff = "diff --git a/large.py b/large.py\n" + (
        "+"
        + "x" * ((config.token_limit // 2) * config.token_estimation_ratio + 1)
        + "\n"
    )
    files = [GitFile(path="large.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert len(analysis.warnings) > 0
    assert any(
        w.level == WarningLevel.HIGH and "large.py" in w.message
        for w in analysis.warnings
    )


def test_format_cost_for_humans(analyzer):
    """Test cost formatting for different ranges."""
    assert "euros" in analyzer.format_cost_for_humans(1.5)
    assert "cents" in analyzer.format_cost_for_humans(0.05)
    assert "millicents" in analyzer.format_cost_for_humans(0.0005)
    assert "microcents" in analyzer.format_cost_for_humans(0.00005)


def test_get_cost_context(analyzer):
    """Test cost context messages."""
    message, color = analyzer.get_cost_context(0.15)  # More than 10 cents
    assert "Significant" in message
    assert color == "yellow"

    message, color = analyzer.get_cost_context(0.07)  # More than 5 cents
    assert "Moderate" in message
    assert color == "blue"

    message, color = analyzer.get_cost_context(0.02)  # More than 1 cent
    assert "Low" in message
    assert color == "green"

    message, color = analyzer.get_cost_context(0.001)  # Less than 1 cent
    assert "Minimal" in message
    assert color == "green"
