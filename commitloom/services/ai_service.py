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
    scope: str | None = None
    breaking: bool = False

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

        # Add breaking change footer if applicable
        if self.breaking:
            lines.append("")
            lines.append("BREAKING CHANGE: This commit contains breaking changes.")

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

    def _detect_scope_from_files(self, changed_files: list[GitFile]) -> str | None:
        """Detect the scope based on changed files."""
        if not changed_files:
            return None

        # Extract top-level directories and file patterns
        paths = [f.path for f in changed_files]

        # Common scope patterns
        if any("cli" in p.lower() for p in paths):
            return "cli"
        elif any("api" in p.lower() for p in paths):
            return "api"
        elif any("core" in p.lower() for p in paths):
            return "core"
        elif any("config" in p.lower() for p in paths):
            return "config"
        elif any("service" in p.lower() for p in paths):
            return "services"
        elif any("test" in p.lower() for p in paths):
            return "tests"
        elif any("doc" in p.lower() for p in paths):
            return "docs"
        elif any(p.endswith(".md") for p in paths):
            return "docs"

        # Try to extract from common path structure
        for path in paths:
            parts = path.split("/")
            if len(parts) > 1 and not parts[0].startswith("."):
                return parts[0]

        return None

    def _detect_breaking_changes(self, diff: str) -> bool:
        """Detect potential breaking changes in the diff."""
        breaking_indicators = [
            r"BREAKING[\s-]CHANGE",
            r"breaking[\s-]change",
            r"API[\s-]breaking",
            r"removed.*public.*method",
            r"deleted.*function",
            r"renamed.*class",
            r"changed.*signature",
            r"major.*version",
        ]

        import re
        for indicator in breaking_indicators:
            if re.search(indicator, diff, re.IGNORECASE):
                return True
        return False

    def generate_prompt(self, diff: str, changed_files: list[GitFile]) -> str:
        """Generate an advanced prompt using few-shot learning and best practices."""
        # Ensure diff is properly encoded by cleaning any invalid UTF-8 sequences
        if isinstance(diff, bytes):
            diff = diff.decode('utf-8', errors='replace')
        elif isinstance(diff, str):
            # Re-encode and decode to ensure clean UTF-8
            try:
                diff = diff.encode('utf-8', errors='replace').decode('utf-8')
            except Exception:
                # If encoding fails, use original string
                pass

        files_summary = ", ".join(f.path for f in changed_files)
        has_binary = any(f.is_binary for f in changed_files)
        binary_files = ", ".join(f.path for f in changed_files if f.is_binary)
        text_files = [f for f in changed_files if not f.is_binary]

        # Detect scope and breaking changes
        scope = self._detect_scope_from_files(changed_files)
        has_breaking = self._detect_breaking_changes(diff)

        if has_binary and not text_files:
            return self._generate_binary_prompt(binary_files, scope)

        prompt = self._generate_advanced_prompt(
            diff=diff,
            files_summary=files_summary,
            binary_files=binary_files,
            scope=scope,
            has_breaking=has_breaking
        )

        return prompt

    def _generate_binary_prompt(self, binary_files: str, scope: str | None) -> str:
        """Generate prompt for binary file changes."""
        scope_part = f"({scope})" if scope else ""
        return (
            "Generate a structured commit message for binary file changes following Conventional Commits.\n"
            "You must respond ONLY with a valid JSON object.\n\n"
            f"Files changed: {binary_files}\n\n"
            "Requirements:\n"
            "1. Title: Follow format 'emoji type(scope): description' (max 50 chars)\n"
            "2. Type: Use 'chore' for binary data updates\n"
            "3. Body: Organize changes with emojis and bullet points\n"
            "4. Include scope if files are in a specific module\n"
            "5. Summary: Brief impact description\n\n"
            "Return ONLY a JSON object in this format:\n"
            "{\n"
            f'  "title": "📝 chore{scope_part}: update binary assets",\n'
            '  "body": {\n'
            '    "Assets": {\n'
            '      "emoji": "📝",\n'
            '      "changes": [\n'
            '        "Updated binary files with new data",\n'
            f'        "Files: {binary_files}"\n'
            "      ]\n"
            "    }\n"
            "  },\n"
            f'  "summary": "Updated binary assets in {scope or "project"}",\n'
            '  "scope": ' + (f'"{scope}"' if scope else 'null') + ',\n'
            '  "breaking": false\n'
            "}"
        )

    def _generate_advanced_prompt(
        self, diff: str, files_summary: str, binary_files: str, scope: str | None, has_breaking: bool
    ) -> str:
        """Generate advanced prompt with few-shot learning."""
        scope_hint = f'\n  "scope": "{scope}",' if scope else '\n  "scope": null,'
        breaking_hint = "true" if has_breaking else "false"

        prompt = f"""You are an expert at writing high-quality git commit messages following Conventional Commits specification.

# Conventional Commits Format
- Format: <type>(<scope>): <description>
- Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
- Scope: Optional, indicates what part of codebase (e.g., api, cli, core, parser)
- Description: Imperative mood, lowercase, no period at end
- Breaking Changes: Add ! after type/scope, e.g., "feat(api)!: change endpoint"

# Files Changed
{files_summary}
{f"Binary files: {binary_files}" if binary_files else ""}

# Git Diff
```
{diff}
```

# Few-Shot Examples of Excellent Commits

Example 1 - Feature Addition:
{{
  "title": "✨ feat(api): add user authentication endpoint",
  "body": {{
    "Features": {{
      "emoji": "✨",
      "changes": [
        "Add JWT-based authentication",
        "Implement login and logout endpoints",
        "Add password hashing with bcrypt"
      ]
    }},
    "Tests": {{
      "emoji": "✅",
      "changes": [
        "Add authentication tests",
        "Test JWT token generation and validation"
      ]
    }}
  }},
  "summary": "Implemented secure JWT authentication system for API",
  "scope": "api",
  "breaking": false
}}

Example 2 - Bug Fix:
{{
  "title": "🐛 fix(parser): handle null values in JSON parser",
  "body": {{
    "Bug Fixes": {{
      "emoji": "🐛",
      "changes": [
        "Add null check before parsing JSON fields",
        "Prevent NullPointerException in edge cases"
      ]
    }}
  }},
  "summary": "Fixed crash when parsing JSON with null values",
  "scope": "parser",
  "breaking": false
}}

Example 3 - Breaking Change:
{{
  "title": "💥 feat(api)!: change authentication response format",
  "body": {{
    "Breaking Changes": {{
      "emoji": "💥",
      "changes": [
        "Changed auth response from string to object",
        "Token now in 'accessToken' field instead of 'token'",
        "Added 'refreshToken' and 'expiresIn' fields"
      ]
    }},
    "Migration": {{
      "emoji": "📝",
      "changes": [
        "Update client code to use new response format",
        "Access token via response.accessToken instead of response.token"
      ]
    }}
  }},
  "summary": "Improved authentication response with refresh tokens and expiration",
  "scope": "api",
  "breaking": true
}}

Example 4 - Performance Improvement:
{{
  "title": "⚡ perf(database): optimize query performance with indexing",
  "body": {{
    "Performance": {{
      "emoji": "⚡",
      "changes": [
        "Add database indexes on user_id and created_at",
        "Reduce query time from 2s to 50ms",
        "Implement connection pooling"
      ]
    }}
  }},
  "summary": "Improved database query performance by 40x with indexing",
  "scope": "database",
  "breaking": false
}}

# Your Task
Analyze the provided diff and generate a commit message following the same high-quality format.

# Requirements
1. Title: Max 50 chars, format "emoji type(scope): description"
2. Use appropriate emoji: ✨ feat, 🐛 fix, 📝 docs, 💄 style, ♻️ refactor, ⚡ perf, ✅ test, 👷 ci, 🔧 chore
3. Detect scope from file paths (e.g., cli, api, core, config)
4. Body: Organize by category with emojis and concise bullet points
5. Breaking changes: Set breaking=true and include migration notes if needed
6. Summary: One sentence describing overall impact
7. Use imperative mood: "add" not "added", "fix" not "fixed"

# Detected Context
- Scope: {scope or "not detected"}
- Potential Breaking Change: {has_breaking}

Return ONLY a JSON object:
{{
  "title": "emoji type(scope): brief description",
  "body": {{
    "Category Name": {{
      "emoji": "📝",
      "changes": [
        "Change description in imperative mood",
        "Another change"
      ]
    }}
  }},
  "summary": "One sentence overall impact",{scope_hint}
  "breaking": {breaking_hint}
}}"""

        return prompt

    def _get_dynamic_temperature(self, diff: str, changed_files: list[GitFile]) -> float:
        """Determine optimal temperature based on change type."""
        # Check for bug fixes (lower temperature for determinism)
        if any(word in diff.lower() for word in ["fix", "bug", "error", "crash", "issue"]):
            return 0.3

        # Check for documentation (slightly higher creativity)
        if any(f.path.endswith(".md") for f in changed_files):
            return 0.6

        # Check for configuration changes (low temperature)
        config_extensions = {".yaml", ".yml", ".toml", ".json", ".ini", ".conf"}
        if any(f.path.endswith(tuple(config_extensions)) for f in changed_files):
            return 0.3

        # Default for features and refactoring
        return 0.5

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
                    scope=None,
                    breaking=False,
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

        # Determine optimal temperature based on change type
        temperature = self._get_dynamic_temperature(diff, changed_files)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": 1000,
            "temperature": temperature,
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
