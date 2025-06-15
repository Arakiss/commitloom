# Changelog

## [1.5.4] - 2025-06-15


### ✨ Features
- suggest new branch for large commits

### 🐛 Bug Fixes
- remove debug prints

### 📦 Build System
- bump version to 1.5.4

### 🔄 Other Changes
- Merge pull request #3 from Arakiss/codex/identificar-características-a-mejorar-o-agregar
- Merge pull request #2 from Arakiss/codex/find-more-potential-bugs-to-fix
- Merge pull request #1 from Arakiss/codex/fix-bug
- fix metrics file parsing
- bump version 1.5.3

## [1.4.0] - 2025-04-17


### ✨ Features
- set gpt-4.1-mini as default model and add 2025 OpenAI models/pricing

### 📦 Build System
- bump version to 1.4.0
- bump version to 1.3.0

## [1.2.10] - 2025-03-06


### 📦 Build System
- bump version to 1.2.10

## [1.2.9] - 2025-03-06


### 📦 Build System
- bump version to 1.2.9

### 🔄 Other Changes
- ✨ feat: add debug options for commit command
- 🔖 chore: bump version to 1.2.8

## [1.2.8] - 2025-03-06


### 🐛 Bug Fixes
- correct GitFile parameter types in tests

### 💄 Styling
- fix blank line whitespace issues
- fix line length issues and format cli_handler.py

### 📦 Build System
- bump version to 1.2.8
- bump version to 1.2.7 and fix metrics storage
- bump version to 1.2.6 and connect release workflows
- bump version to 1.2.5 and fix release creation
- bump version to 1.2.4 and fix release workflow
- bump version to 1.2.3

### 👷 CI
- make linting and test coverage requirements more flexible
- add manual PyPI publish workflow and update version
- enable verbose output in PyPI publish workflow

### 🔄 Other Changes
- ✨ feat: enhance metrics calculations and logging
- ✨ feat: enhance CLI with model selection and help

## [1.2.7] - 2025-03-05
### 🛠️ Fixes
- Fix JSON handling in metrics storage
- Make statistics display more robust against malformed data
- Add safety checks for repository and model usage data



## [1.2.6] - 2025-03-05
### 🛠️ Fixes
- Connect Auto Release and Package Publishing workflows
- Automate PyPI package publishing after GitHub release
- Fix workflow integration between GitHub release and PyPI publish

## [1.2.5] - 2025-03-05
### 🛠️ Fixes
- Use actions/create-release instead of softprops/action-gh-release to ensure proper release event triggering

## [1.2.4] - 2025-03-05
### 🛠️ Fixes
- Fix GitHub release workflow to trigger PyPI publishing correctly
- Add "released" type to the publish workflow trigger
- Ensure GitHub releases are properly formatted

## [1.2.3] - 2025-03-05
### 🛠️ Fixes
- Fix auto-release workflow to correctly detect version bump commits
- Add verbose output to PyPI publish workflow for better diagnostics

## [1.2.2] - 2025-03-05
### 🛠️ Fixes
- Update publish workflow to trigger on both published and created releases

## [1.2.1] - 2025-03-05
### 🔧 Improvements
- Fix GitHub Actions permissions for release automation
- Adjust test coverage threshold to 70%
- Improve CLI test suite compatibility

## [1.2.0] - 2025-03-05
### ✨ Features
- 🚀 Add GitHub Actions workflow for automatic release creation
- 🔧 Fix model property access in AI service 
- 🚀 Improve CLI test coverage

## [1.1.0] - 2025-03-05
### ✨ Features
- ✨ feat: add local metrics and usage statistics
- 📊 Add tracking for usage patterns, token consumption, and cost
- 📈 Track time savings and productivity metrics
- 📝 Add comprehensive documentation for metrics system
- 🖥️ Add new `stats` command to view usage statistics
- 🔧 fix: update console print methods in stats command
- 🐛 fix: continue staging files when a file is not found or deleted

