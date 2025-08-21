"""Tests for the smart grouping module."""

import pytest
from pathlib import Path

from commitloom.core.smart_grouping import SmartGrouper, ChangeType, FileGroup, FileRelationship
from commitloom.core.git import GitFile


class TestSmartGrouper:
    """Test suite for SmartGrouper class."""

    @pytest.fixture
    def grouper(self):
        """Create a SmartGrouper instance for testing."""
        return SmartGrouper()

    @pytest.fixture
    def sample_files(self):
        """Create sample GitFile objects for testing."""
        return [
            GitFile("src/main.py", "M"),
            GitFile("tests/test_main.py", "M"),
            GitFile("src/utils.py", "M"),
            GitFile("docs/README.md", "M"),
            GitFile("package.json", "M"),
            GitFile("src/components/Button.tsx", "M"),
            GitFile("src/components/Button.css", "M"),
            GitFile("tests/test_utils.py", "A"),
            GitFile(".gitignore", "M"),
            GitFile("src/api/user_service.py", "M"),
            GitFile("src/api/user_model.py", "M"),
        ]

    def test_detect_change_types(self, grouper, sample_files):
        """Test that change types are correctly detected."""
        file_types = grouper._detect_change_types(sample_files)

        # Check test files
        assert file_types["tests/test_main.py"] == ChangeType.TEST
        assert file_types["tests/test_utils.py"] == ChangeType.TEST

        # Check documentation files
        assert file_types["docs/README.md"] == ChangeType.DOCS

        # Check config files
        assert file_types["package.json"] == ChangeType.BUILD
        assert file_types[".gitignore"] == ChangeType.CONFIG

        # Check source files (should be REFACTOR by default)
        assert file_types["src/main.py"] == ChangeType.REFACTOR
        assert file_types["src/utils.py"] == ChangeType.REFACTOR

    def test_detect_single_file_type(self, grouper):
        """Test single file type detection."""
        # Test files
        assert grouper._detect_single_file_type("tests/test_something.py") == ChangeType.TEST
        assert grouper._detect_single_file_type("src/__tests__/component.test.js") == ChangeType.TEST
        assert grouper._detect_single_file_type("spec/model.spec.ts") == ChangeType.TEST

        # Documentation files
        assert grouper._detect_single_file_type("README.md") == ChangeType.DOCS
        assert grouper._detect_single_file_type("docs/guide.md") == ChangeType.DOCS
        assert grouper._detect_single_file_type("CHANGELOG.md") == ChangeType.DOCS

        # Config files
        assert grouper._detect_single_file_type("config.yaml") == ChangeType.CONFIG
        assert grouper._detect_single_file_type("Dockerfile") == ChangeType.CONFIG
        assert grouper._detect_single_file_type(".env") == ChangeType.CONFIG

        # Build files
        assert grouper._detect_single_file_type("package.json") == ChangeType.BUILD
        assert grouper._detect_single_file_type("requirements.txt") == ChangeType.BUILD
        assert grouper._detect_single_file_type("pyproject.toml") == ChangeType.BUILD

        # Style files
        assert grouper._detect_single_file_type("styles/main.css") == ChangeType.STYLE
        assert grouper._detect_single_file_type("app.scss") == ChangeType.STYLE

        # Source files with hints
        assert grouper._detect_single_file_type("src/fix_bug.py") == ChangeType.FIX
        assert grouper._detect_single_file_type("feature_login.js") == ChangeType.FEATURE

        # Default case
        assert grouper._detect_single_file_type("random.xyz") == ChangeType.CHORE

    def test_find_relationship_test_implementation_pair(self, grouper):
        """Test detection of test-implementation pairs."""
        file1 = GitFile("src/calculator.py", "M")
        file2 = GitFile("tests/test_calculator.py", "M")

        rel = grouper._find_relationship(file1, file2)
        assert rel is not None
        assert rel.relationship_type == "test-implementation"
        assert rel.strength == 1.0

    def test_find_relationship_same_directory(self, grouper):
        """Test detection of same directory relationship."""
        file1 = GitFile("src/models/user.py", "M")
        file2 = GitFile("src/models/post.py", "M")

        rel = grouper._find_relationship(file1, file2)
        assert rel is not None
        assert rel.relationship_type == "same-directory"
        assert rel.strength == 0.7

    def test_find_relationship_component_pair(self, grouper):
        """Test detection of component pairs (e.g., .tsx and .css with same name)."""
        file1 = GitFile("src/Button.tsx", "M")
        file2 = GitFile("src/Button.css", "M")

        rel = grouper._find_relationship(file1, file2)
        assert rel is not None
        assert rel.relationship_type == "component-pair"
        assert rel.strength == 0.9

    def test_find_relationship_similar_naming(self, grouper):
        """Test detection of similar naming patterns."""
        file1 = GitFile("src/user_service.py", "M")
        file2 = GitFile("src/user_model.py", "M")

        rel = grouper._find_relationship(file1, file2)
        assert rel is not None
        assert rel.relationship_type == "similar-naming"
        assert rel.strength == 0.6

    def test_is_test_implementation_pair(self, grouper):
        """Test the test-implementation pair detection logic."""
        # Valid pairs
        assert grouper._is_test_implementation_pair(Path("src/utils.py"), Path("tests/test_utils.py"))
        assert grouper._is_test_implementation_pair(Path("lib/parser.js"), Path("tests/parser.test.js"))
        assert grouper._is_test_implementation_pair(Path("app/model.ts"), Path("app/model.spec.ts"))

        # Invalid pairs (both tests)
        assert not grouper._is_test_implementation_pair(Path("tests/test_a.py"), Path("tests/test_b.py"))

        # Invalid pairs (both implementations)
        assert not grouper._is_test_implementation_pair(Path("src/a.py"), Path("src/b.py"))

        # Invalid pairs (unrelated names)
        assert not grouper._is_test_implementation_pair(Path("src/utils.py"), Path("tests/test_parser.py"))

    def test_has_similar_naming(self, grouper):
        """Test similar naming detection."""
        # Similar names
        assert grouper._has_similar_naming(Path("user_service.py"), Path("user_model.py"))
        assert grouper._has_similar_naming(Path("auth-handler.js"), Path("auth-validator.js"))

        # Not similar
        assert not grouper._has_similar_naming(Path("user.py"), Path("post.py"))
        assert not grouper._has_similar_naming(Path("main.js"), Path("utils.js"))

    def test_group_by_change_type(self, grouper, sample_files):
        """Test grouping files by change type."""
        file_types = grouper._detect_change_types(sample_files)
        groups = grouper._group_by_change_type(sample_files, file_types)

        # Check that groups are created correctly
        assert ChangeType.TEST in groups
        assert len(groups[ChangeType.TEST]) == 2  # test_main.py and test_utils.py

        assert ChangeType.DOCS in groups
        assert len(groups[ChangeType.DOCS]) == 1  # README.md

        assert ChangeType.BUILD in groups
        assert len(groups[ChangeType.BUILD]) == 1  # package.json

        assert ChangeType.CONFIG in groups
        assert len(groups[ChangeType.CONFIG]) == 1  # .gitignore

    def test_split_large_groups(self, grouper):
        """Test that large groups are split correctly."""
        # Create a large group of files
        large_group = FileGroup(
            files=[GitFile(f"src/file{i}.py", "M") for i in range(12)],
            change_type=ChangeType.REFACTOR,
            reason="Large refactoring",
            confidence=0.8,
        )

        # Split the group
        split_groups = grouper._split_large_groups([large_group])

        # Check that the group was split
        assert len(split_groups) > 1
        # Each group should have at most 5 files
        for group in split_groups:
            assert len(group.files) <= 5
        # Total files should be preserved
        total_files = sum(len(g.files) for g in split_groups)
        assert total_files == 12

    def test_split_small_groups_unchanged(self, grouper):
        """Test that small groups are not split."""
        # Create a small group
        small_group = FileGroup(
            files=[GitFile(f"src/file{i}.py", "M") for i in range(3)],
            change_type=ChangeType.FEATURE,
            reason="Small feature",
            confidence=0.9,
        )

        # Try to split (should remain unchanged)
        result = grouper._split_large_groups([small_group])

        assert len(result) == 1
        assert result[0] == small_group

    def test_analyze_files_empty_input(self, grouper):
        """Test analyzing empty file list."""
        result = grouper.analyze_files([])
        assert result == []

    def test_analyze_files_complete_flow(self, grouper):
        """Test complete analysis flow with sample files."""
        files = [
            GitFile("src/calculator.py", "M"),
            GitFile("tests/test_calculator.py", "M"),
            GitFile("docs/calculator.md", "M"),
            GitFile("src/utils.py", "M"),
            GitFile("package.json", "M"),
        ]

        groups = grouper.analyze_files(files)

        # Should create groups
        assert len(groups) > 0

        # Each group should have files
        for group in groups:
            assert len(group.files) > 0
            assert group.change_type is not None
            assert group.reason != ""
            assert 0 <= group.confidence <= 1

    def test_get_group_summary(self, grouper):
        """Test group summary generation."""
        group = FileGroup(
            files=[GitFile("src/main.py", "M"), GitFile("src/utils.py", "M")],
            change_type=ChangeType.FEATURE,
            reason="New feature implementation",
            confidence=0.85,
            dependencies=["src/config.py", "src/database.py"],
        )

        summary = grouper.get_group_summary(group)

        assert "feature" in summary.lower()
        assert "New feature implementation" in summary
        assert "85" in summary  # 85% confidence
        assert "src/main.py" in summary
        assert "src/utils.py" in summary
        assert "src/config.py" in summary
        assert "src/database.py" in summary

    def test_refine_groups_with_tests(self, grouper):
        """Test that refine_groups properly groups tests with implementations."""
        # Create test and implementation files
        test_files = [
            GitFile("src/calculator.py", "M"),
            GitFile("tests/test_calculator.py", "M"),
        ]

        # Set up relationships
        grouper.relationships = [
            FileRelationship("tests/test_calculator.py", "src/calculator.py", "test-implementation", 1.0)
        ]

        # Create initial groups by type
        groups_by_type = {
            ChangeType.TEST: [test_files[1]],  # test_calculator.py
            ChangeType.REFACTOR: [test_files[0]],  # calculator.py
        }

        refined = grouper._refine_groups(groups_by_type, {})

        # Should create groups that keep test and implementation together
        assert len(refined) > 0

        # Find the test group
        test_groups = [g for g in refined if g.change_type == ChangeType.TEST]
        assert len(test_groups) > 0

    def test_get_language_from_extension(self, grouper):
        """Test language detection from file extension."""
        assert grouper._get_language_from_extension(".py") == "python"
        assert grouper._get_language_from_extension(".js") == "javascript"
        assert grouper._get_language_from_extension(".jsx") == "javascript"
        assert grouper._get_language_from_extension(".ts") == "typescript"
        assert grouper._get_language_from_extension(".tsx") == "typescript"
        assert grouper._get_language_from_extension(".java") == "java"
        assert grouper._get_language_from_extension(".go") == "go"
        assert grouper._get_language_from_extension(".xyz") is None

    def test_import_matches_file(self, grouper):
        """Test import path matching."""
        # Test various import patterns
        assert grouper._import_matches_file("utils", "src/utils.py")
        assert grouper._import_matches_file("models.user", "src/models/user.py")
        assert grouper._import_matches_file("api/handler", "api/handler.js")

        # Non-matching cases
        assert not grouper._import_matches_file("utils", "src/main.py")
        assert not grouper._import_matches_file("models.user", "src/models/post.py")
