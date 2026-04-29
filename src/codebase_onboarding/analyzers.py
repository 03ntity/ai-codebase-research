from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path

from .models import AnalysisResult, FileExcerpt, FileInfo, RepoInventory, SymbolInfo


JS_EXPORT_PATTERN = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)

TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
EXCERPT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".php",
    ".rb",
    ".swift",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".sql",
    ".sh",
    ".ps1",
}


def analyze_repository(inventory: RepoInventory) -> AnalysisResult:
    language_counts = Counter(file.language for file in inventory.files)
    role_counts = Counter(file.role for file in inventory.files)
    entrypoints = detect_entrypoints(inventory.files)
    frameworks = detect_frameworks(inventory.root, inventory.files)
    package_managers = detect_package_managers(inventory.files)
    config_files = sorted(file.relative_path for file in inventory.files if file.role == "configuration")
    test_files = sorted(file.relative_path for file in inventory.files if file.role == "test")
    symbols = extract_symbols(inventory.files)
    risks = detect_risks(inventory, entrypoints, test_files)
    recommended_path = build_recommended_path(inventory.files, entrypoints, test_files)
    largest_files = sorted(inventory.files, key=lambda file: file.size, reverse=True)[:10]
    file_excerpts = select_file_excerpts(inventory.files, entrypoints, recommended_path)

    return AnalysisResult(
        root=inventory.root,
        total_files=len(inventory.files),
        total_lines=sum(file.line_count for file in inventory.files),
        language_counts=dict(language_counts.most_common()),
        role_counts=dict(role_counts.most_common()),
        entrypoints=entrypoints,
        frameworks=frameworks,
        package_managers=package_managers,
        config_files=config_files,
        test_files=test_files,
        symbols=symbols,
        risks=risks,
        recommended_path=recommended_path,
        largest_files=largest_files,
        file_excerpts=file_excerpts,
    )


def detect_entrypoints(files: list[FileInfo]) -> list[str]:
    known_names = {
        "main.py",
        "app.py",
        "server.py",
        "manage.py",
        "__main__.py",
        "index.js",
        "index.ts",
        "main.ts",
        "main.tsx",
        "app.tsx",
        "vite.config.ts",
        "main.go",
        "main.rs",
        "main.java",
        "program.cs",
        "application.kt",
        "index.php",
        "server.rb",
    }
    entrypoints = [
        file.relative_path
        for file in files
        if file.path.name.lower() in known_names
        or file.role == "entrypoint"
        or file.relative_path.lower() in {"cmd/server/main.go", "cmd/api/main.go", "src/main.rs"}
    ]
    return sorted(set(entrypoints))


def detect_frameworks(root: Path, files: list[FileInfo]) -> list[str]:
    frameworks: set[str] = set()
    relative_paths = {file.relative_path.lower() for file in files}
    names = {file.path.name.lower() for file in files}

    if "package.json" in names:
        frameworks.update(_frameworks_from_package_json(root / "package.json"))
    if "pyproject.toml" in names:
        pyproject = _read_text(root / "pyproject.toml").lower()
        for marker, framework in {
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "streamlit": "Streamlit",
            "pytest": "pytest",
            "ruff": "Ruff",
        }.items():
            if marker in pyproject:
                frameworks.add(framework)
    if "manage.py" in names:
        frameworks.add("Django")
    if any(path.endswith("requirements.txt") for path in relative_paths):
        requirements = "\n".join(
            _read_text(file.path).lower() for file in files if file.path.name.lower() == "requirements.txt"
        )
        for marker, framework in {"fastapi": "FastAPI", "django": "Django", "flask": "Flask"}.items():
            if marker in requirements:
                frameworks.add(framework)
    if any(path.endswith(".tsx") for path in relative_paths):
        frameworks.add("React/TSX")
    if "next.config.js" in names or "next.config.mjs" in names or "next.config.ts" in names:
        frameworks.add("Next.js")
    if "vite.config.ts" in names or "vite.config.js" in names:
        frameworks.add("Vite")
    if "cargo.toml" in names:
        cargo = _read_text(root / "Cargo.toml").lower()
        for marker, framework in {
            "actix-web": "Actix Web",
            "axum": "Axum",
            "rocket": "Rocket",
            "tauri": "Tauri",
        }.items():
            if marker in cargo:
                frameworks.add(framework)
    if "go.mod" in names:
        gomod = _read_text(root / "go.mod").lower()
        for marker, framework in {
            "gin-gonic/gin": "Gin",
            "gofiber/fiber": "Fiber",
            "labstack/echo": "Echo",
            "go-chi/chi": "Chi",
            "grpc": "gRPC",
        }.items():
            if marker in gomod:
                frameworks.add(framework)
    if "pom.xml" in names:
        pom = _read_text(root / "pom.xml").lower()
        if "spring-boot" in pom:
            frameworks.add("Spring Boot")
        if "quarkus" in pom:
            frameworks.add("Quarkus")
    if "build.gradle" in names:
        gradle = _read_text(root / "build.gradle").lower()
        if "spring-boot" in gradle:
            frameworks.add("Spring Boot")
        if "ktor" in gradle:
            frameworks.add("Ktor")

    return sorted(frameworks)


