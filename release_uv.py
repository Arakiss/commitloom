#!/usr/bin/env python3
"""
Enhanced release automation script for UV-based projects.
Works without Poetry dependency, directly manipulating pyproject.toml.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Literal

VERSION_TYPES = Literal["major", "minor", "patch"]

COMMIT_TYPES = {
    "feat": "✨ Features",
    "fix": "🐛 Bug Fixes",
    "docs": "📚 Documentation",
    "style": "💄 Styling",
    "refactor": "♻️ Code Refactoring",
    "perf": "⚡ Performance Improvements",
    "test": "✅ Tests",
    "build": "📦 Build System",
    "ci": "👷 CI",
    "chore": "🔧 Chores",
}

def run_command(cmd: str | list[str], check: bool = True) -> str:
    """Run a command safely without shell=True.

    Args:
        cmd: Command as list of arguments (preferred) or string (will be parsed)
        check: Whether to raise exception on non-zero exit

    Returns:
        Command output as string
    """
    import shlex
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)

    try:
        result = subprocess.run(cmd, shell=False, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            print(f"❌ Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
            print(f"   Error: {e.stderr}")
            sys.exit(1)
        return ""

def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    with open(pyproject_path) as f:
        content = f.read()

    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match:
        return match.group(1)

    print("❌ Could not find version in pyproject.toml")
    sys.exit(1)

def bump_version(current_version: str, version_type: VERSION_TYPES) -> str:
    """Bump version based on type."""
    parts = current_version.split('.')
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if version_type == "major":
        return f"{major + 1}.0.0"
    elif version_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"

def update_version_in_files(new_version: str) -> None:
    """Update version in pyproject.toml and __init__.py."""
    # Update pyproject.toml
    pyproject_path = Path("pyproject.toml")
    with open(pyproject_path) as f:
        content = f.read()

    content = re.sub(
        r'^version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE
    )

    with open(pyproject_path, 'w') as f:
        f.write(content)

    # Update __init__.py
    init_path = Path("commitloom/__init__.py")
    if init_path.exists():
        with open(init_path) as f:
            content = f.read()

        content = re.sub(
            r'__version__\s*=\s*"[^"]+"',
            f'__version__ = "{new_version}"',
            content
        )

        with open(init_path, 'w') as f:
            f.write(content)

def parse_commit_message(commit: str) -> tuple[str, str]:
    """Parse a commit message into type and description."""
    match = re.match(r'^(\w+)(?:\(.*?\))?: (.+)$', commit.strip())
    if match:
        return match.group(1), match.group(2)
    return "other", commit.strip()

def categorize_commits(commits: list[str]) -> dict[str, list[str]]:
    """Categorize commits by type."""
    categorized: dict[str, list[str]] = {type_key: [] for type_key in COMMIT_TYPES}
    categorized["other"] = []

    for commit in commits:
        if not commit.strip():
            continue
        commit_type, description = parse_commit_message(commit)
        if commit_type in categorized:
            categorized[commit_type].append(description)
        else:
            categorized["other"].append(description)

    return {k: v for k, v in categorized.items() if v}

def update_changelog(version: str) -> None:
    """Update CHANGELOG.md with new version entry."""
    changelog_path = Path("CHANGELOG.md")
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Get commits since last tag
    try:
        last_tag = run_command(["git", "describe", "--tags", "--abbrev=0"], check=True)
    except Exception:
        last_tag = ""

    if last_tag:
        raw_commits = run_command(["git", "log", f"{last_tag}..HEAD", "--pretty=format:%s"]).split('\n')
    else:
        raw_commits = run_command(["git", "log", "--pretty=format:%s"]).split('\n')

    # Categorize commits
    categorized_commits = categorize_commits(raw_commits)

    # Create new changelog entry
    new_entry = [f"## [{version}] - {current_date}\n"]

    for commit_type, emoji_title in COMMIT_TYPES.items():
        if commit_type in categorized_commits and categorized_commits[commit_type]:
            new_entry.append(f"\n### {emoji_title}")
            for change in categorized_commits[commit_type]:
                new_entry.append(f"- {change}")

    if "other" in categorized_commits and categorized_commits["other"]:
        new_entry.append("\n### 🔄 Other Changes")
        for change in categorized_commits["other"]:
            new_entry.append(f"- {change}")

    new_entry.append("\n")
    new_entry_text = "\n".join(new_entry)

    # Read existing changelog
    if changelog_path.exists():
        with open(changelog_path) as f:
            content = f.read()
    else:
        content = "# Changelog\n\n"

    # Add new entry after header
    updated_content = re.sub(
        r"(# Changelog\n\n)",
        f"\\1{new_entry_text}",
        content
    )

    with open(changelog_path, "w") as f:
        f.write(updated_content)

def create_version_commits(new_version: str) -> None:
    """Create granular commits for version changes."""
    # Update version files
    update_version_in_files(new_version)

    # Commit version bump
    run_command(["git", "add", "pyproject.toml", "commitloom/__init__.py"])
    run_command(["git", "commit", "-m", f"build: bump version to {new_version}"])
    print("✅ Committed version bump")

    # Update changelog
    update_changelog(new_version)
    run_command(["git", "add", "CHANGELOG.md"])
    run_command(["git", "commit", "-m", f"docs: update changelog for {new_version}"])
    print("✅ Committed changelog update")

def get_changelog_entry(version: str) -> str:
    """Extract changelog entry for a specific version."""
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        return ""

    with open(changelog_path) as f:
        content = f.read()

    # Extract the entry for this version
    pattern = rf"## \[{re.escape(version)}\].*?\n\n(.*?)(?=\n## \[|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def create_github_release(version: str, dry_run: bool = False) -> None:
    """Create GitHub release with tag."""
    tag = f"v{version}"

    if dry_run:
        print(f"[DRY RUN] Would create tag: {tag}")
        return

    # Create and push tag
    changelog_content = get_changelog_entry(version)
    tag_message = f"Release {tag}\n\n{changelog_content}" if changelog_content else f"Release {tag}"

    run_command(["git", "tag", "-a", tag, "-m", tag_message])
    print(f"✅ Created tag {tag}")

    # Push commits and tag
    run_command(["git", "push", "origin", "main"])
    print("✅ Pushed commits to main")

    run_command(["git", "push", "origin", "--tags"])
    print("✅ Pushed tag to origin")

    # Create GitHub Release via API
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        try:
            # Get repository info from git remote
            remote_url = run_command(["git", "remote", "get-url", "origin"])
            repo_match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote_url)
            if not repo_match:
                print("⚠️ Could not parse GitHub repository from remote URL")
                return

            repo_path = repo_match.group(1)

            # Prepare release data
            release_data = {
                "tag_name": tag,
                "name": f"Release {tag}",
                "body": changelog_content,
                "draft": False,
                "prerelease": False
            }

            # Create release via GitHub API
            url = f"https://api.github.com/repos/{repo_path}/releases"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            request = urllib.request.Request(
                url,
                data=json.dumps(release_data).encode(),
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(request) as response:
                if response.status == 201:
                    print("✅ Created GitHub Release")
                else:
                    print(f"⚠️ GitHub Release creation returned status {response.status}")

        except Exception as e:
            print(f"⚠️ Could not create GitHub Release: {str(e)}")
            print("   You may need to set the GITHUB_TOKEN environment variable")
    else:
        print("ℹ️ GITHUB_TOKEN not found. Skipping GitHub Release creation")
        print("   Set GITHUB_TOKEN to enable automatic GitHub Release creation")

def check_prerequisites() -> None:
    """Check that we can proceed with release."""
    # Ensure we're on main branch
    current_branch = run_command(["git", "branch", "--show-current"])
    if current_branch != "main":
        print(f"❌ Must be on main branch to release (currently on {current_branch})")
        sys.exit(1)

    # Ensure working directory is clean
    if run_command(["git", "status", "--porcelain"]):
        print("❌ Working directory is not clean. Commit or stash changes first.")
        sys.exit(1)

    # Ensure git user is configured
    user_name = run_command(["git", "config", "user.name"], check=False)
    user_email = run_command(["git", "config", "user.email"], check=False)
    if not user_name or not user_email:
        print("❌ Git user not configured. Please configure git user:")
        print("   git config user.name 'Your Name'")
        print("   git config user.email 'your.email@example.com'")
        sys.exit(1)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enhanced release automation for UV-based projects"
    )
    parser.add_argument(
        "version_type",
        choices=["major", "minor", "patch"],
        help="Type of version bump"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Skip GitHub release creation"
    )

    args = parser.parse_args()

    print("🚀 Starting release process...")

    # Check prerequisites
    check_prerequisites()

    # Get current version and calculate new version
    old_version = get_current_version()
    new_version = bump_version(old_version, args.version_type)

    print(f"📦 Version bump: {old_version} → {new_version}")

    if args.dry_run:
        print("\n[DRY RUN] Would perform the following actions:")
        print(f"  1. Update version to {new_version} in pyproject.toml and __init__.py")
        print(f"  2. Create commit: 'build: bump version to {new_version}'")
        print(f"  3. Update CHANGELOG.md with new entries")
        print(f"  4. Create commit: 'docs: update changelog for {new_version}'")
        print(f"  5. Create tag: v{new_version}")
        if not args.skip_github:
            print(f"  6. Push to origin and create GitHub Release")
    else:
        # Create version commits
        create_version_commits(new_version)

        # Create release
        if not args.skip_github:
            create_github_release(new_version, dry_run=args.dry_run)
        else:
            # Just create local tag
            tag = f"v{new_version}"
            changelog_content = get_changelog_entry(new_version)
            tag_message = f"Release {tag}\n\n{changelog_content}" if changelog_content else f"Release {tag}"
            run_command(["git", "tag", "-a", tag, "-m", tag_message])
            print(f"✅ Created tag {tag}")
            print("ℹ️ Skipped GitHub release (use --skip-github=false to enable)")

        print(f"\n🎉 Release {new_version} is ready!")
        print("\nNext steps:")
        if args.skip_github:
            print("  1. Push changes: git push origin main --tags")
            print("  2. Create GitHub release manually if needed")
        print("  3. Publish to PyPI: uv publish (or your CI/CD will do this)")

if __name__ == "__main__":
    main()