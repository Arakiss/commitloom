"""Configuration settings for CommitLoom."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def find_env_file() -> Path | None:
    """
    Search for .env file in multiple locations:
    1. Current working directory
    2. Project root directory
    3. User's home directory
    """
    search_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",
        Path.home() / ".commitloom" / ".env"
    ]

    for path in search_paths:
        if path.is_file():
            return path
    return None

# Try to load environment variables from the first .env file found
env_file = find_env_file()
if env_file:
    load_dotenv(dotenv_path=env_file)

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
        # Try to get API key from multiple sources
        api_key = (
            os.getenv("OPENAI_API_KEY") or
            os.getenv("COMMITLOOM_API_KEY")
        )

        if not api_key:
            config_file = Path.home() / ".commitloom" / "config"
            if config_file.exists():
                with open(config_file) as f:
                    api_key = f.read().strip()

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set.\n\n"
                "Please set it using one of these methods:\n"
                "1. Set OPENAI_API_KEY environment variable\n"
                "2. Set COMMITLOOM_API_KEY environment variable\n"
                "3. Create a .env file in your project directory\n"
                "4. Create a .env file in ~/.commitloom/\n"
                "5. Store your API key in ~/.commitloom/config"
            )

        token_limit = int(os.getenv(
            "COMMITLOOM_TOKEN_LIMIT",
            os.getenv("TOKEN_LIMIT", "120000")
        ))
        max_files = int(os.getenv(
            "COMMITLOOM_MAX_FILES",
            os.getenv("MAX_FILES_THRESHOLD", "5")
        ))
        cost_warning = float(os.getenv(
            "COMMITLOOM_COST_WARNING",
            os.getenv("COST_WARNING_THRESHOLD", "0.05")
        ))
        default_model = os.getenv(
            "COMMITLOOM_MODEL",
            os.getenv("MODEL_NAME", "gpt-4o-mini")
        )

        return cls(
            token_limit=token_limit,
            max_files_threshold=max_files,
            cost_warning_threshold=cost_warning,
            default_model=default_model,
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
