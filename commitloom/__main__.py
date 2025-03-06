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
@click.option("-v", "--version", is_flag=True, callback=lambda ctx, param, value: 
              value and print(f"CommitLoom, version {__version__}") or exit(0) if value else None,
              help="Show the version and exit.")
@click.pass_context
def cli(ctx, debug: bool, version: bool = False) -> None:
    """Create structured git commits with AI-generated messages."""
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug

    if debug:
        console.setup_logging(debug=True)


@cli.command(help="Generate an AI-powered commit message and commit your changes")
@click.option("-y", "--yes", is_flag=True, help="Skip all confirmation prompts")
@click.option("-c", "--combine", is_flag=True, help="Combine all changes into a single commit")
@click.option(
    "-m", 
    "--model", 
    type=click.Choice(list(config.model_costs.keys())), 
    help=f"Specify the AI model to use (default: {config.default_model})"
)
@click.pass_context
def commit(ctx, yes: bool, combine: bool, model: str | None) -> None:
    """Generate commit message and commit changes."""
    debug = ctx.obj.get("DEBUG", False)

    try:
        # Use test_mode=True when running tests (detected by pytest)
        test_mode = "pytest" in sys.modules
        # Only pass API key if not in test mode and it exists
        api_key = None if test_mode else os.getenv("OPENAI_API_KEY")

        # Initialize with test_mode
        loom = CommitLoom(test_mode=test_mode, api_key=api_key if api_key else None)
        
        # Set custom model if specified
        if model:
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
  loom                   Run the default commit command
  loom commit            Generate commit message for staged changes
  loom commit -y         Skip confirmation prompts
  loom commit -c         Combine all changes into a single commit
  loom commit -m MODEL   Specify AI model to use
  loom stats             Show usage statistics
  loom --version         Display version information
  loom help              Show this help message

[bold]Available Models:[/bold]
  {', '.join(config.model_costs.keys())}
  Default: {config.default_model}

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
    known_commands = ['commit', 'stats', 'help']
    # These are options for the main CLI group
    global_options = ['-d', '--debug', '-v', '--version', '--help']
    # These are options specific to the commit command
    commit_options = ['-y', '--yes', '-c', '--combine', '-m', '--model']
    
    # If no arguments, simply add the default commit command
    if len(sys.argv) == 1:
        sys.argv.insert(1, 'commit')
        cli(obj={})
        return
    
    # Check the first argument
    first_arg = sys.argv[1]
    
    # If it's already a known command, no need to modify
    if first_arg in known_commands:
        cli(obj={})
        return
    
    # If it starts with -y or --yes, it's intended for the commit command
    if first_arg in ['-y', '--yes']:
        sys.argv.insert(1, 'commit')
        cli(obj={})
        return
        
    # If it's a global option, don't insert commit
    if any(first_arg == opt for opt in global_options):
        cli(obj={})
        return
        
    # For any other non-option argument that's not a known command, 
    # assume it's meant for the commit command
    if not first_arg.startswith('-'):
        sys.argv.insert(1, 'commit')
    
    cli(obj={})


if __name__ == "__main__":
    main()
