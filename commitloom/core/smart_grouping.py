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
    HOTFIX = "hotfix"
    TEST = "test"
    DOCS = "docs"
    REFACTOR = "refactor"
    STYLE = "style"
    CHORE = "chore"
    CONFIG = "config"
    BUILD = "build"
    PERF = "perf"
    SECURITY = "security"
    CI = "ci"
    REVERT = "revert"


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
            r"CONTRIBUTING",
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
            r"poetry\.lock$",
            r"uv\.lock$",
            r"Gemfile",
            r"Cargo\.toml$",
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
            r"\.editorconfig$",
            r"\.json$",  # Move .json$ to the end to let package.json match BUILD first
        ],
        ChangeType.STYLE: [
            r"\.css$",
            r"\.scss$",
            r"\.sass$",
            r"\.less$",
            r"\.styl$",
        ],
        ChangeType.CI: [
            r"\.github/workflows/",
            r"\.gitlab-ci\.yml$",
            r"\.travis\.yml$",
            r"\.circleci/",
            r"jenkins",
            r"azure-pipelines",
        ],
        ChangeType.SECURITY: [
            r"security",
            r"\.secret",
            r"auth",
            r"crypt",
            r"hash",
            r"password",
            r"token",
        ],
        ChangeType.HOTFIX: [
            r"hotfix",
            r"urgent",
            r"critical",
        ],
        ChangeType.PERF: [
            r"perf",
            r"performance",
            r"optim",
            r"cache",
        ],
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
                if re.search(pattern, file_path, re.IGNORECASE):
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
            if re.search(pattern, file_path, re.IGNORECASE):
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
            # Determine file language
            ext = Path(file.path).suffix.lower()
            language = self._get_language_from_extension(ext)

            if language and language in self.IMPORT_PATTERNS:
                imports = self._extract_imports(file.path, language)
                # Match imports to files in our change set
                for imp in imports:
                    for other_file in files:
                        if self._import_matches_file(imp, other_file.path):
                            dependencies[file.path].append(other_file.path)

        return dict(dependencies)

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

        # Check if file exists and is readable
        file_path_obj = Path(file_path)
        if not file_path_obj.exists() or not file_path_obj.is_file():
            return imports

        try:
            # Read file content (with size limit to avoid performance issues)
            if file_path_obj.stat().st_size > 1_000_000:  # 1MB limit
                return imports

            content = file_path_obj.read_text(encoding="utf-8", errors="ignore")

            # Extract imports based on language
            if language == "python":
                imports = self._extract_python_imports(content)
            elif language in ("javascript", "typescript"):
                imports = self._extract_js_imports(content)
            # Add more languages as needed

        except (OSError, UnicodeDecodeError):
            # If we can't read the file, return empty list
            pass

        return imports

    def _extract_python_imports(self, content: str) -> list[str]:
        """Extract Python imports using AST parsing."""
        import ast
        imports = []

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            # If parsing fails, fall back to regex
            imports = self._extract_imports_regex(content, "python")

        return imports

    def _extract_js_imports(self, content: str) -> list[str]:
        """Extract JavaScript/TypeScript imports using regex."""
        return self._extract_imports_regex(content, "javascript")

    def _extract_imports_regex(self, content: str, language: str) -> list[str]:
        """Extract imports using regex patterns."""
        imports = []
        patterns = self.IMPORT_PATTERNS.get(language, [])

        for pattern in patterns:
            matches = re.findall(pattern, content)
            imports.extend(matches)

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

    def _calculate_dynamic_confidence(
        self, files: list[GitFile], change_type: ChangeType, relationships: list[FileRelationship]
    ) -> float:
        """
        Calculate confidence score based on multiple factors.

        Args:
            files: Files in the group
            change_type: Type of change
            relationships: Relationships between files

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence

        # Factor 1: Number of files (smaller groups are more confident)
        if len(files) == 1:
            confidence += 0.2
        elif len(files) <= 3:
            confidence += 0.15
        elif len(files) <= 5:
            confidence += 0.1

        # Factor 2: Relationship strength
        if relationships:
            avg_strength = sum(r.strength for r in relationships) / len(relationships)
            confidence += avg_strength * 0.2

        # Factor 3: Change type confidence
        high_confidence_types = {ChangeType.TEST, ChangeType.DOCS, ChangeType.CONFIG, ChangeType.CI}
        if change_type in high_confidence_types:
            confidence += 0.1

        # Factor 4: All files in same directory
        if len(set(Path(f.path).parent for f in files)) == 1:
            confidence += 0.1

        # Ensure confidence is in valid range
        return min(max(confidence, 0.0), 1.0)

    def _detect_feature_boundary(self, files: list[GitFile]) -> list[list[GitFile]]:
        """
        Detect feature boundaries within a group of files.

        Args:
            files: List of files to analyze

        Returns:
            List of file groups representing different features
        """
        # Group files by common feature prefixes
        feature_groups: dict[str, list[GitFile]] = defaultdict(list)

        for file in files:
            feature_key = self._extract_feature_key(file.path)
            feature_groups[feature_key].append(file)

        return list(feature_groups.values())

    def _extract_feature_key(self, file_path: str) -> str:
        """
        Extract a feature key from file path.

        Args:
            file_path: Path to the file

        Returns:
            Feature key for grouping
        """
        parts = Path(file_path).parts

        # Look for feature indicators
        for part in parts:
            # Feature folder or file prefix patterns
            if any(
                keyword in part.lower()
                for keyword in ["feature", "module", "component", "service", "controller", "model"]
            ):
                return part

        # Use top-level directory as fallback
        return parts[0] if parts else "default"

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

        for change_type, files in groups_by_type.items():
            if not files:
                continue

            # Get relevant relationships for these files
            file_paths = {f.path for f in files}
            relevant_relationships = [
                r for r in self.relationships if r.file1 in file_paths and r.file2 in file_paths
            ]

            # For test files, try to group with their implementations
            if change_type == ChangeType.TEST:
                test_groups = self._group_tests_with_implementations(files)
                refined_groups.extend(test_groups)
            # For small groups, keep them together
            elif len(files) <= 3:
                confidence = self._calculate_dynamic_confidence(files, change_type, relevant_relationships)
                group = FileGroup(
                    files=files,
                    change_type=change_type,
                    reason=f"All {change_type.value} changes",
                    confidence=confidence,
                )
                refined_groups.append(group)
            # For larger groups, detect feature boundaries and split by module
            else:
                # Try to detect feature boundaries first
                feature_subgroups = self._detect_feature_boundary(files)

                for feature_files in feature_subgroups:
                    if len(feature_files) <= 5:
                        # Small enough to keep as one group
                        confidence = self._calculate_dynamic_confidence(
                            feature_files, change_type, relevant_relationships
                        )
                        group = FileGroup(
                            files=feature_files,
                            change_type=change_type,
                            reason=f"{change_type.value} changes in feature",
                            confidence=confidence,
                        )
                        refined_groups.append(group)
                    else:
                        # Still too large, split by module
                        subgroups = self._split_by_module(feature_files, change_type)
                        refined_groups.extend(subgroups)

        return refined_groups

    def _group_tests_with_implementations(self, test_files: list[GitFile]) -> list[FileGroup]:
        """Group test files with their corresponding implementations."""
        groups = []

        for test_file in test_files:
            # Find related implementation files
            related_files = [test_file]

            for rel in self.relationships:
                if rel.relationship_type == "test-implementation":
                    if rel.file1 == test_file.path:
                        # Find the implementation file in our file list
                        impl_file = next((f for f in test_files if f.path == rel.file2), None)
                        if impl_file:
                            related_files.append(impl_file)

            group = FileGroup(
                files=related_files,
                change_type=ChangeType.TEST,
                reason="Test and related implementation",
                confidence=0.9,
            )
            groups.append(group)

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
