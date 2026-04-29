from __future__ import annotations

import argparse
from pathlib import Path

from .ai_client import AIClientError, assess_skill_candidate, generate_ai_onboarding_brief
from .analyzers import analyze_repository
from .models import SkillAssessment
from .report import render_markdown_report
from .scanner import scan_repository
from .terminal import Terminal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codebase-onboard",
        description="Scan a repository and generate a Markdown onboarding report.",
    )
    parser.add_argument("target", type=Path, help="Repository or folder to analyze.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("onboarding-report.md"),
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=250_000,
        help="Skip files larger than this many bytes.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and folders.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="AI generation temperature. Defaults to 0.3.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    terminal = Terminal()

    target = args.target.resolve()
    if not target.exists():
        parser.error(f"Target does not exist: {target}")
    if not target.is_dir():
        parser.error(f"Target must be a directory: {target}")

    output = args.output.resolve()
    terminal.banner(str(target), str(output))

    terminal.step(1, 5, "Scanning repository")
    inventory = scan_repository(
        target,
        max_file_size=args.max_file_size,
        include_hidden=args.include_hidden,
    )
    terminal.step(2, 5, f"Prepared {len(inventory.files)} files for onboarding analysis")

    terminal.step(3, 5, "Inferring repository structure")
    result = analyze_repository(inventory)
    terminal.info(f"Selected {len(result.file_excerpts)} high-signal files for AI context")

    terminal.step(4, 5, "Requesting onboarding brief from AI provider")
    try:
        with terminal.span("AI onboarding analysis"):
            ai_brief = generate_ai_onboarding_brief(result, temperature=args.temperature)
    except AIClientError as exc:
        terminal.error(str(exc))
        parser.error(str(exc))

    report = render_markdown_report(result, ai_brief=ai_brief)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")

    terminal.report_written(result.total_files, str(target), str(output))

    terminal.step(5, 5, "Evaluating whether the project can become an agent skill")
    try:
        with terminal.span("AI skill assessment"):
            assessment = assess_skill_candidate(result, ai_brief)
    except AIClientError as exc:
        terminal.error(str(exc))
        parser.error(str(exc))

    handle_skill_assessment(target, assessment, terminal)


def handle_skill_assessment(target: Path, assessment: SkillAssessment, terminal: Terminal | None = None) -> None:
    terminal = terminal or Terminal()
    terminal.skill_assessment(assessment)

    if not assessment.is_skill_candidate:
        terminal.warning("No SKILL.md was created because the project was not recommended as a reusable agent skill.")
        return

    if not terminal.ask_yes_no("Create SKILL.md in the target project?"):
        terminal.warning("Skipped SKILL.md creation.")
        return

    skill_path = target / "SKILL.md"
    if skill_path.exists() and not terminal.ask_yes_no("SKILL.md already exists. Overwrite it?"):
        terminal.warning("Skipped SKILL.md creation because the file already exists.")
        return

    skill_md = normalize_skill_md(
        assessment.skill_md or "",
        fallback_name=assessment.recommended_skill_name or target.name,
        fallback_description="Use this skill when an agent needs the reusable workflow captured from this project.",
    )
    skill_path.write_text(skill_md, encoding="utf-8")
    terminal.success(f"Created {skill_path}")


def normalize_skill_md(content: str, *, fallback_name: str, fallback_description: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("---"):
        return cleaned + "\n"

    skill_name = _normalize_skill_name(fallback_name)
    return (
        "---\n"
        f"name: {skill_name}\n"
        f"description: {fallback_description}\n"
        "---\n\n"
        f"{cleaned}\n"
    )


def _normalize_skill_name(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value)
    normalized = "-".join(part for part in normalized.split("-") if part)
    return normalized[:63] or "generated-skill"
