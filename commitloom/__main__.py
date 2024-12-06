#!/usr/bin/env python3
"""Entry point for running commitloom as a module."""


import os

from dotenv import load_dotenv

# Load environment variables before any imports
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

from .cli.main import main

if __name__ == "__main__":
    main()
