"""Tests for AI service module."""

import pytest
from unittest.mock import patch, MagicMock
import json
import requests

from commitloom.services.ai_service import (
    AIService,
    TokenUsage,
    CommitSuggestion,
)
from commitloom.core.git import GitFile
from commitloom.config.settings import config


@pytest.fixture
def ai_service():
    """Fixture for AIService instance with mocked API key."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        return AIService()


def test_token_usage_from_api_usage():
    """Test TokenUsage creation from API response."""
    usage_data = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    }

    usage = TokenUsage.from_api_usage(usage_data)

    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150
    assert (
        usage.input_cost
        == (100 / 1_000_000) * config.model_costs[config.default_model].input
    )
    assert (
        usage.output_cost
        == (50 / 1_000_000) * config.model_costs[config.default_model].output
    )
    assert usage.total_cost == usage.input_cost + usage.output_cost


def test_generate_prompt_text_files(ai_service):
    """Test prompt generation for text files."""
    files = [GitFile(path="test.py")]
    diff = "diff --git a/test.py b/test.py\n+new line"

    prompt = ai_service._generate_prompt(diff, files)

    assert "test.py" in prompt
    assert diff in prompt
    assert "Requirements:" in prompt
    assert "Title:" in prompt
    assert "Body:" in prompt
    assert "Summary:" in prompt


def test_generate_prompt_binary_files(ai_service):
    """Test prompt generation for binary files."""
    files = [GitFile(path="image.png", size=1024)]
    diff = "Binary files changed:\n- image.png (1.00 KB)"

    prompt = ai_service._generate_prompt(diff, files)

    assert "image.png" in prompt
    assert "Binary files changed" in prompt
    assert "📝" in prompt  # Should include binary file emoji


@patch("requests.post")
def test_generate_commit_message_success(mock_post, ai_service):
    """Test successful commit message generation."""
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "title": "✨ feat: add new feature",
                            "body": {
                                "Features": {
                                    "emoji": "✨",
                                    "changes": ["Added new functionality"],
                                }
                            },
                            "summary": "Added new feature for better user experience",
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }

    mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_response)

    suggestion, usage = ai_service.generate_commit_message(
        "test diff", [GitFile(path="test.py")]
    )

    assert isinstance(suggestion, CommitSuggestion)
    assert suggestion.title == "✨ feat: add new feature"
    assert "Features" in suggestion.body
    assert isinstance(usage, TokenUsage)
    assert usage.prompt_tokens == 100


@patch("requests.post")
def test_generate_commit_message_api_error(mock_post, ai_service):
    """Test handling of API errors."""
    mock_post.return_value = MagicMock(
        status_code=400, json=lambda: {"error": {"message": "API Error"}}
    )

    with pytest.raises(ValueError) as exc_info:
        ai_service.generate_commit_message("test diff", [GitFile(path="test.py")])

    assert "API Error" in str(exc_info.value)


@patch("requests.post")
def test_generate_commit_message_invalid_json(mock_post, ai_service):
    """Test handling of invalid JSON response."""
    mock_response = {
        "choices": [{"message": {"content": "Invalid JSON"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }

    mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_response)

    with pytest.raises(ValueError) as exc_info:
        ai_service.generate_commit_message("test diff", [GitFile(path="test.py")])

    assert "Failed to parse API response as JSON" in str(exc_info.value)


@patch("requests.post")
def test_generate_commit_message_network_error(mock_post, ai_service):
    """Test handling of network errors."""
    mock_post.side_effect = requests.exceptions.RequestException("Network Error")

    with pytest.raises(ValueError) as exc_info:
        ai_service.generate_commit_message("test diff", [GitFile(path="test.py")])

    assert "API Request failed" in str(exc_info.value)


def test_format_commit_message(ai_service):
    """Test commit message formatting."""
    commit_data = CommitSuggestion(
        title="✨ feat: new feature",
        body={
            "Features": {"emoji": "✨", "changes": ["Change 1", "Change 2"]},
            "Fixes": {"emoji": "🐛", "changes": ["Fix 1"]},
        },
        summary="Added new features and fixed bugs",
    )

    formatted = ai_service.format_commit_message(commit_data)

    assert "✨ Features:" in formatted
    assert "🐛 Fixes:" in formatted
    assert "Change 1" in formatted
    assert "Change 2" in formatted
    assert "Fix 1" in formatted
    assert formatted.endswith("Added new features and fixed bugs\n")


def test_ai_service_missing_api_key():
    """Test AIService initialization with missing API key."""
    with patch.dict("os.environ", clear=True):
        with pytest.raises(ValueError) as exc_info:
            config.from_env()

    assert "OPENAI_API_KEY environment variable is not set" in str(exc_info.value)
