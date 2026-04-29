from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FileInfo:
    path: Path
    relative_path: str
    size: int
    extension: str
    role: str
    language: str
    line_count: int = 0


@dataclass
class SymbolInfo:
    file: str
    kind: str
    name: str
    line: int | None = None


@dataclass
class FileExcerpt:
    file: str
    language: str
    role: str
    start_line: int
    end_line: int
    truncated: bool
    content: str


@dataclass
class RepoInventory:
    root: Path
    files: list[FileInfo] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    root: Path
    total_files: int
    total_lines: int
    language_counts: dict[str, int]
    role_counts: dict[str, int]
    entrypoints: list[str]
    frameworks: list[str]
    package_managers: list[str]
    config_files: list[str]
    test_files: list[str]
    symbols: list[SymbolInfo]
    risks: list[str]
    recommended_path: list[str]
    largest_files: list[FileInfo]
    file_excerpts: list[FileExcerpt]


@dataclass
class SkillAssessment:
    is_skill_candidate: bool
    confidence: str
    reason: str
    recommended_skill_name: str | None = None
    skill_md: str | None = None
