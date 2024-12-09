#!/usr/bin/env python3
"""Entry point for running commitloom as a module."""

import os
import sys
from typing import NoReturn

import click
from dotenv import load_dotenv

# Load environment variables before any imports
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

from .cli.cli_handler import CommitLoom
from .cli import console


def handle_error(error: Exception) -> NoReturn:
    """Handle errors in a consistent way."""
    if isinstance(error, KeyboardInterrupt):
        console.print_error("\nOperation cancelled by user.")
        sys.exit(1)
    else:
        console.print_error(f"An error occurred: {str(error)}")
        sys.exit(1)


@click.command()
@click.option("-y", "--yes", is_flag=True, help="Skip all confirmation prompts")
@click.option("-c", "--combine", is_flag=True, help="Combine all changes into a single commit")
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging")
def main(yes: bool, combine: bool, debug: bool) -> None:
    """Create structured git commits with AI-generated messages."""
    try:
        loom = CommitLoom()
        loom.run(auto_commit=yes, combine_commits=combine, debug=debug)
    except (KeyboardInterrupt, Exception) as e:
        handle_error(e)


if __name__ == "__main__":
    main()
