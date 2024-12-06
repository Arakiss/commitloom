#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

VERSION_TYPES = Literal["major", "minor", "patch"]

def run_command(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True).decode().strip()

def get_current_version() -> str:
    return run_command("poetry version -s")

def bump_version(version_type: VERSION_TYPES) -> str:
    output = run_command(f"poetry version {version_type}")
    return output.split(" ")[-1]

def update_changelog(version: str) -> None:
    changelog_path = Path("CHANGELOG.md")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    with open(changelog_path, "r") as f:
        content = f.read()
    
    # Get commits since last release
    last_tag = run_command("git describe --tags --abbrev=0 || echo ''")
    if last_tag:
        commits = run_command(f"git log {last_tag}..HEAD --pretty=format:'- %s'")
    else:
        commits = run_command("git log --pretty=format:'- %s'")
    
    # Create new changelog entry
    new_entry = f"## [{version}] - {current_date}\n\n{commits}\n\n"
    
    # Add new entry after the header
    updated_content = re.sub(
        r"(# Changelog\n\n)",
        f"\\1{new_entry}",
        content
    )
    
    with open(changelog_path, "w") as f:
        f.write(updated_content)

def create_github_release(version: str, dry_run: bool = False) -> None:
    tag = f"v{version}"
    if not dry_run:
        # Create and push tag
        run_command(f'git tag -a {tag} -m "Release {tag}"')
        run_command("git push origin main --tags")
        print(f"✅ Created and pushed tag {tag}")
    else:
        print(f"Would create tag: {tag}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Release automation script")
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
    
    args = parser.parse_args()
    
    # Ensure we're on main branch
    current_branch = run_command("git branch --show-current")
    if current_branch != "main":
        print("❌ Must be on main branch to release")
        exit(1)
    
    # Ensure working directory is clean
    if run_command("git status --porcelain"):
        print("❌ Working directory is not clean")
        exit(1)
    
    # Get current version and bump it
    old_version = get_current_version()
    new_version = bump_version(args.version_type)
    print(f"📦 Bumping version: {old_version} -> {new_version}")
    
    if not args.dry_run:
        # Update changelog
        update_changelog(new_version)
        print("📝 Updated CHANGELOG.md")
        
        # Commit changes
        run_command('git add CHANGELOG.md pyproject.toml')
        run_command(f'git commit -m "chore: release {new_version}"')
        run_command("git push origin main")
        print("✅ Committed and pushed changes")
        
        # Create GitHub release
        create_github_release(new_version)
        print(f"🎉 Release {new_version} is ready!")
    else:
        print("Dry run completed. No changes made.")

if __name__ == "__main__":
    main() 