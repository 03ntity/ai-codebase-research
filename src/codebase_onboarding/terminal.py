from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from .models import SkillAssessment

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:  # pragma: no cover - exercised when rich is not installed
    Console = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]
    Table = None  # type: ignore[assignment]


class Terminal:
    def __init__(self) -> None:
        self._console = Console() if Console else None

    def banner(self, target: str, output: str) -> None:
        text = (
            "AI Codebase Onboarding Agent\n"
            f"Target: {target}\n"
            f"Output: {output}"
        )
        if self._console and Panel:
            self._console.print(Panel.fit(text, title="Session", border_style="cyan"))
        else:
            print("AI Codebase Onboarding Agent")
            print(f"Target: {target}")
            print(f"Output: {output}")

    def step(self, current: int, total: int, message: str) -> None:
        self.info(f"[{current}/{total}] {message}")

    def info(self, message: str) -> None:
        self._emit("INFO", message, "cyan")

    def success(self, message: str) -> None:
        self._emit("OK", message, "green")

    def warning(self, message: str) -> None:
        self._emit("WARN", message, "yellow")

    def error(self, message: str) -> None:
        self._emit("ERROR", message, "red")

    @contextmanager
    def span(self, message: str) -> Iterator[None]:
        start = perf_counter()
        if self._console:
            with self._console.status(message, spinner="dots"):
                yield
        else:
            self.info(message)
            yield
        elapsed = perf_counter() - start
        self.success(f"{message} completed in {elapsed:.1f}s")

    def report_written(self, analyzed_files: int, target: str, output: str) -> None:
        rows = [
            ("Analyzed files", str(analyzed_files)),
            ("Target", target),
            ("Report", output),
        ]
        self.table("Report Summary", rows)

    def skill_assessment(self, assessment: SkillAssessment) -> None:
        rows = [
            ("Candidate", "yes" if assessment.is_skill_candidate else "no"),
            ("Confidence", assessment.confidence),
            ("Reason", assessment.reason),
        ]
        if assessment.recommended_skill_name:
            rows.append(("Recommended name", assessment.recommended_skill_name))
        self.table("Skill Assessment", rows)

    def table(self, title: str, rows: list[tuple[str, str]]) -> None:
        if self._console and Table:
            table = Table(title=title, show_header=True, header_style="bold cyan")
            table.add_column("Field", style="bold")
            table.add_column("Value")
            for key, value in rows:
                table.add_row(key, value)
            self._console.print(table)
            return

        print(title)
        for key, value in rows:
            print(f"- {key}: {value}")

    def ask_yes_no(self, prompt: str, *, default: bool = False) -> bool:
        suffix = " [Y/n]: " if default else " [y/N]: "
        try:
            if self._console:
                answer = self._console.input(f"{prompt}{suffix}").strip().lower()
            else:
                answer = input(f"{prompt}{suffix}").strip().lower()
        except EOFError:
            return default

        if not answer:
            return default
        return answer in {"y", "yes"}

    def _emit(self, level: str, message: str, style: str) -> None:
        if self._console:
            self._console.print(f"[bold {style}]{level:<5}[/] {message}")
        else:
            print(f"{level:<5} {message}")
