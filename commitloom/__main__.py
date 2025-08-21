#!/usr/bin/env python3
"""Entry point for running commitloom as a module."""

import os
import sys

import click
from dotenv import load_dotenv

# Load environment variables before any imports
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

from . import __version__
from .cli import console
from .cli.cli_handler import CommitLoom
from .config.settings import config


def handle_error(error: BaseException) -> None:
    """Handle errors in a consistent way."""
    if isinstance(error, KeyboardInterrupt):
        console.print_error("\nOperation cancelled by user.")
    else:
        console.print_error(f"An error occurred: {str(error)}")


@click.group()
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "-v",
    "--version",
    is_flag=True,
    callback=lambda ctx, param, value: value and print(f"CommitLoom, version {__version__}") or exit(0)
    if value
    else None,
    help="Show the version and exit.",
)
@click.pass_context
def cli(ctx, debug: bool, version: bool = False) -> None:
    """Create structured git commits with AI-generated messages."""
    ctx.ensure_object(dict)

    # Check for debug mode in config file or environment variable
    debug_env = os.getenv("DEBUG_MODE", "").lower() in ("true", "1", "yes")
    ctx.obj["DEBUG"] = debug or debug_env

    if debug or debug_env:
        console.setup_logging(debug=True)


@cli.command(help="Generate an AI-powered commit message and commit your changes")
@click.option("-y", "--yes", is_flag=True, help="Skip all confirmation prompts")
@click.option("-c", "--combine", is_flag=True, help="Combine all changes into a single commit")
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "-s",
    "--smart-grouping/--no-smart-grouping",
    default=True,
    help="Enable/disable intelligent file grouping (default: enabled)",
)
@click.option(
    "-m",
    "--model",
    type=str,  # Permitir cualquier string
    help=f"Specify any OpenAI model to use (default: {config.default_model})",
)
@click.pass_context
def commit(ctx, yes: bool, combine: bool, debug: bool, smart_grouping: bool, model: str | None) -> None:
    """Generate commit message and commit changes."""
    # Use debug from either local flag or global context
    debug = debug or ctx.obj.get("DEBUG", False)

    if debug:
        console.setup_logging(debug=True)

    try:
        test_mode = "pytest" in sys.modules
        api_key = None if test_mode else os.getenv("OPENAI_API_KEY")
        loom = CommitLoom(test_mode=test_mode, api_key=api_key if api_key else None)

        # Configure smart grouping
        loom.use_smart_grouping = smart_grouping
        if smart_grouping:
            console.print_info("Smart grouping: ENABLED (analyzing file relationships)")
        else:
            console.print_info("Smart grouping: DISABLED (using basic grouping)")

        # Validación personalizada para modelos OpenAI
        if model:
            if not model.startswith("gpt-"):
                console.print_warning(
                    f"Model '{model}' does not appear to be a valid OpenAI model (should start with 'gpt-')."
                )
            if model not in config.model_costs:
                console.print_warning(
                    f"Model '{model}' is not in the known cost list. Cost estimation will be unavailable or inaccurate."
                )
            os.environ["COMMITLOOM_MODEL"] = model
            console.print_info(f"Using model: {model}")
        loom.run(auto_commit=yes, combine_commits=combine, debug=debug)
    except (KeyboardInterrupt, Exception) as e:
        handle_error(e)
        sys.exit(1)


@cli.command(help="Show usage statistics and metrics")
@click.pass_context
def stats(ctx) -> None:
    """Show usage statistics."""
    debug = ctx.obj.get("DEBUG", False)

    try:
        # Create a CommitLoom instance and run the stats command
        loom = CommitLoom(test_mode=True)  # Test mode to avoid API key requirement
        if debug:
            console.setup_logging(debug=True)
        loom.stats_command()
    except (KeyboardInterrupt, Exception) as e:
        handle_error(e)
        sys.exit(1)


@cli.command(help="Display detailed help information")
def help() -> None:
    """Display detailed help information about CommitLoom."""
    help_text = f"""
[bold cyan]CommitLoom v{__version__}[/bold cyan]
[italic]Weave perfect git commits with AI-powered intelligence[/italic]

[bold]Basic Usage:[/bold]
  loom                          Run the default commit command
  loom commit                   Generate commit message for staged changes
  loom commit -y                Skip confirmation prompts
  loom commit -c                Combine all changes into a single commit
  loom commit -s                Enable smart grouping (default)
  loom commit --no-smart-grouping  Disable smart grouping
  loom commit -m MODEL          Specify any OpenAI model to use
  loom stats                    Show usage statistics
  loom --version                Display version information
  loom help                     Show this help message

[bold]Available Models:[/bold]
  {", ".join(config.model_costs.keys())}
  Default: {config.default_model}
  (You can use any OpenAI model name, but cost estimation is only available for the above models.)

[bold]Environment Setup:[/bold]
  1. Set OPENAI_API_KEY in your environment or in a .env file
  2. Stage your changes with 'git add'
  3. Run 'loom' to generate and apply commit messages

[bold]Documentation:[/bold]
  Full documentation: https://github.com/Arakiss/commitloom#readme
    """
    console.console.print(help_text)


# For backwards compatibility, default to commit command if no subcommand provided
def main() -> None:
    """Entry point for the CLI."""
    known_commands = ["commit", "stats", "help"]
    # These are options for the main CLI group
    global_options = ["-v", "--version", "--help"]
    # These are debug options that should include commit command
    debug_options = ["-d", "--debug"]
    # These are options specific to the commit command
    commit_options = [
        "-y",
        "--yes",
        "-c",
        "--combine",
        "-m",
        "--model",
        "-s",
        "--smart-grouping",
        "--no-smart-grouping",
    ]

    # If no arguments, simply add the default commit command
    if len(sys.argv) == 1:
        sys.argv.insert(1, "commit")
        cli(obj={})
        return

    # Check if we have debug option anywhere in the arguments
    has_debug = any(arg in debug_options for arg in sys.argv[1:])

    # Check the first argument
    first_arg = sys.argv[1]

    # If it's already a known command, no need to modify
    if first_arg in known_commands:
        cli(obj={})
        return

    # If it's a global option without debug, don't insert commit
    if first_arg in global_options and not has_debug:
        cli(obj={})
        return

    # If we have debug option anywhere, or commit-specific options, add commit command
    if has_debug or first_arg in commit_options or any(arg in commit_options for arg in sys.argv[1:]):
        # Insert 'commit' at the beginning of options
        sys.argv.insert(1, "commit")
        cli(obj={})
        return

    # For any other non-option argument that's not a known command,
    # assume it's meant for the commit command
    if not first_arg.startswith("-"):
        sys.argv.insert(1, "commit")

    cli(obj={})


if __name__ == "__main__":
    main()
