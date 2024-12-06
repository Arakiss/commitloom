"""AI service for generating commit messages using OpenAI."""

import json
from dataclasses import dataclass

import requests

from ..config.settings import config
from ..core.git import GitFile


@dataclass
class TokenUsage:
    """Token usage information from API response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float

    @classmethod
    def from_api_usage(
        cls, usage: dict[str, int], model: str = config.default_model
    ) -> "TokenUsage":
        """Create TokenUsage from API response usage data."""
        prompt_tokens = usage["prompt_tokens"]
        completion_tokens = usage["completion_tokens"]
        total_tokens = usage["total_tokens"]

        # Calculate costs
        input_cost = (prompt_tokens / 1_000_000) * config.model_costs[model].input
        output_cost = (completion_tokens / 1_000_000) * config.model_costs[model].output
        total_cost = input_cost + output_cost

        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
        )


@dataclass
class CommitSuggestion:
    """Represents a commit message suggestion."""

    title: str
    body: dict[str, dict[str, str | list[str]]]
    summary: str

    def format_body(self) -> str:
        """Format the commit body for git commit message."""
        formatted = []
        for category, content in self.body.items():
            formatted.append(f"\n{category}:")
            for change in content["changes"]:
                formatted.append(f"- {change}")
        formatted.append(f"\n{self.summary}")
        return "\n".join(formatted)


class AIService:
    """Service for interacting with OpenAI API."""

    def __init__(self):
        """Initialize the AI service."""
        # API key is now handled by the config
        pass

    def format_commit_message(self, commit_data: CommitSuggestion) -> str:
        """Format a commit message from the suggestion data."""
        formatted_message = commit_data.title + "\n\n"

        for category, content in commit_data.body.items():
            formatted_message += f"{category}:\n"
            for change in content["changes"]:
                formatted_message += f"- {change}\n"
            formatted_message += "\n"

        formatted_message += f"{commit_data.summary}\n"
        return formatted_message

    def _generate_prompt(self, diff: str, changed_files: list[GitFile]) -> str:
        """Generate the prompt for the AI model."""
        files_summary = ", ".join(f.path for f in changed_files)

        # Check if we're dealing with binary files
        if diff.startswith("Binary files changed:"):
            return (
                "Generate a structured commit message in JSON format for the following binary file changes.\n"
                "The commit MUST follow conventional commits format with a gitemoji prefix.\n\n"
                f"Files changed: {files_summary}\n\n"
                f"{diff}\n\n"
                "Requirements:\n"
                "1. Title: Maximum 50 characters, MUST start with an appropriate "
                "gitemoji (e.g. 📝, ✨, 🐛), followed by the semantic commit "
                "type (feat, fix, etc) and a brief description.\n"
                "2. Body: Create a simple summary of the binary file changes.\n"
                "3. Summary: A brief sentence describing the data updates.\n\n"
                "Return the response in the following JSON format:\n"
                "{\n"
                '  "title": "✨ feat: example title",\n'
                '  "body": {\n'
                '    "Changes": {\n'
                '      "changes": [\n'
                '        "✨ Added new feature X",\n'
                '        "🔧 Updated configuration Y"\n'
                "      ]\n"
                "    }\n"
                "  },\n"
                '  "summary": "This change implements feature X with updated configuration."\n'
                "}"
            )

        return (
            "Generate a structured commit message in JSON format for the following git diff.\n"
            "The commit MUST follow conventional commits format with a gitemoji prefix.\n\n"
            f"Files changed: {files_summary}\n\n"
            "```\n"
            f"{diff}\n"
            "```\n\n"
            "Requirements:\n"
            "1. Title: Maximum 50 characters, MUST start with an appropriate "
            "gitemoji (e.g. 📝, ✨, 🐛), followed by the semantic commit "
            "type (feat, fix, etc) and a brief description.\n"
            "2. Body: Organize changes into categories. Each category should "
            "have an appropriate emoji and bullet points summarizing key "
            "changes.\n"
            "3. Summary: A brief sentence summarizing the overall impact.\n\n"
            "Return the response in the following JSON format:\n"
            "{\n"
            '  "title": "✨ feat: example title",\n'
            '  "body": {\n'
            '    "Features": {\n'
            '      "changes": [\n'
            '        "✨ Added new feature X",\n'
            '        "🔧 Updated configuration Y"\n'
            "      ]\n"
            "    },\n"
            '    "Fixes": {\n'
            '      "changes": [\n'
            '        "🐛 Fixed issue Z"\n'
            "      ]\n"
            "    }\n"
            "  },\n"
            '  "summary": "This change implements feature X with configuration updates and bug fixes."\n'
            "}"
        )

    def generate_commit_message(
        self, diff: str, changed_files: list[GitFile]
    ) -> tuple[CommitSuggestion, TokenUsage]:
        """Generate a commit message using the OpenAI API."""
        prompt = self._generate_prompt(diff, changed_files)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        }

        data = {
            "model": config.default_model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": 1000,
            "temperature": 0.7,
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30,
            )

            if response.status_code == 400:
                error_data = response.json()
                error_message = error_data.get("error", {}).get(
                    "message", "Unknown error"
                )
                raise ValueError(f"API Error: {error_message}")

            response.raise_for_status()
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
            usage = response_data["usage"]

            try:
                commit_data = json.loads(content)
                return CommitSuggestion(**commit_data), TokenUsage.from_api_usage(usage)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse API response as JSON: {str(e)}") from e

        except requests.exceptions.RequestException as e:
            if hasattr(e.response, "text"):
                error_message = e.response.text
            else:
                error_message = str(e)
            raise ValueError(f"API Request failed: {error_message}") from e
