#!/usr/bin/env python3
"""Entry point for running commitloom as a module."""

import os
import sys

import click
from dotenv import load_dotenv

# Load environment variables before any imports
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

from .cli.cli_handler import CommitLoom
from .cli import console


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
        message = "\nOperation cancelled by user." if isinstance(e, KeyboardInterrupt) else f"An error occurred: {str(e)}"
        console.print_error(message)
        sys.exit(1)


if __name__ == "__main__":
    main()
