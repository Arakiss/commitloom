# CommitLoom 🧵

> Weave perfect git commits with AI-powered intelligence

[![PyPI version](https://badge.fury.io/py/commitloom.svg)](https://badge.fury.io/py/commitloom)
[![Python Version](https://img.shields.io/pypi/pyversions/commitloom)](https://pypi.org/project/commitloom)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/github/Arakiss/commitloom/branch/main/graph/badge.svg?token=NH2X51V6IA)](https://codecov.io/github/Arakiss/commitloom)
[![CI](https://github.com/Arakiss/commitloom/actions/workflows/ci.yml/badge.svg)](https://github.com/Arakiss/commitloom/actions/workflows/ci.yml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

CommitLoom is an intelligent git assistant I created to help developers craft meaningful, structured commits. Like a master weaver's loom, it brings together all the threads of your changes into beautiful, well-organized commits.

## 🎯 Why CommitLoom?

As a developer, I found that managing git commits was often challenging:
- Writing clear, descriptive commit messages takes time
- Large changes are hard to organize effectively
- Maintaining consistency across projects is difficult
- Binary files require special attention

I built CommitLoom to solve these challenges by:
- Automatically generating structured commit messages
- Intelligently batching large changes
- Ensuring consistent commit style
- Providing clear insights about your changes

## 🚀 Quick Start

1. Install CommitLoom via pip or UV:

```bash
# Using pip
pip install commitloom

# Using UV (faster alternative)
uv add commitloom
# or for global installation
uvx commitloom
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

## ✨ Features

- 🤖 **AI-Powered Analysis**: Intelligently analyzes your changes and generates structured, semantic commit messages
- 🧠 **Smart File Grouping**: Advanced semantic analysis to group related files intelligently based on functionality, relationships, and change types
- 🧵 **Smart Batching**: Weaves multiple changes into coherent, logical commits using intelligent grouping algorithms
- 📊 **Complexity Analysis**: Identifies when commits are getting too large or complex
- 🌿 **Branch Suggestions**: Offers to create a new branch for very large commits
- 💰 **Cost Control**: Built-in token and cost estimation to keep API usage efficient
- 📈 **Usage Metrics**: Track your usage, cost savings, and productivity gains with built-in metrics
- 🔍 **Binary Support**: Special handling for binary files with size and type detection
- ⚡ **UV Support**: Compatible with UV package manager for faster dependency management
- 🎨 **Beautiful CLI**: Rich, colorful interface with clear insights and warnings

## 🧠 Smart File Grouping

CommitLoom v1.6.0+ includes advanced semantic analysis for intelligent file grouping. Instead of simple directory-based batching, it now:

### How It Works
- **Change Type Detection**: Automatically identifies the type of changes (features, fixes, tests, docs, refactoring, etc.)
- **File Relationship Analysis**: Detects relationships between files:
  - Test files and their corresponding implementation files
  - Component files that work together (e.g., component + styles + tests)
  - Configuration files and their dependent modules
  - Documentation files and related code
- **Semantic Grouping**: Groups files based on functionality rather than just directory structure
- **Confidence Scoring**: Each grouping decision is scored for reliability

### Benefits
- **Better Commit Organization**: Related changes are grouped together logically
- **Cleaner History**: More meaningful commit messages that reflect actual feature boundaries
- **Reduced Context Switching**: Files that belong together are committed together
- **Intelligent Defaults**: Works automatically but can be disabled with `--no-smart-grouping`

### Example
```bash
# Before: Files grouped by directory
Commit 1: src/components/Button.tsx, src/components/Input.tsx
Commit 2: tests/Button.test.tsx, tests/Input.test.tsx

# After: Files grouped by functionality  
Commit 1: src/components/Button.tsx, tests/Button.test.tsx, docs/Button.md
Commit 2: src/components/Input.tsx, tests/Input.test.tsx, docs/Input.md
```

## 📖 Project History

CommitLoom evolved from my personal script that I was tired of copying across different projects. Its predecessor, GitMuse, was my experiment with local models like Llama through Ollama, but I couldn't achieve the consistent, high-quality results I needed. The rise of cost-effective OpenAI models, particularly gpt-4o-mini, made it possible for me to create a more reliable and powerful tool.

Key improvements over GitMuse:
- Uses OpenAI's models for superior commit message generation
- More cost-effective with the new gpt-4o-mini model
- Better structured for distribution and maintenance
- Enhanced error handling and user experience
- Improved binary file handling

### Recent Major Updates

**v1.6.0+ (2024)**: Introduced intelligent file grouping and performance improvements:
- **Smart File Grouping**: Advanced semantic analysis for better commit organization
- **UV Package Manager Support**: Migrated from Poetry to UV for 10-100x faster dependency management
- **Enhanced CLI**: New `-s/--smart-grouping` and `--no-smart-grouping` options
- **Improved Error Handling**: Better JSON parsing and metrics collection
- **Performance Optimizations**: Reduced logging verbosity and duplicate messages

## ⚙️ Configuration

CommitLoom offers multiple ways to configure your API key and settings:

### Command Usage

CommitLoom can be invoked using either of these commands:

```bash
# Using the full name
loom [command] [options]

# Using the short alias
cl [command] [options]
```

#### Available Commands

- `loom commit` (or simply `loom`): Generate a commit message and commit your changes
- `loom stats`: Display detailed usage statistics and metrics

#### Options

- `-y, --yes`: Auto-confirm all prompts (non-interactive mode)
- `-c, --combine`: Combine all changes into a single commit
- `-s, --smart-grouping`: Enable intelligent file grouping (default: enabled)
- `--no-smart-grouping`: Disable smart grouping and use simple batching
- `-d, --debug`: Enable debug logging
- `-m, --model`: Specify the AI model to use (e.g., gpt-4.1-mini)

#### Usage Examples

```bash
# Basic usage (interactive mode with smart grouping)
loom

# Non-interactive mode with combined commits
loom -y -c

# Use smart grouping with specific model
loom -s -m gpt-4.1

# Disable smart grouping for simple batching
loom --no-smart-grouping

# View usage statistics
loom stats

# View debug information with statistics
loom stats -d
```

### API Key Configuration

You can set your API key using any of these methods (in order of precedence):

1. Environment variables:

```bash
export OPENAI_API_KEY=your-api-key
# or
export COMMITLOOM_API_KEY=your-api-key
```

2. Project-level `.env` file:

```env
OPENAI_API_KEY=your-api-key
# or
COMMITLOOM_API_KEY=your-api-key
```

3. Global configuration file:

```bash
# Create global config directory
mkdir -p ~/.commitloom
# Store your API key
echo "your-api-key" > ~/.commitloom/config
```

4. Global `.env` file in `~/.commitloom/.env`

### Other Settings

Configure additional settings via environment variables or `.env` files:

```env
# New environment variable names (recommended)
COMMITLOOM_TOKEN_LIMIT=120000
COMMITLOOM_MAX_FILES=5
COMMITLOOM_COST_WARNING=0.05
COMMITLOOM_MODEL=gpt-4o-mini

# Legacy names (still supported)
TOKEN_LIMIT=120000
MAX_FILES_THRESHOLD=5
COST_WARNING_THRESHOLD=0.05
MODEL_NAME=gpt-4o-mini
```

Configuration files are searched in this order:
1. Current working directory `.env`
2. Project root directory `.env`
3. Global `~/.commitloom/.env`
4. System environment variables

### 🤖 Model Configuration

CommitLoom supports any OpenAI model for commit message generation. You can specify any model name (e.g., `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`, etc.) using the `MODEL_NAME` or `COMMITLOOM_MODEL` environment variable, or with the `-m`/`--model` CLI option.

| Model           | Description                        | Input (per 1M tokens) | Output (per 1M tokens) | Best for                |
|-----------------|------------------------------------|-----------------------|------------------------|-------------------------|
| gpt-4.1         | Highest quality, 1M ctx, multimodal| $2.00                 | $8.00                  | Final docs, critical    |
| gpt-4.1-mini    | Default, best cost/quality         | $0.40                 | $1.60                  | Most use cases          |
| gpt-4.1-nano    | Fastest, cheapest                  | $0.10                 | $0.40                  | Drafts, previews        |
| gpt-4o-mini     | Legacy, cost-efficient             | $0.15                 | $0.60                  | Legacy/compatibility    |
| gpt-4o          | Legacy, powerful                   | $2.50                 | $10.00                 | Legacy/compatibility    |
| gpt-3.5-turbo   | Legacy, fine-tuned                 | $3.00                 | $6.00                  | Training data           |
| gpt-4o-2024-05-13| Legacy, previous version           | $5.00                 | $15.00                 | Legacy support          |

> **Default model:** `gpt-4.1-mini` (best balance for documentation and code)

> **Warning:** If you use a model that is not in the above list, CommitLoom will still work, but cost estimation and token pricing will not be available for that model. You will see a warning in the CLI, and cost will be reported as zero. To add cost support for a new model, update the `model_costs` dictionary in `commitloom/config/settings.py`.

You can change the model by setting the `MODEL_NAME` environment variable. The default `gpt-4.1-mini` model is recommended as it provides the best balance of cost and quality for commit message generation. It's OpenAI's most cost-efficient small model that's smarter and cheaper than GPT-3.5 Turbo.

> Note: Prices are based on OpenAI's official pricing (https://openai.com/pricing/). Batch API usage can provide a 50% discount but responses will be returned within 24 hours.

## ❓ FAQ

### Why the name "CommitLoom"?

I chose the name to reflect the tool's ability to weave together different aspects of your changes into a coherent commit, like a loom weaving threads into fabric. It emphasizes both the craftsmanship aspect of good commits and the tool's ability to bring structure to complex changes.

### Why use OpenAI instead of local models?

While local models like Llama are impressive, my experience with GitMuse showed that for specialized tasks like commit message generation, OpenAI's models provide superior results. With the introduction of cost-effective models like gpt-4o-mini, I found that the benefits of cloud-based AI outweigh the advantages of local models for this specific use case.

### How much will it cost to use CommitLoom?

With the default gpt-4.1-mini model, costs are very low:
- Input: $0.40 per million tokens  
- Output: $1.60 per million tokens

For perspective, a typical commit analysis:
- Uses ~1,000-2,000 tokens
- Costs less than $0.004 (0.4 cents)
- That's about 250 commits for $1

This makes it one of the most cost-effective tools in its category, especially when compared to the time saved and quality of commit messages generated.

### Can I use CommitLoom in CI/CD pipelines?

Yes! Use the `-y` flag for non-interactive mode:
```bash
loom -y
```

### How does CommitLoom track metrics and usage statistics?

CommitLoom keeps track of various metrics to help you understand your usage patterns:

- **Usage tracking**: Number of commits generated, tokens used, and associated costs
- **Time savings**: Estimated time saved compared to writing commit messages manually
- **Repository statistics**: Which repositories you use CommitLoom with most frequently
- **Model usage**: Performance metrics for different AI models
- **Cost analysis**: Detailed breakdown of token usage and associated costs

All metrics are stored locally in your user data directory (`~/.local/share/commitloom/metrics` on Linux) and are never sent to external servers.

To view your metrics, simply run:
```bash
loom stats
```

For detailed documentation on the metrics system, see the [Usage Metrics Documentation](docs/usage_metrics/README.md).

### How does CommitLoom handle large changes?

CommitLoom automatically:
1. Analyzes the size and complexity of changes
2. Uses smart grouping to organize related files together
3. Warns about potentially oversized commits
4. Suggests splitting changes when appropriate
5. Maintains context across split commits
6. Optionally creates a new branch when commits are very large

### What is smart grouping and how does it work?

Smart grouping is CommitLoom's advanced semantic analysis feature that intelligently organizes your changed files:

- **Detects relationships**: Groups test files with their implementation files, components with their styles, etc.
- **Understands change types**: Identifies whether changes are features, fixes, documentation, tests, or refactoring
- **Semantic analysis**: Goes beyond directory structure to understand what files actually work together
- **Automatic by default**: Enabled automatically in v1.6.0+, but can be disabled with `--no-smart-grouping`

This results in more logical commits where related files are grouped together, making your git history cleaner and more meaningful.

## 🛠️ Development Status

- ✅ **CI/CD**: Automated testing, linting, and publishing with GitHub Actions
- ✅ **Package Management**: Migrated to UV for faster dependency resolution and builds
- ✅ **Code Quality**: 
  - Ruff for linting and formatting
  - MyPy for static type checking
  - 70%+ test coverage with pytest
- ✅ **Smart Features**: Advanced semantic analysis and intelligent file grouping
- ✅ **Distribution**: Available on PyPI and GitHub Releases
- ✅ **Documentation**: Comprehensive README with feature examples and type hints
- ✅ **Maintenance**: Actively maintained and accepting contributions

## 🤝 Contributing

While I maintain this project personally, I welcome contributions! If you'd like to help improve CommitLoom, please:
- Check the issues page for current tasks
- Follow the code style guidelines
- Add tests for new features
- Update documentation as needed

See the [Contributing Guidelines](CONTRIBUTING.md) for detailed instructions.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">Crafted with 🧵 by <a href="https://github.com/Arakiss">@Arakiss</a></p>
