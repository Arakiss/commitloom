# Changelog

## [1.6.4] - 2025-10-01


### ✨ Features
- add enhanced release script for UV-based workflow

### 🐛 Bug Fixes
- critical security and encoding vulnerabilities
- disable all formatting-related linter rules
- handle non-UTF-8 file encodings in git operations

### 📚 Documentation
- update changelog for 1.6.3

### ✅ Tests
- fix tests to work with new encoding-safe subprocess calls

### 📦 Build System
- bump version to 1.6.4
- bump version to 1.6.3

### 👷 CI
- disable code formatting check in CI

### 🔧 Chores
- update uv.lock file

## [1.6.3] - 2025-09-23

### 🐛 Bug Fixes
- **Fixed encoding issues with non-UTF-8 files**: CommitLoom now properly handles files with different character encodings
  - Removed automatic UTF-8 decoding assumptions in subprocess calls
  - Added explicit encoding handling with fallback to error replacement
  - Fixed crashes when processing Lua files or legacy files with special characters
  - All git operations now handle encoding errors gracefully

### 🔧 Chores
- Synchronized version between pyproject.toml and __init__.py

## [1.6.2] - 2025-08-21

### 🐛 Bug Fixes
- **Fixed duplicate debug logging**: Removed redundant `setup_logging()` calls that caused "Debug mode enabled" to appear twice
- **Cleaner CLI output**: Debug mode message now appears only once when using `-d/--debug` flag

### 🚀 Improvements
- Streamlined logging initialization process
- Better separation of concerns in CLI setup
- Maintained all existing functionality with cleaner output

## [1.6.1] - 2025-08-21

### 🐛 Bug Fixes
- **Fixed duplicate logging**: Removed redundant logger calls causing messages to appear 2-3 times
- **Fixed metrics JSON parsing**: Better handling of corrupted or missing metrics files
- **Fixed MyPy type errors**: Added proper type checks for Response objects and type hints
- **Reduced output verbosity**: Simplified smart grouping output to be more concise

### 🚀 Improvements
- Cleaner console output without debug noise
- Silent handling of first-run file creation
- More concise smart grouping summaries
- Better error handling for API responses

## [1.6.0] - 2025-08-21

### ✨ Features
- **Smart File Grouping**: Intelligent semantic analysis for grouping related files in commits
  - Detects relationships between test files and their implementations
  - Identifies component pairs (e.g., .tsx and .css files)
  - Groups files by change type (feature, fix, test, docs, etc.)
  - Analyzes file dependencies and imports
  - CLI option `-s/--smart-grouping` (enabled by default)

### 🚀 Improvements
- **Migration from Poetry to UV**: Complete build system overhaul
  - 10-100x faster dependency installation
  - Simplified configuration using PEP 621 standard
  - Improved CI/CD pipeline performance
  - Better cache management
  - Updated all GitHub Actions workflows

### 📦 Build System
- Migrated from Poetry to UV package manager
- Updated pyproject.toml to PEP 621 format
- Added Dockerfile with UV support
- Updated CI/CD workflows for UV compatibility

### 📚 Documentation
- Updated CONTRIBUTING.md with UV instructions
- Added comprehensive tests for smart grouping feature
- Improved code coverage to 74%

### 🧪 Tests
- Added comprehensive test suite for smart grouping
- All 133 tests passing
- Code coverage increased from 68% to 74%

## [1.5.6] - 2025-08-21

### ✨ Features
- polish commit flow and AI service

### 🐛 Bug Fixes
- explicit response check in API retries

### 🧪 Tests
- improve coverage for new features

## [1.5.5] - 2025-06-15


### 🐛 Bug Fixes
- add debug option to commit command and improve CLI argument parsing
- update poetry.lock file
- sync version in __init__.py and improve release script

### 📦 Build System
- bump version to 1.5.5
- trigger release workflow for version 1.5.4
- republish version 1.5.4 to PyPI

### 🔧 Chores
- cleanup trigger file

## [1.5.4] - 2025-06-15


