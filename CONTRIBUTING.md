# Contributing to CommitLoom

First off, thank you for considering contributing to CommitLoom! While I maintain this project personally, I welcome contributions that help make CommitLoom better.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and constructive environment. I expect everyone to:

- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* Use a clear and descriptive title
* Describe the exact steps to reproduce the problem
* Provide specific examples to demonstrate the steps
* Describe the behavior you observed after following the steps
* Explain which behavior you expected to see instead and why
* Include any error messages or logs

### Suggesting Enhancements

If you have a suggestion for the project, I'd love to hear it! Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* A clear and descriptive title
* A detailed description of the proposed functionality
* Any possible drawbacks or considerations
* If possible, examples of similar features in other projects

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. Ensure the test suite passes
4. Make sure your code follows the existing style
5. Update the documentation if needed

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/your-username/commitloom.git
   cd commitloom
   ```

2. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Install dependencies:
   ```bash
   uv sync --all-extras --dev
   ```

4. Set up pre-commit hooks (if available):
   ```bash
   uv run pre-commit install
   ```

## Style Guide

This project uses:
- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- [MyPy](http://mypy-lang.org/) for type checking
- Line length limit of 88 characters (Black compatible)
- Double quotes for strings
- Type hints are required for all functions

### Code Style Examples

```python
from typing import List, Optional

def process_data(input_data: List[str], max_items: Optional[int] = None) -> List[str]:
    """Process the input data and return filtered results.
    
    Args:
        input_data: List of strings to process
        max_items: Optional maximum number of items to return
        
    Returns:
        List of processed strings
    """
    processed = [item.strip().lower() for item in input_data if item]
    if max_items is not None:
        return processed[:max_items]
    return processed
```

## Testing

- All new features should include tests
- Maintain or improve test coverage
- Run tests with: `uv run pytest`
- Check coverage with: `uv run pytest --cov`

## Documentation

- Keep the README.md up to date
- Document all public functions and classes
- Include docstrings with type information
- Update CHANGELOG.md for significant changes

## Git Commit Messages

I use CommitLoom itself for commit messages! However, if you're writing them manually:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters
- Reference issues and pull requests liberally after the first line

## Questions?

Feel free to open an issue with your question or reach out to me directly at petruarakiss@gmail.com.

Thank you for contributing to CommitLoom! 🧵 