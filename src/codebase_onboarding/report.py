from __future__ import annotations

from datetime import datetime, timezone

from .models import AnalysisResult


def render_markdown_report(result: AnalysisResult, ai_brief: str) -> str:
    lines: list[str] = []
    lines.append(f"# Codebase Onboarding Report: {result.root.name}")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append(ai_brief.strip())
    lines.append("")

    lines.append("## Agentic Workflow")
    lines.append("")
    lines.append(
        "This report was produced by an AI-driven onboarding workflow. The local discovery layer "
        "collects repository evidence, then the AI provider generates the human-readable onboarding "
        "brief from that grounded context."
    )
    lines.append("")

    return "\n".join(lines)
