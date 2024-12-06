# CommitLoom 🧵

> Weave perfect git commits with AI-powered intelligence

CommitLoom is an intelligent git assistant that helps you craft meaningful, structured commits. Like a master weaver's loom, it brings together all the threads of your changes into beautiful, well-organized commits.

[![PyPI version](https://img.shields.io/pypi/v/commitloom.svg)](https://pypi.org/project/commitloom/)
[![Python versions](https://img.shields.io/pypi/pyversions/commitloom.svg)](https://pypi.org/project/commitloom/)
[![License](https://img.shields.io/github/license/yourusername/commitloom.svg)](https://github.com/yourusername/commitloom/blob/main/LICENSE)
[![CI](https://github.com/yourusername/commitloom/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/commitloom/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yourusername/commitloom/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/commitloom)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Downloads](https://pepy.tech/badge/commitloom)](https://pepy.tech/project/commitloom)

## Project Status

- ✅ **CI/CD**: Automated testing, linting, and publishing
- ✅ **Code Quality**: 
  - Ruff for linting and formatting
  - MyPy for static type checking
  - 70%+ test coverage
- ✅ **Distribution**: Available on PyPI and GitHub Releases
- ✅ **Documentation**: Comprehensive README and type hints
- ✅ **Maintenance**: Actively maintained and accepting contributions

## ✨ Features

- 🤖 **AI-Powered Analysis**: Intelligently analyzes your changes and generates structured, semantic commit messages
- 🧵 **Smart Batching**: Weaves multiple changes into coherent, logical commits
- 📊 **Complexity Analysis**: Identifies when commits are getting too large or complex
- 💰 **Cost Control**: Built-in token and cost estimation to keep API usage efficient
- 🔍 **Binary Support**: Special handling for binary files with size and type detection
- 🎨 **Beautiful CLI**: Rich, colorful interface with clear insights and warnings

## 🚀 Quick Start

1. Install CommitLoom via pip:

```bash
pip install commitloom
```

2. Set up your OpenAI API key:

```bash
export OPENAI_API_KEY=your-api-key
# or create a .env file with OPENAI_API_KEY=your-api-key
```

3. Stage your changes with git:

```bash
git add .  # or stage specific files
```

4. Use CommitLoom to create your commit:

```bash
loom  # Interactive mode
# or
loom -y  # Non-interactive mode
```

## 📝 CLI Usage

CommitLoom can be used in both interactive and non-interactive modes:

```bash
# Interactive mode (default)
loom

# Non-interactive mode (auto-confirm all prompts)
loom -y

# Combine all changes into a single commit
loom -c

# Enable verbose logging
loom -v

# Show help
loom --help
```

### CLI Options

- `-y, --yes`: Auto-confirm all prompts (non-interactive mode)
- `-c, --combine`: Combine all changes into a single commit
- `-v, --verbose`: Enable verbose logging
- `-h, --help`: Show help message

### Interactive Features

- Analyzes staged changes and suggests commit messages
- Handles large changes by splitting them into batches
- Provides warnings for complex changes
- Shows token usage and cost estimates
- Allows choosing between individual or combined commits

### Non-Interactive Features

- Perfect for CI/CD pipelines
- Automatically handles batching and commits
- Provides clear error messages
- Maintains high commit quality without user intervention

## 🎯 Why CommitLoom?

Managing git commits can be challenging:
- Writing clear, descriptive commit messages takes time
- Large changes are hard to organize effectively
- Maintaining consistency across a team is difficult
- Binary files require special attention

CommitLoom solves these challenges by:
- Automatically generating structured commit messages
- Intelligently batching large changes
- Ensuring consistent commit style
- Providing clear insights about your changes

## 🛠️ How It Works

When you run `loom`, it:

1. 🔍 **Analyzes** your staged changes
2. 📊 **Evaluates** complexity and size
3. 🤖 **Generates** appropriate commit messages
4. 🧵 **Organizes** changes into optimal batches if needed
5. 💡 **Guides** you through the commit process

## ⚙️ Configuration

Configure via environment variables or `.env` file:

```env
# Required
OPENAI_API_KEY=your-api-key

# Optional with defaults
TOKEN_LIMIT=120000
MAX_FILES_THRESHOLD=5
COST_WARNING_THRESHOLD=0.05
MODEL_NAME=gpt-4o-mini  # Default and most cost-effective model
```

### 🤖 Model Configuration

CommitLoom supports various OpenAI models with different cost implications:

| Model | Description | Cost per 1M tokens (Input/Output) | Best for |
|-------|-------------|----------------------------------|----------|
| gpt-4o-mini | Default, optimized for commits | $0.15/$0.60 | Most use cases |
| gpt-4o | Latest model, powerful | $2.50/$10.00 | Complex analysis |
| gpt-4o-2024-05-13 | Previous version | $5.00/$15.00 | Legacy support |
| gpt-3.5-turbo | Fine-tuned version | $3.00/$6.00 | Training data |

You can change the model by setting the `MODEL_NAME` environment variable. The default `gpt-4o-mini` model is recommended as it provides the best balance of cost and quality for commit message generation. It's OpenAI's most cost-efficient small model that's smarter and cheaper than GPT-3.5 Turbo.

> Note: Prices are based on OpenAI's official pricing (https://openai.com/api/pricing/). Batch API usage can provide a 50% discount but responses will be returned within 24 hours.

### Cost Management

Built-in cost optimization:
- Pre-estimates API costs
- Provides clear usage metrics
- Warns about expensive operations
- Helps optimize token usage

You can set custom warning thresholds:

```env
COST_WARNING_THRESHOLD=0.10  # Warn at €0.10
```

## 📝 CLI Commands

```bash
loom              # Interactive commit creation
loom analyze      # Just analyze changes
loom suggest      # Generate commit message suggestions
loom batch        # Process changes in batches
```

## 🎨 Features in Detail

### Smart Change Analysis

CommitLoom analyzes your changes to ensure quality:
- Evaluates commit size and complexity
- Warns about potential issues
- Suggests improvements
- Monitors token usage and costs

### Intelligent Batching

For larger changes, CommitLoom:
- Splits changes into optimal batches
- Maintains context across commits
- Offers flexible commit strategies
- Preserves commit quality at scale

### Cost Management

Built-in cost optimization:
- Pre-estimates API costs
- Provides clear usage metrics
- Warns about expensive operations
- Helps optimize token usage

## 🔧 Advanced Usage

### Custom Ignore Patterns

Configure files to ignore:

```env
IGNORED_PATTERNS=[
    "*.lock",
    "dist/*",
    "node_modules/*"
]
```

### Cost Thresholds

Set custom warning thresholds:

```env
COST_WARNING_THRESHOLD=0.10  # Warn at €0.10
```

## 🤝 Contributing

We welcome contributions! See our [Contributing Guidelines](CONTRIBUTING.md) for:
- Setting up development
- Running tests
- Submitting PRs
- Code style guidelines

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙌 Acknowledgments

CommitLoom is powered by:
- OpenAI's GPTs models for intelligent analysis
- Rich for beautiful terminal interfaces
- Poetry for dependency management
- And many other amazing open source projects

---

<p align="center">Crafted with 🧵 by developers, for developers</p>

## 🛠️ Local Development Setup

### Prerequisites

- Python 3.11 or higher
- Poetry (Python package manager)
- Git

### Setting Up Development Environment

1. Clone the repository:

```bash
git clone https://github.com/yourusername/commitloom.git
cd commitloom
```

2. Install Poetry (if not already installed):

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install dependencies:

```bash
poetry install
```

4. Set up environment variables:

```bash
cp .env.example .env  # Create from example if available
# Edit .env file with your configuration:
# OPENAI_API_KEY=your-api-key
# TOKEN_LIMIT=120000
# MAX_FILES_THRESHOLD=5
# COST_WARNING_THRESHOLD=0.05
```

5. Activate the virtual environment:

```bash
poetry shell
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_specific.py
```

### Running Locally

1. Install the package in editable mode:

```bash
poetry install
```

2. Run the CLI:

```bash
poetry run loom
```

### Development Commands

```bash
# Format code
poetry run black .

# Run linter
poetry run flake8

# Run type checker
poetry run mypy .
```