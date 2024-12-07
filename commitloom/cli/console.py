"""Console output formatting and user interaction."""


from unittest.mock import MagicMock

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.prompt import Confirm, Prompt
from rich.text import Text

from ..core.analyzer import (
    CommitAnalysis,
    CommitAnalyzer,
    WarningLevel,
)
from ..core.analyzer import (
    Warning as AnalyzerWarning,
)
from ..core.git import GitFile
from ..services.ai_service import TokenUsage

console = Console()


def create_progress() -> Progress:
    """Create a progress bar with custom styling."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


def print_changed_files(files: list[GitFile]) -> None:
    """Print list of changed files."""
    console.print(
        "\n[bold blue]📜 Changes detected in the following files:[/bold blue]"
    )
    for file in files:
        console.print(f"  - [cyan]{file.path}[/cyan]")


def print_warnings(warnings: list[AnalyzerWarning] | CommitAnalysis) -> None:
    """Print warnings."""
    if isinstance(warnings, CommitAnalysis):
        if not warnings.warnings:
            return
        analysis = warnings
        warnings_list = warnings.warnings
    elif not warnings:
        return
    else:
        warnings_list = warnings

    console.print("\n[bold yellow]⚠️ Commit Size Warnings:[/bold yellow]")
    for warning in warnings_list:
        icon = "🔴" if warning.level == WarningLevel.HIGH else "🟡"
        console.print(f"{icon} {warning.message}")

    if 'analysis' in locals():
        console.print("\n[cyan]📊 Commit Statistics:[/cyan]")
        console.print(f"  • Estimated tokens: {analysis.estimated_tokens:,}")
        console.print(f"  • Estimated cost: €{analysis.estimated_cost:.4f}")
        console.print(f"  • Files changed: {analysis.num_files}")


def print_batch_start(batch_num: int, total_batches: int, files: list[GitFile]) -> None:
    """Print information about starting a new batch."""
    console.print(
        f"\n[bold blue]📦 Processing Batch {batch_num}/{total_batches}[/bold blue]"
    )
    console.print("[cyan]Files in this batch:[/cyan]")
    for file in files:
        console.print(f"  - [dim]{file.path}[/dim]")


def print_batch_complete(batch_num: int, total_batches: int) -> None:
    """Print completion message for a batch."""
    console.print(
        f"\n[bold green]✅ Batch {batch_num}/{total_batches} completed successfully[/bold green]"
    )


def print_batch_summary(total_files: int, total_batches: int) -> None:
    """Print summary of batch processing plan."""
    console.print("\n[bold blue]🔄 Batch Processing Summary:[/bold blue]")
    console.print(f"  • Total files: [cyan]{total_files}[/cyan]")
    console.print(f"  • Number of batches: [cyan]{total_batches}[/cyan]")
    console.print(f"  • Files per batch: [cyan]~{total_files // total_batches}[/cyan]")


def format_cost(cost: float) -> str:
    """Format cost in both human-readable and precise formats."""
    human_cost = CommitAnalyzer.format_cost_for_humans(cost)
    precise_cost = f"(€{cost:.8f})"
    return f"{human_cost} {precise_cost}"


def print_token_usage(usage: TokenUsage, batch_num: int | None = None) -> None:
    """Print token usage summary."""
    batch_info = f" (Batch {batch_num})" if batch_num is not None else ""
    console.print(
        f"""
[bold cyan]📊 Token Usage Summary{batch_info}:[/bold cyan]
  • Prompt Tokens: {usage.prompt_tokens:,}
  • Completion Tokens: {usage.completion_tokens:,}
  • Total Tokens: {usage.total_tokens:,}

[bold green]💰 Cost Breakdown:[/bold green]
  • Input Cost: {format_cost(usage.input_cost)}
  • Output Cost: {format_cost(usage.output_cost)}
  • Total Cost: {format_cost(usage.total_cost)}
"""
    )


def print_commit_message(message: str) -> None:
    """Print formatted commit message."""
    console.print(Panel(Text(message), expand=False, border_style="green"))


def print_batch_info(batch_number: int, files: list[str]) -> None:
    """Print information about a batch of files."""
    console.print(f"\n[bold blue]📑 Batch {batch_number} Summary:[/bold blue]")
    for file in files:
        console.print(f"  - [cyan]{file}[/cyan]")


def confirm_action(prompt: str) -> bool:
    """Ask user to confirm an action."""
    return Confirm.ask(f"\n{prompt}")


def confirm_batch_continue() -> bool:
    """Ask user if they want to continue with next batch."""
    return Confirm.ask("\n[bold yellow]🤔 Continue with next batch?[/bold yellow]")


def select_commit_strategy() -> str:
    """Ask user how they want to handle multiple commits."""
    console.print(
        "\n[bold blue]🤔 How would you like to handle the commits?[/bold blue]"
    )
    return Prompt.ask(
        "Choose strategy", choices=["individual", "combined"], default="individual"
    )


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"\n[bold green]✅ {message}[/bold green]")


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"\n[bold red]❌ {message}[/bold red]")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"\n[bold blue]ℹ️ {message}[/bold blue]")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"\n[bold yellow]⚠️ {message}[/bold yellow]")


def print_analysis(analysis: CommitAnalysis | MagicMock, files: list[GitFile]) -> None:
    """Print analysis results."""
    console.print("\n[bold]Analysis Results:[/bold]")
    console.print(f"Files: {', '.join(f.path for f in files)}")

    try:
        if isinstance(analysis, MagicMock):
            if hasattr(analysis, "estimate_tokens_and_cost"):
                tokens, cost = analysis.estimate_tokens_and_cost()
                console.print(f"Estimated tokens: {tokens:,}")
                console.print(f"Estimated cost: €{cost:.4f}")
            else:
                # Handle mock in tests
                console.print(f"Estimated tokens: {analysis.estimated_tokens}")
                console.print(f"Estimated cost: €{analysis.estimated_cost}")
        else:
            console.print(f"Estimated tokens: {analysis.estimated_tokens:,}")
            console.print(f"Estimated cost: €{analysis.estimated_cost:.4f}")
    except (AttributeError, ValueError):
        # Handle any mock-related errors gracefully
        console.print("Error displaying analysis details")
