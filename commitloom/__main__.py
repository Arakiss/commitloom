#!/usr/bin/env python3
"""Entry point for running commitloom as a module."""

from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables before any imports
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from .cli.main import main

if __name__ == '__main__':
    main() 