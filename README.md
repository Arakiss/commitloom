# CommitLoom 🧵

> Weave perfect git commits with AI-powered intelligence

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

## ✨ Features

- 🤖 **AI-Powered Analysis**: Intelligently analyzes your changes and generates structured, semantic commit messages
- 🧵 **Smart Batching**: Weaves multiple changes into coherent, logical commits
- 📊 **Complexity Analysis**: Identifies when commits are getting too large or complex
- 💰 **Cost Control**: Built-in token and cost estimation to keep API usage efficient
- 🔍 **Binary Support**: Special handling for binary files with size and type detection
- 🎨 **Beautiful CLI**: Rich, colorful interface with clear insights and warnings

## 📖 Project History

CommitLoom evolved from my personal script that I was tired of copying across different projects. Its predecessor, GitMuse, was my experiment with local models like Llama through Ollama, but I couldn't achieve the consistent, high-quality results I needed. The rise of cost-effective OpenAI models, particularly gpt-4o-mini, made it possible for me to create a more reliable and powerful tool.

Key improvements over GitMuse:
- Uses OpenAI's models for superior commit message generation
- More cost-effective with the new gpt-4o-mini model
- Better structured for distribution and maintenance
- Enhanced error handling and user experience
- Improved binary file handling

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

## ❓ FAQ

### Why the name "CommitLoom"?

I chose the name to reflect the tool's ability to weave together different aspects of your changes into a coherent commit, like a loom weaving threads into fabric. It emphasizes both the craftsmanship aspect of good commits and the tool's ability to bring structure to complex changes.

### Why use OpenAI instead of local models?

While local models like Llama are impressive, my experience with GitMuse showed that for specialized tasks like commit message generation, OpenAI's models provide superior results. With the introduction of cost-effective models like gpt-4o-mini, I found that the benefits of cloud-based AI outweigh the advantages of local models for this specific use case.

### How much will it cost to use CommitLoom?

With the default gpt-4o-mini model, costs are very low:
- Input: $0.15 per million tokens
- Output: $0.60 per million tokens
For perspective, a typical commit analysis might use 1000-2000 tokens, costing less than $0.002.

### Can I use CommitLoom in CI/CD pipelines?

Yes! Use the `-y` flag for non-interactive mode:
```bash
loom -y
```

### How does CommitLoom handle large changes?

CommitLoom automatically:
1. Analyzes the size and complexity of changes
2. Warns about potentially oversized commits
3. Suggests splitting changes when appropriate
4. Maintains context across split commits

## 🛠️ Development Status

- ✅ **CI/CD**: Automated testing, linting, and publishing
- ✅ **Code Quality**: 
  - Ruff for linting and formatting
  - MyPy for static type checking
  - 70%+ test coverage
- ✅ **Distribution**: Available on PyPI and GitHub Releases
- ✅ **Documentation**: Comprehensive README and type hints
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

<p align="center">Crafted with 🧵 by <a href="https://github.com/yourusername">@yourusername</a></p>