"""Smart grouping module for intelligent file batching based on semantic relationships."""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .git import GitFile


class ChangeType(Enum):
    """Types of changes detected in files."""

    FEATURE = "feature"
    FIX = "fix"
    TEST = "test"
    DOCS = "docs"
    REFACTOR = "refactor"
    STYLE = "style"
    CHORE = "chore"
    CONFIG = "config"
    BUILD = "build"
    PERF = "perf"


@dataclass
class FileRelationship:
    """Represents a relationship between two files."""

    file1: str
    file2: str
    relationship_type: str
    strength: float  # 0.0 to 1.0


@dataclass
class FileGroup:
    """A group of files that should be committed together."""

    files: list[GitFile]
    change_type: ChangeType
    reason: str
    confidence: float  # 0.0 to 1.0
    dependencies: list[str] = field(default_factory=list)


class SmartGrouper:
    """Intelligent file grouping based on semantic analysis."""

    MAX_FILE_SIZE_FOR_ANALYSIS = 200_000

    # Patterns for detecting change types
    CHANGE_TYPE_PATTERNS = {
        ChangeType.TEST: [
            r"test[s]?/",
            r"test_.*\.py$",
            r".*_test\.py$",
            r".*\.test\.[jt]sx?$",
            r".*\.spec\.[jt]sx?$",
            r"__tests__/",
        ],
        ChangeType.DOCS: [
            r"\.md$",
            r"\.rst$",
            r"docs?/",
            r"README",
            r"CHANGELOG",
            r"LICENSE",
            r"(?<!requirements)\.txt$",  # Don't match requirements.txt
        ],
        ChangeType.BUILD: [
            r"package\.json$",
            r"package-lock\.json$",
            r"requirements\.txt$",
            r"pyproject\.toml$",
            r"setup\.py$",
            r"Makefile$",
            r"CMakeLists\.txt$",
            r"\.gradle$",
            r"pom\.xml$",
        ],
        ChangeType.CONFIG: [
            r"\.yaml$",
            r"\.yml$",
            r"\.toml$",
            r"\.ini$",
            r"\.cfg$",
            r"\.conf$",
            r"\.env",
            r"Dockerfile",
            r"docker-compose",
            r"\.gitignore$",
            r"\.json$",  # Move .json$ to the end to let package.json match BUILD first
        ],
        ChangeType.STYLE: [
            r"\.css$",
            r"\.scss$",
            r"\.sass$",
            r"\.less$",
            r"\.styl$",
        ],
    }

    CHANGE_TYPE_PRIORITY = {
        ChangeType.TEST: 0,
        ChangeType.FEATURE: 1,
        ChangeType.FIX: 1,
        ChangeType.PERF: 1,
        ChangeType.REFACTOR: 2,
        ChangeType.DOCS: 3,
        ChangeType.STYLE: 3,
        ChangeType.BUILD: 4,
        ChangeType.CONFIG: 4,
        ChangeType.CHORE: 5,
    }

    # Import patterns for various languages
    IMPORT_PATTERNS = {
        "python": [
            r"from\s+([.\w]+)\s+import",
            r"import\s+([.\w]+)",
            r"from\s+\.+(\w+)",  # Relative imports
        ],
        "javascript": [
            r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
            r"require\(['\"]([^'\"]+)['\"]\)",
            r"from\s+['\"]([^'\"]+)['\"]",
        ],
        "typescript": [
            r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
            r"require\(['\"]([^'\"]+)['\"]\)",
            r"from\s+['\"]([^'\"]+)['\"]",
        ],
        "java": [
            r"import\s+([\w.]+);",
        ],
        "go": [
            r"import\s+\"([^\"]+)\"",
            r"import\s+\([^)]+\)",
        ],
    }

    def __init__(self):
        """Initialize the smart grouper."""
        self.relationships: list[FileRelationship] = []
        self.file_contents_cache: dict[str, str] = {}

    def analyze_files(self, files: list[GitFile]) -> list[FileGroup]:
        """
        Analyze files and create intelligent groups.

        Args:
            files: List of changed files to analyze

        Returns:
            List of file groups for committing
        """
        if not files:
            return []

        self.file_contents_cache.clear()

        # Step 1: Detect change types for each file
        file_types = self._detect_change_types(files)

        # Step 2: Analyze relationships between files
        self.relationships = self._analyze_relationships(files)

        # Step 3: Detect dependencies
        dependencies = self._detect_dependencies(files)

        # Step 4: Create initial groups by change type
        groups_by_type = self._group_by_change_type(files, file_types)

        # Step 5: Refine groups based on relationships and dependencies
        refined_groups = self._refine_groups(groups_by_type, dependencies)

        # Step 6: Split large groups if necessary
        final_groups = self._split_large_groups(refined_groups)

        self._enrich_groups_with_dependencies(final_groups, dependencies)

        return final_groups

    def _detect_change_types(self, files: list[GitFile]) -> dict[str, ChangeType]:
        """
        Detect the type of change for each file.

        Args:
            files: List of files to analyze

        Returns:
            Dictionary mapping file paths to change types
        """
        file_types = {}

        for file in files:
            change_type = self._detect_single_file_type(file.path)
            file_types[file.path] = change_type

        return file_types

    def _detect_single_file_type(self, file_path: str) -> ChangeType:
        """
        Detect the change type for a single file.

        Args:
            file_path: Path to the file

        Returns:
            The detected change type
        """
        # Check against patterns
        for change_type, patterns in self.CHANGE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if self._matches_pattern(pattern, file_path):
                    return change_type

        # Check file extension for common source files
        ext = Path(file_path).suffix.lower()
        source_extensions = {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
            ".go",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".scala",
            ".cs",
            ".vb",
            ".f90",
        }

        if ext in source_extensions:
            # Try to determine if it's a feature or fix based on path
            if "fix" in file_path.lower() or "bug" in file_path.lower():
                return ChangeType.FIX
            elif "feature" in file_path.lower() or "feat" in file_path.lower():
                return ChangeType.FEATURE
            else:
                # Default to refactor for source files
                return ChangeType.REFACTOR

        # Default to chore
        return ChangeType.CHORE

    def _analyze_relationships(self, files: list[GitFile]) -> list[FileRelationship]:
        """
        Analyze relationships between files.

        Args:
            files: List of files to analyze

        Returns:
            List of file relationships
        """
        relationships = []

        for i, file1 in enumerate(files):
            for file2 in files[i + 1 :]:
                # Check for various relationship types
                rel = self._find_relationship(file1, file2)
                if rel:
                    relationships.append(rel)

        return relationships

    def _find_relationship(self, file1: GitFile, file2: GitFile) -> FileRelationship | None:
        """
        Find relationship between two files.

        Args:
            file1: First file
            file2: Second file

        Returns:
            FileRelationship if found, None otherwise
        """
        path1 = Path(file1.path)
        path2 = Path(file2.path)

        # Test and implementation relationship
        if self._is_test_implementation_pair(path1, path2):
            return FileRelationship(file1.path, file2.path, "test-implementation", strength=1.0)

        # Component relationship (e.g., .tsx and .css files with same name)
        # Check this before same-directory to give it priority
        if path1.stem == path2.stem and path1.parent == path2.parent and path1.suffix != path2.suffix:
            # Check if they're likely component pairs (different extensions but same name)
            component_extensions = {
                ".tsx",
                ".jsx",
                ".ts",
                ".js",
                ".css",
                ".scss",
                ".sass",
                ".less",
                ".module.css",
            }
            if path1.suffix in component_extensions or path2.suffix in component_extensions:
                return FileRelationship(file1.path, file2.path, "component-pair", strength=0.9)

        # Similar naming (check before same directory)
        if self._has_similar_naming(path1, path2):
            return FileRelationship(file1.path, file2.path, "similar-naming", strength=0.6)

        # Same directory relationship
        if path1.parent == path2.parent:
            return FileRelationship(file1.path, file2.path, "same-directory", strength=0.7)

        # Parent-child directory relationship
        if self._is_parent_child_directory(path1, path2):
            return FileRelationship(file1.path, file2.path, "directory-hierarchy", strength=0.5)

        # Similar naming (e.g., user_service.py and user_model.py)
        if self._has_similar_naming(path1, path2):
            return FileRelationship(file1.path, file2.path, "similar-naming", strength=0.6)

        return None

    def _is_test_implementation_pair(self, path1: Path, path2: Path) -> bool:
        """Check if two files form a test-implementation pair."""
        # Check if one is test and other is not
        is_test1 = self._is_test_file(str(path1))
        is_test2 = self._is_test_file(str(path2))

        if is_test1 == is_test2:
            return False  # Both test or both not test

        # Check if they have similar names
        test_path = path1 if is_test1 else path2
        impl_path = path2 if is_test1 else path1

        # Remove test markers from filename
        test_name = test_path.stem
        test_name = re.sub(r"(test_|_test|\.test|\.spec)", "", test_name)

        impl_name = impl_path.stem

        return test_name == impl_name or test_name in impl_name or impl_name in test_name

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file."""
        for pattern in self.CHANGE_TYPE_PATTERNS[ChangeType.TEST]:
            if self._matches_pattern(pattern, file_path):
                return True
        return False

    def _is_parent_child_directory(self, path1: Path, path2: Path) -> bool:
        """Check if paths are in parent-child directory relationship."""
        try:
            return path1.parent in path2.parents or path2.parent in path1.parents
        except ValueError:
            return False

    def _has_similar_naming(self, path1: Path, path2: Path) -> bool:
        """Check if two files have similar naming patterns."""
        # Extract base names without extensions
        name1 = path1.stem.lower()
        name2 = path2.stem.lower()

        # Split by common separators
        parts1 = [p for p in re.split(r"[_\-.]", name1) if p]  # Filter empty parts
        parts2 = [p for p in re.split(r"[_\-.]", name2) if p]  # Filter empty parts

        # Check for common parts
        common_parts = set(parts1) & set(parts2)
        if not common_parts:
            return False

        # Calculate similarity ratio
        total_parts = len(set(parts1) | set(parts2))
        common_ratio = len(common_parts) / total_parts if total_parts > 0 else 0

        # More lenient threshold for similar naming
        return common_ratio >= 0.3  # Changed from 0.5 to 0.3

    def _detect_dependencies(self, files: list[GitFile]) -> dict[str, list[str]]:
        """
        Detect dependencies between files based on imports.

        Args:
            files: List of files to analyze

        Returns:
            Dictionary mapping file paths to their dependencies
        """
        dependencies = defaultdict(list)

        for file in files:
            if file.is_binary:
                continue

            ext = Path(file.path).suffix.lower()
            language = self._get_language_from_extension(ext)

            if not language or language not in self.IMPORT_PATTERNS:
                continue

            raw_imports = self._extract_imports(file.path, language)

            if not raw_imports:
                continue

            normalized_imports = [self._normalize_import_path(imp) for imp in raw_imports]

            matched_dependencies: set[str] = set()
            for imp in normalized_imports:
                if not imp:
                    continue
                for other_file in files:
                    if other_file.path == file.path:
                        continue
                    if self._import_matches_file(imp, other_file.path):
                        matched_dependencies.add(other_file.path)

            if matched_dependencies:
                dependencies[file.path].extend(sorted(matched_dependencies))

        return {path: deps for path, deps in dependencies.items() if deps}

    def _get_language_from_extension(self, ext: str) -> str | None:
        """Get programming language from file extension."""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
        }
        return extension_map.get(ext)

    def _extract_imports(self, file_path: str, language: str) -> list[str]:
        """
        Extract import statements from a file.

        Args:
            file_path: Path to the file
            language: Programming language

        Returns:
            List of imported modules/files
        """
        imports: list[str] = []

        try:
            content = self._get_file_contents(file_path)
        except OSError:
            return []

        if not content:
            return []

        for pattern in self.IMPORT_PATTERNS.get(language, []):
            for match in re.findall(pattern, content):
                if isinstance(match, tuple):
                    imports.extend([m for m in match if m])
                elif match:
                    imports.append(match)

        return imports

    def _import_matches_file(self, import_path: str, file_path: str) -> bool:
        """Check if an import path matches a file path."""
        # Normalize paths
        import_parts = import_path.replace(".", "/").split("/")
        file_path_obj = Path(file_path)

        # Remove file extension for matching
        file_stem = file_path_obj.stem
        file_parts = list(file_path_obj.parent.parts) + [file_stem]

        # Check if import parts match any subsequence in file parts
        import_str = "/".join(import_parts)
        file_str = "/".join(file_parts)

        # Check for exact match or if import is contained in file path
        if import_str in file_str:
            return True

        # Check if the last part of import matches the file name
        if import_parts and import_parts[-1] == file_stem:
            return True

        return False

    def _group_by_change_type(
        self, files: list[GitFile], file_types: dict[str, ChangeType]
    ) -> dict[ChangeType, list[GitFile]]:
        """
        Group files by their change type.

        Args:
            files: List of files
            file_types: Mapping of file paths to change types

        Returns:
            Dictionary mapping change types to lists of files
        """
        groups = defaultdict(list)

        for file in files:
            change_type = file_types.get(file.path, ChangeType.CHORE)
            groups[change_type].append(file)

        return dict(groups)

    def _refine_groups(
        self, groups_by_type: dict[ChangeType, list[GitFile]], dependencies: dict[str, list[str]]
    ) -> list[FileGroup]:
        """
        Refine groups based on relationships and dependencies.

        Args:
            groups_by_type: Initial groups by change type
            dependencies: File dependencies

        Returns:
            Refined list of file groups
        """
        refined_groups = []
        assigned_paths: set[str] = set()

        file_lookup = {file.path: file for file_list in groups_by_type.values() for file in file_list}

        original_order = {change_type: index for index, change_type in enumerate(groups_by_type.keys())}
        sorted_change_types = sorted(
            groups_by_type.keys(),
            key=lambda ct: (self._change_type_priority(ct), original_order.get(ct, 0)),
        )

        for change_type in sorted_change_types:
            files = groups_by_type.get(change_type, [])
            if not files:
                continue

            available_files = [file for file in files if file.path not in assigned_paths]

            if not available_files:
                continue

            if change_type == ChangeType.TEST:
                test_groups = self._group_tests_with_implementations(
                    available_files, file_lookup, dependencies, assigned_paths
                )
                refined_groups.extend(test_groups)
            elif len(available_files) <= 3:
                group = FileGroup(
                    files=available_files,
                    change_type=change_type,
                    reason=f"All {change_type.value} changes",
                    confidence=0.8,
                )
                assigned_paths.update(file.path for file in available_files)
                refined_groups.append(group)
            else:
                subgroups = self._split_by_module(available_files, change_type)
                for subgroup in subgroups:
                    assigned_paths.update(file.path for file in subgroup.files)
                refined_groups.extend(subgroups)

        return refined_groups

    def _group_tests_with_implementations(
        self,
        test_files: list[GitFile],
        file_lookup: dict[str, GitFile],
        dependencies: dict[str, list[str]],
        assigned_paths: set[str],
    ) -> list[FileGroup]:
        """Group test files with their corresponding implementations."""
        groups: list[FileGroup] = []
        test_paths = {file.path for file in test_files}

        implementation_to_tests: dict[str, set[str]] = defaultdict(set)
        for rel in self.relationships:
            if rel.relationship_type != "test-implementation":
                continue

            test_path, impl_path = self._identify_test_and_implementation(rel.file1, rel.file2)
            if not test_path or not impl_path:
                continue

            if test_path not in test_paths:
                continue

            if impl_path not in file_lookup:
                continue

            implementation_to_tests[impl_path].add(test_path)

        for impl_path, tests in implementation_to_tests.items():
            if impl_path in assigned_paths:
                continue

            candidate_tests = [test for test in sorted(tests) if test not in assigned_paths]
            if not candidate_tests:
                continue

            group_paths: set[str] = {impl_path}
            group_paths.update(candidate_tests)

            group_files = [file_lookup[path] for path in sorted(group_paths)]
            if not group_files:
                continue

            assigned_paths.update(group_paths)

            reason = "Test with linked implementation" if len(candidate_tests) == 1 else "Test suite with implementation"
            confidence = 0.9 if len(candidate_tests) == 1 else 0.95

            groups.append(
                FileGroup(
                    files=group_files,
                    change_type=ChangeType.TEST,
                    reason=reason,
                    confidence=confidence,
                )
            )

        for test_file in test_files:
            if test_file.path in assigned_paths:
                continue

            related_paths: set[str] = {test_file.path}
            for dependency in dependencies.get(test_file.path, []):
                if dependency in assigned_paths:
                    continue
                if dependency in file_lookup:
                    related_paths.add(dependency)

            group_files = [file_lookup[path] for path in sorted(related_paths) if path in file_lookup]
            if not group_files:
                continue

            assigned_paths.update(related_paths)

            reason = "Isolated test change" if len(group_files) == 1 else "Test with supporting files"
            confidence = 0.7 if len(group_files) == 1 else 0.78

            groups.append(
                FileGroup(
                    files=group_files,
                    change_type=ChangeType.TEST,
                    reason=reason,
                    confidence=confidence,
                )
            )

        return groups

    def _split_by_module(self, files: list[GitFile], change_type: ChangeType) -> list[FileGroup]:
        """Split files into groups by module or directory."""
        module_groups = defaultdict(list)

        for file in files:
            # Group by top-level directory or module
            parts = Path(file.path).parts
            if len(parts) > 1:
                module = parts[0]
            else:
                module = "root"
            module_groups[module].append(file)

        groups = []
        for module, module_files in module_groups.items():
            group = FileGroup(
                files=module_files,
                change_type=change_type,
                reason=f"{change_type.value} changes in {module} module",
                confidence=0.7,
            )
            groups.append(group)

        return groups

    def _split_large_groups(self, groups: list[FileGroup]) -> list[FileGroup]:
        """
        Split large groups into smaller, manageable chunks.

        Args:
            groups: List of file groups

        Returns:
            List of file groups with large groups split
        """
        final_groups = []
        max_files_per_group = 5  # Configurable threshold

        for group in groups:
            if len(group.files) <= max_files_per_group:
                final_groups.append(group)
            else:
                # Split the group
                for i in range(0, len(group.files), max_files_per_group):
                    chunk = group.files[i : i + max_files_per_group]
                    split_group = FileGroup(
                        files=chunk,
                        change_type=group.change_type,
                        reason=f"{group.reason} (part {i // max_files_per_group + 1})",
                        confidence=group.confidence * 0.9,  # Slightly lower confidence for splits
                    )
                    final_groups.append(split_group)

        return final_groups

    def get_group_summary(self, group: FileGroup) -> str:
        """
        Get a human-readable summary of a file group.

        Args:
            group: The file group

        Returns:
            Summary string
        """
        file_list = ", ".join(f.path for f in group.files)
        return (
            f"Group: {group.change_type.value}\n"
            f"Reason: {group.reason}\n"
            f"Confidence: {group.confidence:.1%}\n"
            f"Files: {file_list}\n"
            f"Dependencies: {', '.join(group.dependencies) if group.dependencies else 'None'}"
        )

    @classmethod
    def _change_type_priority(cls, change_type: ChangeType) -> int:
        """Get processing priority for a change type."""
        return cls.CHANGE_TYPE_PRIORITY.get(change_type, 5)

    def _identify_test_and_implementation(self, path1: str, path2: str) -> tuple[str | None, str | None]:
        """Identify which path corresponds to the test and which to the implementation."""
        is_test1 = self._is_test_file(path1)
        is_test2 = self._is_test_file(path2)

        if is_test1 and not is_test2:
            return path1, path2
        if is_test2 and not is_test1:
            return path2, path1

        return None, None

    def _normalize_import_path(self, import_path: str) -> str:
        """Normalize import paths for comparison."""
        normalized = import_path.strip().strip("\"'")
        normalized = normalized.lstrip("./")
        return normalized

    def _get_file_contents(self, file_path: str) -> str:
        """Retrieve file contents with caching and safety checks."""
        if file_path in self.file_contents_cache:
            return self.file_contents_cache[file_path]

        path = Path(file_path)
        try:
            if not path.exists() or path.is_dir():
                self.file_contents_cache[file_path] = ""
                return ""

            if path.stat().st_size > self.MAX_FILE_SIZE_FOR_ANALYSIS:
                self.file_contents_cache[file_path] = ""
                return ""

            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""

        self.file_contents_cache[file_path] = content
        return content

    def _enrich_groups_with_dependencies(
        self, groups: list[FileGroup], dependencies: dict[str, list[str]]
    ) -> None:
        """Populate dependency information for each group."""
        for group in groups:
            group_paths = {file.path for file in group.files}
            dependency_set = {
                dep
                for file in group.files
                for dep in dependencies.get(file.path, [])
                if dep not in group_paths
            }

            group.dependencies = sorted(dependency_set)

    def _matches_pattern(self, pattern: str, file_path: str) -> bool:
        """Match change-type patterns against either full paths or file names."""
        target = file_path if "/" in pattern else Path(file_path).name
        return re.search(pattern, target, re.IGNORECASE) is not None
