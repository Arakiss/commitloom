"""Configuration settings for CommitLoom."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables at module level
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


@dataclass(frozen=True)
class ModelCosts:
    """Cost configuration for AI models."""

    input: float
    output: float


@dataclass(frozen=True)
class Config:
    """Main configuration settings."""

    token_limit: int
    max_files_threshold: int
    cost_warning_threshold: float
    default_model: str
    token_estimation_ratio: int
    ignored_patterns: list[str]
    model_costs: dict[str, ModelCosts]
    api_key: str

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        return cls(
            token_limit=int(os.getenv("TOKEN_LIMIT", "120000")),
            max_files_threshold=int(os.getenv("MAX_FILES_THRESHOLD", "5")),
            cost_warning_threshold=float(os.getenv("COST_WARNING_THRESHOLD", "0.05")),
            default_model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            token_estimation_ratio=4,
            ignored_patterns=[
                "bun.lockb",
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
                ".env",
                ".env.*",
                "*.lock",
                "*.log",
                "__pycache__/*",
                "*.pyc",
                ".DS_Store",
                "dist/*",
                "build/*",
                "node_modules/*",
                "*.min.js",
                "*.min.css",
            ],
            model_costs={
                "gpt-4o-mini": ModelCosts(
                    input=0.00015,
                    output=0.00060,
                ),
                "gpt-4o": ModelCosts(
                    input=0.00250,
                    output=0.01000,
                ),
                "gpt-3.5-turbo": ModelCosts(
                    input=0.00300,
                    output=0.00600,
                ),
                "gpt-4o-2024-05-13": ModelCosts(
                    input=0.00500,
                    output=0.01500,
                ),
            },
            api_key=api_key,
        )


# Global configuration instance
config = Config.from_env()
