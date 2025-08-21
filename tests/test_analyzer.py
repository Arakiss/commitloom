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
    tokens_for_10_cents = int((0.10 * 1_000_000) / config.model_costs[config.default_model].input)
    diff = "diff --git a/expensive.py b/expensive.py\n" + (
        "+" + "x" * tokens_for_10_cents * config.token_estimation_ratio + "\n"
    )
    files = [mock_git_file("expensive.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.is_complex
    assert any("expensive" in w for w in analysis.warnings)


def test_analyze_diff_complexity_large_file(analyzer, mock_git_file):
    """Test analysis when a single file is very large."""
    tokens = config.token_limit * 0.8  # 80% del límite
    diff = "x" * int(tokens * config.token_estimation_ratio)
    files = [mock_git_file("large.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.is_complex
    assert any("large" in str(w) for w in analysis.warnings)


def test_analyze_diff_complexity_binary_file(analyzer, mock_git_file):
    """Test analysis with binary files."""
    diff = "Binary files a/image.png and b/image.png differ"
    files = [mock_git_file("image.png", size=1024, hash_="abc123")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert not analysis.is_complex
    assert analysis.estimated_tokens > 0


def test_analyze_diff_complexity_empty_diff(analyzer, mock_git_file):
    """Test analysis with empty diff."""
    diff = ""
    files = [mock_git_file("empty.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert not analysis.is_complex
    assert analysis.estimated_tokens == 0


def test_analyze_diff_complexity_multiple_conditions(analyzer, mock_git_file):
    """Test analysis with multiple complexity conditions."""
    # Create a diff that triggers multiple conditions:
    # 1. Many files
    # 2. Moderate cost
    # 3. One large file
    files = [mock_git_file(f"file{i}.py") for i in range(config.max_files_threshold + 1)]
    tokens = config.token_limit * 0.8
    diff = "x" * int(tokens * config.token_estimation_ratio)

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.is_complex
    assert len(analysis.warnings) >= 2
    assert any("files changed" in str(w) for w in analysis.warnings)
    assert any("large" in str(w) for w in analysis.warnings)


def test_analyze_diff_complexity_edge_cases(analyzer, mock_git_file):
    """Test analysis with edge cases."""
    # Test con un archivo justo en el límite
    tokens = config.token_limit
    diff = "x" * (tokens * config.token_estimation_ratio)
    files = [mock_git_file("edge.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.is_complex
    assert any("token limit" in str(w) for w in analysis.warnings)


def test_analyze_diff_complexity_special_chars(analyzer, mock_git_file):
    """Test analysis with special characters."""
    diff = "🚀" * 100  # Emojis y caracteres especiales
    files = [mock_git_file("special.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert analysis.estimated_tokens > 0
    assert not analysis.is_complex


def test_analyze_diff_complexity_git_format(analyzer, mock_git_file):
    """Test analysis with different git diff formats."""
    diff = (
        "diff --git a/file.py b/file.py\n"
        "index abc123..def456 100644\n"
        "--- a/file.py\n"
        "+++ b/file.py\n"
        "@@ -1,3 +1,4 @@\n"
        " unchanged line\n"
        "-removed line\n"
        "+added line\n"
        "+another added line\n"
        " unchanged line\n"
    )
    files = [mock_git_file("file.py")]

    analysis = analyzer.analyze_diff_complexity(diff, files)

    assert not analysis.is_complex
    assert analysis.estimated_tokens > 0


def test_format_cost_for_humans():
    """Test cost formatting."""
    assert CommitAnalyzer.format_cost_for_humans(0.0001) == "0.01¢"
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


def test_estimate_tokens_and_cost_unknown_model(capsys):
    """Fallback to zero cost for unknown model."""
    tokens, cost = CommitAnalyzer.estimate_tokens_and_cost("test", model="unknown")
    captured = capsys.readouterr()
    assert "Cost estimation is not available" in captured.out
    assert tokens >= 0
    assert cost == 0


def test_analyze_diff_complexity_moderate_cost(analyzer, mock_git_file):
    """Should warn about moderate cost without marking complex."""
    tokens_for_six_cents = int((0.06 * 1_000_000) / config.model_costs[config.default_model].input)
    diff = "diff --git a/mod.py b/mod.py\n" + (
        "+" + "x" * tokens_for_six_cents * config.token_estimation_ratio + "\n"
    )
    files = [mock_git_file("mod.py")]
    analysis = analyzer.analyze_diff_complexity(diff, files)
    assert any("moderate" in str(w) for w in analysis.warnings)
    assert analysis.is_complex
