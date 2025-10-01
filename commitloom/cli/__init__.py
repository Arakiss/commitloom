"""CLI module for CommitLoom.

This module contains the command-line interface components including
the main CLI handler and console output utilities.
"""

from . import console
from .cli_handler import CommitLoom

__all__ = [
    "CommitLoom",
    "console",
]