### ✨ Features
- suggest new branch for large commits

### 🐛 Bug Fixes
- remove debug prints

### 📦 Build System
- bump version to 1.5.4

## [1.5.3] - 2025-06-13

### ✨ Features
- commit batching with smart detection for better project organization
- automatic warning system for complex commits
- multi-commit workflow with descriptive messages
- improved handling of large changesets

### 🐛 Bug Fixes
- batch mode file path handling

### 🔧 Other Changes
- version sync and refactors

## [1.5.2] - 2025-06-11

### ✨ Features
- add --combine flag to force single commit for all changes

## [1.5.1] - 2025-06-10

### 🐛 Bug Fixes
- resolve subprocess text encoding issue
- improve non-text file handling

## [1.5.0] - 2025-06-10

### ✨ Features
- automatic commit splitting for multiple unrelated changes
- smart change detection based on directories
- batch processing with user confirmation
- improved git operations and file handling

### 🐛 Bug Fixes
- comprehensive test suite for new batching features
- edge case handling for various file types

## [1.4.9] - 2025-06-10

### 🐛 Bug Fixes
- handle binary and special files properly

### ✨ Features
- improve git diff handling
- skip binary files automatically
- add comprehensive test coverage

## [1.4.8] - 2025-06-01

### 🐛 Bug Fixes
- improve JSON validation in AI responses
- add fallback for malformed commit messages
- enhance error handling and logging

## [1.4.7] - 2025-05-31

### ✨ Features
- add comprehensive test suite with 90%+ coverage
- improve error handling and edge cases
- add proper mocking for external dependencies

### 🐛 Bug Fixes
- fix token estimation accuracy
- improve cost calculation precision

## [1.4.6] - 2025-05-29

### ✨ Features
- add metrics tracking and usage statistics
- new `stats` command to view AI usage metrics
- track token usage, costs, and model performance
- persistent storage of usage data

## [1.4.5] - 2025-05-29

### ✨ Features
- improve cost estimation accuracy
- add model pricing information
- better token usage reporting

## [1.4.4] - 2025-05-29

### ✨ Features
- add -y flag to skip all confirmations
- improve UX for CI/CD pipelines
- add --yes as alias for -y flag

## [1.4.3] - 2025-05-28

### 🐛 Bug Fixes
- fix import error in main module
- ensure all modules are properly exported

## [1.4.2] - 2025-05-28

### 🐛 Bug Fixes
- fix version management between pyproject.toml and __init__.py
- improve release script for better version handling

## [1.4.1] - 2025-05-28

### ✨ Features
- add token usage and cost estimation
- display AI model information
- show estimated costs before committing
- add -d/--debug flag for verbose output

## [1.4.0] - 2025-05-28

### ✨ Features
- configurable AI models via settings file
- cost tracking for different models
- improved token estimation
- customizable token limits and thresholds

### 🐛 Bug Fixes
- better error handling for API failures
- improved configuration validation

## [1.3.0] - 2025-05-27

### ✨ Features
- automatic detection of required API keys
- smart warning system for large diffs
- enhanced cost and token estimation
- better handling of binary files

### 🐛 Bug Fixes
- improved error messages for missing API keys
- better handling of edge cases in git operations

## [1.2.0] - 2025-05-26

### ✨ Features
- add retry logic with exponential backoff for API calls
- improve error handling and user feedback
- add comprehensive logging system

### 🐛 Bug Fixes
- handle API timeout errors gracefully
- fix issues with special characters in commit messages

## [1.1.0] - 2025-05-25

### ✨ Features
- add --version flag to display version information
- improve CLI help documentation
- add contribution guidelines

### 📚 Documentation
- add comprehensive README
- improve installation instructions
- add usage examples

## [1.0.0] - 2025-05-24

### 🎉 Initial Release
- AI-powered commit message generation
- Support for OpenAI and Anthropic Claude APIs
- Interactive CLI with rich formatting
- Conventional commits format support
- Comprehensive git operations handling