## [1.0.1] - 2024-12-10

### 📦 Build System
- bump version to 1.0.1

### 🔄 Other Changes
- 🔧 fix: update commit loom calls with api_key
- 🐛 fix: update test files for compatibility
- 🔧 feat: require API key in AIService
- ✨ feat: enhance CommitLoom with API key support

## [1.0.0] - 2024-12-10


### ✨ Features
- batch 1/5 - 5 files

### 📦 Build System
- bump version to 1.0.0

### 🔄 Other Changes
- 📝 fix: improve warning message formatting
- ✨ test: improve tests for CommitLoom
- ✨ feat: enhance AI service and CLI handling
- ✨ feat: test commit
- ✨ feat: test commit
- ✨ feat: test commit
- ✨ feat: test commit
- 🐛 fix: remove trailing whitespace in test files
- 🔧 chore: reorganize imports and cleanup tests
- ✨ feat: enhance AI service and batch processing tests
- 🔧 refactor: improve commit analysis and batch processing
- 🔧 refactor: improve CLI tests and error handling
- 🔧 fix: improve warnings and error handling
- 🧪 test: improve console action confirmation test
- ✨ feat: enhance commit analysis and AI service
- ✨ feat: add pytest-mock and enhance tests
- ✨ feat: enhance warning system and improve API service
- ✨ test: add unit tests for git operations
- ✨ feat: add tests for batch processing and commits
- ✨ feat: enhance AI service tests and console outputs
- ✨ test: improve CLI test coverage
- ✨ feat: improve error handling and logging
- 🛠️ fix: improve error handling in main
- ✨ feat: improve error handling in main.py
- 🐛 fix: improve error handling in main function
- ✨ feat: improve error handling in main module
- ✨ feat: enhance CLI argument handling tests
- 🔧 test: refactor CLI tests with Click
- 🔧 refactor: update tests for CLI handler module
- ✨ feat: add folder4_subfolder2_module.py
- ✨ feat: add new modules to folder4
- ✨ feat: add new modules in test_batch
- ✨ feat: add new module and folders
- ✨ feat: add new modules for subfolders
- ✨ feat: add new module and init files
- ✨ feat: add CLI handler and test modules
- ✨ chore: refactor tests for better clarity
- 🗑️ chore: remove deprecated modules
- 🗑️ refactor: remove unused modules
- 🔧 feat: enhance Git file handling and config
- 🔧 refactor: improve CLI and file handling
- ✨ feat: enhance CLI with argument parsing
- 🔧 refactor: update type hints and clean imports
- ✨ feat: add new test files
- ✨ feat: add new test files for subfolder1
- ✨ feat: enhance batch processing in CommitLoom
- ✨ feat: add auto-confirm mode for actions
- ✨ feat: enhance commit processing and staging
- ✨ feat: implement batch processing for commits
- ✨ feat: add folder4 modules and configuration
- ✨ feat: add new modules and configuration
- ✨ feat: add new modules and config files
- ✨ feat: add initial modules and config files
- 🔧 refactor: improve subprocess handling

## [0.9.8] - 2024-12-09


### 📦 Build System
- bump version to 0.9.8

### 🔄 Other Changes
- ✨ feat: enhance commit process with CLI options

## [0.9.7] - 2024-12-09


### 📦 Build System
- bump version to 0.9.7

### 🔄 Other Changes
- ✨ feat: improve batch processing for commits

## [0.9.6] - 2024-12-08


### 📦 Build System
- bump version to 0.9.6

### 🔄 Other Changes
- ✨ feat: enhance batch processing and stashing

## [0.9.5] - 2024-12-08


### 📦 Build System
- bump version to 0.9.5

### 🔄 Other Changes
- ✨ feat: improve file processing and validation

## [0.9.4] - 2024-12-08


### 📦 Build System
- bump version to 0.9.4

### 🔄 Other Changes
- 🔧 refactor: improve file validation logic

## [0.9.3] - 2024-12-08


