from __future__ import annotations

from pathlib import Path

from .models import FileInfo, RepoInventory


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".turbo",
    "coverage",
    ".idea",
    ".vscode",
}

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".csproj": "C# project",
    ".fsproj": "F# project",
    ".sln": "Visual Studio Solution",
    ".gradle": "Gradle",
}


def scan_repository(
    root: Path,
    *,
    max_file_size: int = 250_000,
    include_hidden: bool = False,
) -> RepoInventory:
    root = root.resolve()
    inventory = RepoInventory(root=root)

    for path in sorted(root.rglob("*")):
        if not include_hidden and _has_hidden_part(path.relative_to(root)):
            continue
        if _is_ignored(path, root):
            continue
        if not path.is_file():
            continue

        relative_path = path.relative_to(root).as_posix()
        try:
            size = path.stat().st_size
        except OSError:
            inventory.skipped_files.append(relative_path)
            continue

        if size > max_file_size:
            inventory.skipped_files.append(f"{relative_path} (>{max_file_size} bytes)")
            continue

        extension = path.suffix.lower()
        language = LANGUAGE_BY_EXTENSION.get(extension, "Other")
        role = classify_role(path.name, relative_path)
        line_count = count_lines(path)

        inventory.files.append(
            FileInfo(
                path=path,
                relative_path=relative_path,
                size=size,
                extension=extension,
                role=role,
                language=language,
                line_count=line_count,
            )
        )

    return inventory


def classify_role(filename: str, relative_path: str) -> str:
    lower_name = filename.lower()
    lower_path = relative_path.lower()

    if lower_name in {"readme.md", "readme.rst", "readme.txt"}:
        return "documentation"
    if lower_name in {
        "pyproject.toml",
        "requirements.txt",
        "package.json",
        "cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "settings.gradle",
        "composer.json",
        "gemfile",
        "mix.exs",
        "deno.json",
    } or lower_name.endswith((".csproj", ".fsproj", ".sln")):
        return "manifest"
    if lower_name.startswith(".env") or lower_name.endswith(".env"):
        return "environment"
    if "test" in lower_path or "spec" in lower_path:
        return "test"
    if lower_name in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}:
        return "deployment"
    if lower_name.endswith((".config.js", ".config.ts", ".config.cjs", ".config.mjs")):
        return "configuration"
    if lower_name in {"tsconfig.json", "ruff.toml", "mypy.ini", "pytest.ini", "tox.ini"}:
        return "configuration"
    if lower_path.startswith(("docs/", "doc/")) or lower_name.endswith(".md"):
        return "documentation"
    if lower_path.startswith((".github/", ".gitlab/")):
        return "ci"
    if lower_name in {
        "main.py",
        "app.py",
        "server.py",
        "manage.py",
        "index.js",
        "index.ts",
        "main.ts",
        "main.tsx",
        "app.tsx",
        "main.go",
        "main.rs",
        "main.java",
        "program.cs",
        "application.kt",
        "index.php",
        "server.rb",
    }:
        return "entrypoint"
    return "source"


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def _is_ignored(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in IGNORED_DIRS for part in relative_parts)


def _has_hidden_part(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)
