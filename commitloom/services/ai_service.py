"""AI service for generating commit messages using OpenAI."""

import json
from dataclasses import dataclass
import os
import time

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
    def from_api_usage(cls, usage: dict[str, int], model: str = config.default_model) -> "TokenUsage":
        """Create TokenUsage from API response usage data."""
        prompt_tokens = usage["prompt_tokens"]
        completion_tokens = usage["completion_tokens"]
        total_tokens = usage["total_tokens"]

        # Si el modelo no está en la lista, coste 0 y advertencia
        if model in config.model_costs:
            input_cost = (prompt_tokens / 1_000) * config.model_costs[model].input
            output_cost = (completion_tokens / 1_000) * config.model_costs[model].output
        else:
            input_cost = 0.0
            output_cost = 0.0
            print(f"[WARNING] Cost estimation is not available for model '{model}'.")
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
    """Structured commit message suggestion."""

    title: str
    body: dict[str, dict[str, str | list[str]]]
    summary: str

    def format_body(self) -> str:
        """Format the commit message body."""
        lines = [self.title, ""]
        for category, data in self.body.items():
            emoji = data["emoji"]
            changes = data["changes"]
            lines.append(f"{emoji} {category}:")
            for change in changes:
                lines.append(f"  - {change}")
            lines.append("")
        lines.append(self.summary)
        return "\n".join(lines)


class AIService:
    """Service for interacting with OpenAI API."""

    def __init__(self, api_key: str | None = None, test_mode: bool = False):
        """Initialize AI service.

        Args:
            api_key: OpenAI API key. If not provided, will try to get from environment.
            test_mode: If True, bypass API key requirement for testing.
        """
        if not test_mode and api_key is None:
            raise ValueError("API key is required")
        self.api_key = api_key or config.api_key
        self.test_mode = test_mode
        # Permitir override por variable de entorno
        self.model_name = os.getenv("COMMITLOOM_MODEL", config.default_model)
        self.session = requests.Session()

    @property
    def model(self) -> str:
        """Get the model name.

        Returns:
            The model name from config.
        """
        return self.model_name

    @classmethod
    def token_usage_from_api_usage(cls, usage: dict[str, int]) -> TokenUsage:
        """Create TokenUsage from API response usage data."""
        return TokenUsage.from_api_usage(usage)

    def generate_prompt(self, diff: str, changed_files: list[GitFile]) -> str:
        """Generate the prompt for the AI model."""
        files_summary = ", ".join(f.path for f in changed_files)
        has_binary = any(f.is_binary for f in changed_files)
        binary_files = ", ".join(f.path for f in changed_files if f.is_binary)
        text_files = [f for f in changed_files if not f.is_binary]

        if has_binary and not text_files:
            return (
                "Generate a structured commit message for the following binary file changes.\n"
                "You must respond ONLY with a valid JSON object.\n\n"
                f"Files changed: {binary_files}\n\n"
                "Requirements:\n"
                "1. Title: Maximum 50 characters, starting with an appropriate "
                "gitemoji (📝 for data files), followed by the semantic commit "
                "type and a brief description.\n"
                "2. Body: Create a simple summary of the binary file changes.\n"
                "3. Summary: A brief sentence describing the data updates.\n\n"
                "Return ONLY a JSON object in this format:\n"
                "{\n"
                '  "title": "📝 chore: update binary files",\n'
                '  "body": {\n'
                '    "Data Updates": {\n'
                '      "emoji": "📝",\n'
                '      "changes": [\n'
                '        "Updated binary files with new data",\n'
                f'        "Files affected: {binary_files}"\n'
                "      ]\n"
                "    }\n"
                "  },\n"
                f'  "summary": "Updated binary files: {binary_files}"\n'
                "}"
            )

        prompt = (
            "Generate a structured commit message for the following git diff.\n"
            "You must respond ONLY with a valid JSON object.\n\n"
            f"Files changed: {files_summary}\n\n"
        )
        if binary_files:
            prompt += f"Binary files: {binary_files}\n\n"
        prompt += (
            "```\n"
            f"{diff}\n"
            "```\n\n"
            "Requirements:\n"
            "1. Title: Maximum 50 characters, starting with an appropriate "
            "gitemoji, followed by the semantic commit type and a brief "
            "description.\n"
            "2. Body: Organize changes into categories. Each category should "
            "have an appropriate emoji and bullet points summarizing key "
            "changes.\n"
            "3. Summary: A brief sentence summarizing the overall impact.\n\n"
            "Return ONLY a JSON object in this format:\n"
            "{\n"
            '  "title": "✨ feat: add new feature",\n'
            '  "body": {\n'
            '    "Features": {\n'
            '      "emoji": "✨",\n'
            '      "changes": [\n'
            '        "Added new feature X",\n'
            '        "Implemented functionality Y"\n'
            "      ]\n"
            "    },\n"
            '    "Configuration": {\n'
            '      "emoji": "🔧",\n'
            '      "changes": [\n'
            '        "Updated settings for feature X"\n'
            "      ]\n"
            "    }\n"
            "  },\n"
            '  "summary": "Added new feature X with configuration updates"\n'
            "}"
        )
        return prompt

    def generate_commit_message(
        self, diff: str, changed_files: list[GitFile]
    ) -> tuple[CommitSuggestion, TokenUsage]:
        """Generate a commit message using the OpenAI API."""
        if self.test_mode:
            # Return mock data for testing
            return (
                CommitSuggestion(
                    title="✨ feat: test commit",
                    body={"Features": {"emoji": "✨", "changes": ["Test change"]}},
                    summary="Test summary",
                ),
                TokenUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    input_cost=0.01,
                    output_cost=0.02,
                    total_cost=0.03,
                ),
            )

        if not self.api_key:
            raise ValueError("API key is required")

        prompt = self.generate_prompt(diff, changed_files)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": 1000,
            "temperature": 0.7,
        }

        last_exception: requests.exceptions.RequestException | None = None
        response: requests.Response | None = None
        for attempt in range(3):
            try:
                response = self.session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30,
                )
                if response.status_code >= 500:
                    raise requests.exceptions.RequestException(
                        f"Server error: {response.status_code}", response=response
                    )
                break
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt == 2:
                    break
                time.sleep(2**attempt)

        if last_exception and (response is None or response.status_code >= 500):
            if (
                hasattr(last_exception, "response")
                and last_exception.response is not None
                and hasattr(last_exception.response, "text")
            ):
                error_message = last_exception.response.text
            else:
                error_message = str(last_exception)
            raise ValueError(f"API Request failed: {error_message}") from last_exception

        if response is None:
            raise ValueError("No response received from API")
            
        if response.status_code == 400:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            raise ValueError(f"API Error: {error_message}")

        response.raise_for_status()
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]
        usage = response_data["usage"]

        try:
            commit_data = json.loads(content)
            return CommitSuggestion(**commit_data), TokenUsage.from_api_usage(usage)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response: {str(e)}") from e

    @staticmethod
    def format_commit_message(commit_data: CommitSuggestion) -> str:
        """Format a commit message from the suggestion data."""
        return commit_data.format_body()