def detect_package_managers(files: list[FileInfo]) -> list[str]:
    names = {file.path.name.lower() for file in files}
    managers = []
    if "pyproject.toml" in names:
        managers.append("Python pyproject")
    if "requirements.txt" in names:
        managers.append("pip requirements")
    if "poetry.lock" in names:
        managers.append("Poetry")
    if "uv.lock" in names:
        managers.append("uv")
    if "package.json" in names:
        managers.append("npm-compatible")
    if "pnpm-lock.yaml" in names:
        managers.append("pnpm")
    if "yarn.lock" in names:
        managers.append("Yarn")
    if "package-lock.json" in names:
        managers.append("npm")
    if "cargo.toml" in names:
        managers.append("Cargo")
    if "go.mod" in names:
        managers.append("Go modules")
    if "pom.xml" in names:
        managers.append("Maven")
    if "build.gradle" in names or "settings.gradle" in names:
        managers.append("Gradle")
    if "composer.json" in names:
        managers.append("Composer")
    if "gemfile" in names:
        managers.append("Bundler")
    if any(name.endswith((".csproj", ".fsproj", ".sln")) for name in names):
        managers.append(".NET")
    return managers


def extract_symbols(files: list[FileInfo]) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []
    for file in files:
        if file.language == "Python":
            symbols.extend(_extract_python_symbols(file))
        elif file.extension in {".js", ".jsx", ".ts", ".tsx"}:
            symbols.extend(_extract_js_symbols(file))
        elif file.extension == ".go":
            symbols.extend(_extract_regex_symbols(file, r"^\s*func\s+(?:\([^)]+\)\s*)?([A-Za-z_]\w*)\s*\(", "function"))
        elif file.extension == ".rs":
            symbols.extend(_extract_regex_symbols(file, r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)\s*\(", "function"))
            symbols.extend(_extract_regex_symbols(file, r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)", "type"))
        elif file.extension in {".java", ".kt", ".cs", ".php", ".rb", ".swift"}:
            symbols.extend(_extract_common_language_symbols(file))
        if len(symbols) >= 200:
            break
    return symbols[:200]


def detect_risks(inventory: RepoInventory, entrypoints: list[str], test_files: list[str]) -> list[str]:
    risks: list[str] = []
    names = {file.path.name.lower() for file in inventory.files}

    if not any(name.startswith("readme") for name in names):
        risks.append("No README detected. New contributors may lack setup and project context.")
    if not entrypoints:
        risks.append("No clear entrypoint detected. Onboarding should document how the application starts.")
    if not test_files:
        risks.append("No test files detected. Changes may be harder to validate safely.")
    if inventory.skipped_files:
        risks.append(f"{len(inventory.skipped_files)} files were skipped because they were too large or unreadable.")

    large_source_files = [
        file.relative_path
        for file in inventory.files
        if file.role == "source" and file.line_count > 500
    ][:5]
    if large_source_files:
        risks.append("Large source files may hide multiple responsibilities: " + ", ".join(large_source_files))

    todo_count = sum(_count_todos(file.path) for file in inventory.files if file.role in {"source", "test"})
    if todo_count:
        risks.append(f"{todo_count} TODO/FIXME markers found across source and test files.")

    env_files = [file.relative_path for file in inventory.files if file.role == "environment"]
    if env_files:
        risks.append("Environment files are present. Confirm secrets are not committed: " + ", ".join(env_files[:5]))

    return risks


def build_recommended_path(files: list[FileInfo], entrypoints: list[str], test_files: list[str]) -> list[str]:
    readmes = sorted(file.relative_path for file in files if file.path.name.lower().startswith("readme"))
    manifests = sorted(file.relative_path for file in files if file.role == "manifest")
    configs = sorted(file.relative_path for file in files if file.role == "configuration")

    path: list[str] = []
    path.extend(readmes[:2])
    path.extend(manifests[:5])
    path.extend(entrypoints[:5])
    path.extend(configs[:5])
    path.extend(test_files[:5])

    seen: set[str] = set()
    ordered = []
    for item in path:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def select_file_excerpts(
    files: list[FileInfo],
    entrypoints: list[str],
    recommended_path: list[str],
    *,
    max_files: int = 12,
    max_chars_per_file: int = 5_000,
    max_total_chars: int = 30_000,
) -> list[FileExcerpt]:
    candidates = [
        file
        for file in files
        if file.extension in EXCERPT_EXTENSIONS
        and file.role != "environment"
        and file.size > 0
        and file.size <= 250_000
    ]

    by_path = {file.relative_path: file for file in candidates}
    ordered: list[FileInfo] = []

    def add(path: str) -> None:
        file = by_path.get(path)
        if file and file not in ordered:
            ordered.append(file)

    for path in recommended_path:
        add(path)
    for path in entrypoints:
        add(path)

    priority_roles = {"manifest", "configuration", "documentation", "entrypoint"}
    for file in sorted(candidates, key=lambda item: (item.role not in priority_roles, item.relative_path)):
        if file.role in priority_roles and file not in ordered:
            ordered.append(file)

    source_files = [
        file
        for file in candidates
        if file.role == "source" and file.language not in {"Markdown", "JSON", "YAML", "TOML"}
    ]
    for file in sorted(source_files, key=lambda item: (-item.line_count, item.relative_path)):
        if file not in ordered:
            ordered.append(file)

    excerpts: list[FileExcerpt] = []
    total_chars = 0
    for file in ordered:
        if len(excerpts) >= max_files or total_chars >= max_total_chars:
            break
        remaining = max_total_chars - total_chars
        excerpt = _build_excerpt(file, max_chars=min(max_chars_per_file, remaining))
        if not excerpt:
            continue
        excerpts.append(excerpt)
        total_chars += len(excerpt.content)

    return excerpts


def _extract_python_symbols(file: FileInfo) -> list[SymbolInfo]:
    text = _read_text(file.path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    symbols: list[SymbolInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(SymbolInfo(file=file.relative_path, kind="class", name=node.name, line=node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(SymbolInfo(file=file.relative_path, kind="function", name=node.name, line=node.lineno))
    return symbols


def _build_excerpt(file: FileInfo, *, max_chars: int) -> FileExcerpt | None:
    if max_chars <= 0:
        return None
    text = _read_text(file.path)
    if not text.strip():
        return None

    lines = text.splitlines()
    excerpt_lines: list[str] = []
    char_count = 0
    for line in lines:
        next_count = char_count + len(line) + 1
        if next_count > max_chars:
            break
        excerpt_lines.append(line)
        char_count = next_count

    if not excerpt_lines:
        excerpt_lines = [text[:max_chars]]

    return FileExcerpt(
        file=file.relative_path,
        language=file.language,
        role=file.role,
        start_line=1,
        end_line=len(excerpt_lines),
        truncated=len(excerpt_lines) < len(lines) or len(text) > max_chars,
        content="\n".join(excerpt_lines),
    )


def _extract_js_symbols(file: FileInfo) -> list[SymbolInfo]:
    text = _read_text(file.path)
    return [
        SymbolInfo(file=file.relative_path, kind="symbol", name=match.group(1), line=_line_number(text, match.start()))
        for match in JS_EXPORT_PATTERN.finditer(text)
    ]


def _extract_regex_symbols(file: FileInfo, pattern: str, kind: str) -> list[SymbolInfo]:
    text = _read_text(file.path)
    regex = re.compile(pattern, re.MULTILINE)
    return [
        SymbolInfo(file=file.relative_path, kind=kind, name=match.group(1), line=_line_number(text, match.start()))
        for match in regex.finditer(text)
    ]


def _extract_common_language_symbols(file: FileInfo) -> list[SymbolInfo]:
    patterns = [
        (r"^\s*(?:public\s+|private\s+|protected\s+|internal\s+)?(?:class|interface|enum|struct)\s+([A-Za-z_]\w*)", "type"),
        (r"^\s*(?:fun|func|function|def)\s+([A-Za-z_]\w*)\s*\(", "function"),
        (r"^\s*class\s+([A-Za-z_]\w*)", "type"),
    ]
    symbols: list[SymbolInfo] = []
    for pattern, kind in patterns:
        symbols.extend(_extract_regex_symbols(file, pattern, kind))
    return symbols[:40]


def _frameworks_from_package_json(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()

    dependencies = {}
    dependencies.update(data.get("dependencies", {}))
    dependencies.update(data.get("devDependencies", {}))

    markers = {
        "react": "React",
        "next": "Next.js",
        "vite": "Vite",
        "vue": "Vue",
        "svelte": "Svelte",
        "express": "Express",
        "fastify": "Fastify",
        "tailwindcss": "Tailwind CSS",
        "playwright": "Playwright",
        "vitest": "Vitest",
        "jest": "Jest",
    }
    return {framework for package, framework in markers.items() if package in dependencies}


def _count_todos(path: Path) -> int:
    count = 0
    for line in _read_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*", "<!--")) and TODO_PATTERN.search(stripped):
            count += 1
    return count


def _line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