### 📦 Build System
- bump version to 0.9.3

### 🔄 Other Changes
- 🔧 chore: update publish workflow configuration
- 🔧 chore: refine publish workflow for PyPI

## [0.9.2] - 2024-12-08


### 📦 Build System
- bump version to 0.9.2

### 🔄 Other Changes
- 🔧 refactor: improve commit processing logic
- ✨ feat: restructure CI workflow for publishing

## [0.9.1] - 2024-12-07


### 📦 Build System
- bump version to 0.9.1

### 🔄 Other Changes
- 💡 docs: enhance README with cost analysis details
- ✨ feat: add version verification step

## [0.9.0] - 2024-12-07


### 📦 Build System
- bump version to 0.9.0

### 🔄 Other Changes
- ✨ feat: add CLI command aliases and usage info

## [0.8.0] - 2024-12-07


### 📦 Build System
- bump version to 0.8.0

### 🔄 Other Changes
- ✨ feat: validate files before processing in batches

## [0.7.0] - 2024-12-07


### 📦 Build System
- bump version to 0.7.0

### 🔄 Other Changes
- ✨ chore: update dependencies and improve code

## [0.6.0] - 2024-12-07


### 📦 Build System
- bump version to 0.6.0

### 🔄 Other Changes
- ✨ feat: enhance release management with categories
- ✨ feat: stage files and commit improvements

## [0.5.0] - 2024-12-07

- 🔧 refactor: improve settings.py type hints

## [0.4.0] - 2024-12-07

- 🔧 chore: improve configuration setup
- 🔧 chore: update permissions for publishing

## [0.3.0] - 2024-12-06

- 🔧 chore: clean up imports and format code
- ✨ feat: add GitHub release creation functionality
- 🔧 chore: clean up release.py formatting

## [0.2.0] - 2024-12-06

- ✨ feat: enhance release process with changelog
- 📖 docs: update README with badges
- 🔧 chore: update dependencies in pyproject.toml
- ✨ refactor: improve console and AI service handling
- ✨ feat: enhance commit message generation
- ✨ feat: Improve commit message generation
- 📝 refactor: update commit message generation format
- ✨ feat: enhance commit suggestion formatting
- 🔧 chore: refactor imports and improve code structure
- 🔧 chore: update CI configuration and clean tests
- 🔧 chore: upgrade Codecov action to v5
- ✨ feat: enhance CI with Codecov integration
- 🔧 test: improve KeyboardInterrupt handling in main
- 🔧 test: fix KeyboardInterrupt handling in tests
- 🔧 chore: add OpenAI API key to CI workflow
- ✨ feat: update README and clean up code formatting
- fix: resolve CI test failures - Add mock OpenAI API key and fix package installation
- ✨ feat: update commit message format in tests
- ✨ feat: add cost formatting for token usage
- ✨ feat: enhance commit message formatting
- ✨ feat: initial release with core features
- ✨ feat: enhance README to improve clarity
- ✨ feat: update README for enhanced clarity
- ✨ feat: enhance model configuration and costs
- 🔧 fix: handle deleted files during staging
- ✨ feat: enhance git operations and tests
- ✨ feat: enhance commit creation with warnings
- 🚀 feat: add CI/CD workflows and improve CLI
- ✨ feat: enhance commit process with stashing
- 🔧 test: Update test cases for Git functionality
- ✨ feat: Enhance AI service with new features
- 🔧 fix: resolve issues in CLI and settings
- ✨ feat: add .gitignore and enhance README
- git init

All notable changes to CommitLoom will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-03-19

### Added
- Initial release of CommitLoom
- AI-powered commit message generation using OpenAI's models
- Support for multiple OpenAI models (gpt-4o-mini, gpt-4o, etc.)
- Smart batching of changes
- Binary file handling
- Cost estimation and control
- Rich CLI interface
- Comprehensive test suite
- Full type hints support

[0.1.0]: https://github.com/Arakiss/commitloom/releases/tag/v0.1.0 