"""AI service for generating commit messages using OpenAI."""

import json
import requests
from dataclasses import dataclass
from typing import Dict, List, Tuple

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
        cls, usage: Dict[str, int], model: str = config.default_model
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
    """Generated commit message suggestion."""

    title: str
    body: Dict[str, Dict[str, List[str]]]
    summary: str


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

    def _generate_prompt(self, diff: str, changed_files: List[GitFile]) -> str:
        """Generate a prompt for commit message generation."""
        files_summary = ", ".join(f.path for f in changed_files[:3])
        if len(changed_files) > 3:
            files_summary += f" and {len(changed_files) - 3} more"

        # Check if we're dealing with binary files
        if diff.startswith("Binary files changed:"):
            return f"""Generate a structured commit message for the following binary file changes:

Files changed: {files_summary}

{diff}

Requirements:
1. Title: Maximum 50 characters, starting with an appropriate gitemoji (📝 for data files), followed by the semantic commit type and a brief description.
2. Body: Create a simple summary of the binary file changes.
3. Summary: A brief sentence describing the data updates.

You must respond ONLY with a valid JSON object in the following format:
{{
    "title": "Your commit message title here",
    "body": {{
        "📝 Data Updates": {{
            "emoji": "📝",
            "changes": [
                "Updated binary files with new data",
                "Files affected: {files_summary}"
            ]
        }}
    }},
    "summary": "A brief summary of the data updates."
}}"""

        return f"""Generate a structured commit message for the following git diff, following the semantic commit and gitemoji conventions:

Files changed: {files_summary}

```
{diff}
```

Requirements:
1. Title: Maximum 50 characters, starting with an appropriate gitemoji, followed by the semantic commit type and a brief description.
2. Body: Organize changes into categories. Each category should have an appropriate emoji and 2-3 bullet points summarizing key changes.
3. Summary: A brief sentence summarizing the overall impact of the changes.

You must respond ONLY with a valid JSON object in the following format:
{{
    "title": "Your commit message title here",
    "body": {{
        "🔧 Category1": {{
            "emoji": "🔧",
            "changes": [
                "First change in category 1",
                "Second change in category 1"
            ]
        }},
        "✨ Category2": {{
            "emoji": "✨",
            "changes": [
                "First change in category 2",
                "Second change in category 2"
            ]
        }}
    }},
    "summary": "A brief summary of the overall changes and their impact."
}}"""

    def generate_commit_message(
        self, diff: str, changed_files: List[GitFile]
    ) -> Tuple[CommitSuggestion, TokenUsage]:
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
                raise ValueError(f"Failed to parse API response as JSON: {str(e)}")

        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("error", {}).get("message", str(e))
                except json.JSONDecodeError:
                    error_message = str(e)
            else:
                error_message = str(e)
            raise ValueError(f"API Request failed: {error_message}")
