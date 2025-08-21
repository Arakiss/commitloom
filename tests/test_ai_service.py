"""Tests for AI service module."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from commitloom.services.ai_service import AIService, CommitSuggestion


@pytest.fixture
def ai_service():
    """Fixture for AIService instance."""
    return AIService(api_key="test_key")


def test_token_usage_from_api_usage():
    """Test token usage calculation from API response."""
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    }
    token_usage = AIService.token_usage_from_api_usage(usage)

    assert token_usage.prompt_tokens == 100
    assert token_usage.completion_tokens == 50
    assert token_usage.total_tokens == 150


def test_generate_prompt_text_files(ai_service, mock_git_file):
    """Test prompt generation for text files."""
    files = [mock_git_file("test.py")]
    diff = "test diff"

    prompt = ai_service.generate_prompt(diff, files)

    assert "test.py" in prompt
    assert "test diff" in prompt


def test_generate_prompt_binary_files(ai_service, mock_git_file):
    """Test prompt generation for binary files."""
    files = [mock_git_file("image.png", size=1024, hash_="abc123")]
    prompt = ai_service.generate_prompt("", files)
    assert "image.png" in prompt
    assert "binary file changes" in prompt


def test_generate_prompt_mixed_files(ai_service, mock_git_file):
    """Prompt should mention both binary and text changes."""
    files = [
        mock_git_file("image.png", size=1024, hash_="abc123"),
        mock_git_file("test.py"),
    ]
    diff = "diff content"
    prompt = ai_service.generate_prompt(diff, files)
    assert "image.png" in prompt
    assert "test.py" in prompt
    assert "Binary files" in prompt


def test_generate_commit_message_success(ai_service, mock_git_file):
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

    ai_service.session.post = MagicMock(return_value=MagicMock(status_code=200, json=lambda: mock_response))

    suggestion, usage = ai_service.generate_commit_message("test diff", [mock_git_file("test.py")])

    assert isinstance(suggestion, CommitSuggestion)
    assert suggestion.title == "✨ feat: add new feature"
    assert usage.total_tokens == 150


def test_generate_commit_message_api_error(ai_service, mock_git_file):
    """Test handling of API errors."""
    ai_service.session.post = MagicMock(
        return_value=MagicMock(status_code=400, json=lambda: {"error": {"message": "API Error"}})
    )

    with pytest.raises(ValueError) as exc_info:
        ai_service.generate_commit_message("test diff", [mock_git_file("test.py")])

    assert "API Error" in str(exc_info.value)


def test_generate_commit_message_invalid_json(ai_service, mock_git_file):
    """Test handling of invalid JSON response."""
    mock_response = {
        "choices": [{"message": {"content": "Invalid JSON"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }

    ai_service.session.post = MagicMock(return_value=MagicMock(status_code=200, json=lambda: mock_response))

    with pytest.raises(ValueError) as exc_info:
        ai_service.generate_commit_message("test diff", [mock_git_file("test.py")])

    assert "Failed to parse AI response" in str(exc_info.value)


def test_generate_commit_message_network_error(ai_service, mock_git_file):
    """Test handling of network errors."""
    ai_service.session.post = MagicMock(side_effect=requests.exceptions.RequestException("Network Error"))

    with pytest.raises(ValueError) as exc_info:
        ai_service.generate_commit_message("test diff", [mock_git_file("test.py")])

    assert "Network Error" in str(exc_info.value)


@patch("time.sleep", return_value=None)
def test_generate_commit_message_retries(mock_sleep, ai_service, mock_git_file):
    """Temporary failures should be retried."""
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "title": "✨ feat: retry success",
                            "body": {
                                "Features": {
                                    "emoji": "✨",
                                    "changes": ["Added new functionality"],
                                }
                            },
                            "summary": "Added new feature",
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    ai_service.session.post = MagicMock(
        side_effect=[
            requests.exceptions.RequestException("temp"),
            MagicMock(status_code=200, json=lambda: mock_response),
        ]
    )
    suggestion, _ = ai_service.generate_commit_message("diff", [mock_git_file("test.py")])
    assert suggestion.title == "✨ feat: retry success"
    assert ai_service.session.post.call_count == 2


def test_format_commit_message():
    """Test commit message formatting."""
    suggestion = CommitSuggestion(
        title="✨ feat: add new feature",
        body={"Changes": {"emoji": "✨", "changes": ["Added new functionality"]}},
        summary="Added new feature for better user experience",
    )

    message = AIService.format_commit_message(suggestion)

    assert "✨ feat: add new feature" in message
    assert "Added new functionality" in message
    assert "Added new feature for better user experience" in message


def test_ai_service_missing_api_key():
    """Test error when API key is missing."""
    with pytest.raises(ValueError) as exc_info:
        AIService(api_key=None)

    assert "API key is required" in str(exc_info.value)


@patch("time.sleep", return_value=None)
def test_generate_commit_message_retries_exhausted(mock_sleep, ai_service, mock_git_file):
    """Should raise error after exhausting all retries."""
    ai_service.session.post = MagicMock(side_effect=requests.exceptions.RequestException("temp"))
    with pytest.raises(ValueError) as exc_info:
        ai_service.generate_commit_message("diff", [mock_git_file("test.py")])
    assert "API Request failed" in str(exc_info.value)
    assert ai_service.session.post.call_count == 3
