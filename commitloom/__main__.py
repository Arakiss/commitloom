#!/usr/bin/env python3
"""Entry point for running commitloom as a module."""

import os
import sys

import click
from dotenv import load_dotenv

# Load environment variables before any imports
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
print(f"Loading .env from: {os.path.abspath(env_path)}")
load_dotenv(dotenv_path=env_path)

# Debug: Check if API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key loaded: {'Yes' if api_key else 'No'}")

from .cli import console
from .cli.cli_handler import CommitLoom


def handle_error(error: Exception) -> None:
    """Handle errors in a consistent way."""
    if isinstance(error, KeyboardInterrupt):
        console.print_error("\nOperation cancelled by user.")
    else:
        console.print_error(f"An error occurred: {str(error)}")


@click.command()
@click.option("-y", "--yes", is_flag=True, help="Skip all confirmation prompts")
@click.option("-c", "--combine", is_flag=True, help="Combine all changes into a single commit")
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging")
def main(yes: bool, combine: bool, debug: bool) -> None:
    """Create structured git commits with AI-generated messages."""
    try:
        # Use test_mode=True when running tests (detected by pytest)
        test_mode = "pytest" in sys.modules
        loom = CommitLoom(test_mode=test_mode)
        loom.run(auto_commit=yes, combine_commits=combine, debug=debug)
    except (KeyboardInterrupt, Exception) as e:
        handle_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
