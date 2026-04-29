import unittest
from pathlib import Path
from unittest.mock import patch

from codebase_onboarding.ai_client import build_onboarding_prompt
from codebase_onboarding.cli import main
from codebase_onboarding.analyzers import analyze_repository
from codebase_onboarding.models import SkillAssessment
from codebase_onboarding.report import render_markdown_report
from codebase_onboarding.scanner import scan_repository


class CodebaseOnboardingTest(unittest.TestCase):
    def test_generates_onboarding_report_for_python_project(self) -> None:
        root = Path(__file__).parent / "fixtures" / "demo_project"
        inventory = scan_repository(root)
        result = analyze_repository(inventory)
        report = render_markdown_report(result, "## Mock AI Brief\n\nRead `main.py` first.")

        self.assertIn("main.py", result.entrypoints)
        self.assertEqual(result.language_counts["Python"], 2)
        self.assertTrue(any(symbol.name == "App" for symbol in result.symbols))
        self.assertTrue(any(excerpt.file == "main.py" for excerpt in result.file_excerpts))
        self.assertIn("Codebase Onboarding Report", report)
        self.assertIn("Agentic Workflow", report)

    def test_builds_ai_prompt_from_analysis(self) -> None:
        root = Path(__file__).parent / "fixtures" / "demo_project"
        result = analyze_repository(scan_repository(root))
        prompt = build_onboarding_prompt(result)

        self.assertIn("Repository analysis JSON", prompt)
        self.assertIn("demo_project", prompt)
        self.assertIn("selected_file_excerpts", prompt)
        self.assertIn("class App", prompt)
        self.assertIn("30/60/90 minute onboarding plan", prompt)

    def test_detects_go_project_entrypoints_and_symbols(self) -> None:
        root = Path(__file__).parent / "fixtures" / "go_project"
        result = analyze_repository(scan_repository(root))
        prompt = build_onboarding_prompt(result)

        self.assertIn("cmd/api/main.go", result.entrypoints)
        self.assertIn("Go modules", result.package_managers)
        self.assertTrue(any(symbol.name == "main" for symbol in result.symbols))
        self.assertIn("func main()", prompt)

    def test_detects_rust_project_entrypoints_and_symbols(self) -> None:
        root = Path(__file__).parent / "fixtures" / "rust_project"
        result = analyze_repository(scan_repository(root))
        prompt = build_onboarding_prompt(result)

        self.assertIn("src/main.rs", result.entrypoints)
        self.assertIn("Cargo", result.package_managers)
        self.assertTrue(any(symbol.name == "main" for symbol in result.symbols))
        self.assertIn("fn main()", prompt)

    def test_cli_requires_ai_and_writes_report_with_mocked_provider(self) -> None:
        root = Path(__file__).parent / "fixtures" / "demo_project"
        output = root / "onboarding-test-output.md"

        with patch(
            "codebase_onboarding.cli.generate_ai_onboarding_brief",
            return_value="## Mock AI Brief\n\nRead `main.py` first.",
        ), patch(
            "codebase_onboarding.cli.assess_skill_candidate",
            return_value=SkillAssessment(
                is_skill_candidate=False,
                confidence="medium",
                reason="The fixture is too small to be a reusable skill.",
            ),
        ):
            main([str(root), "--output", str(output)])

        report = output.read_text(encoding="utf-8")
        self.assertIn("Mock AI Brief", report)

    def test_cli_can_create_skill_md_when_user_accepts(self) -> None:
        root = Path(__file__).parent / "fixtures" / "demo_project"
        output = root / "onboarding-test-output.md"
        skill_path = root / "SKILL.md"

        skill_content = (
            "---\n"
            "name: demo-project\n"
            "description: Use when testing generated skill creation from a demo project.\n"
            "---\n\n"
            "# Demo Project\n\n"
            "Use this skill to inspect the demo project fixture.\n"
        )

        with patch(
            "codebase_onboarding.cli.generate_ai_onboarding_brief",
            return_value="## Mock AI Brief\n\nRead `main.py` first.",
        ), patch(
            "codebase_onboarding.cli.assess_skill_candidate",
            return_value=SkillAssessment(
                is_skill_candidate=True,
                confidence="high",
                reason="The project has a reusable workflow.",
                recommended_skill_name="demo-project",
                skill_md=skill_content,
            ),
        ), patch("codebase_onboarding.terminal.Terminal.ask_yes_no", return_value=True):
            main([str(root), "--output", str(output)])

        self.assertEqual(skill_path.read_text(encoding="utf-8"), skill_content)


if __name__ == "__main__":
    unittest.main()
