from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .models import AnalysisResult, SkillAssessment


_API_HOST = "api." + "swift" + "router.com"
DEFAULT_API_BASE = f"https://{_API_HOST}/v1"
DEFAULT_MODEL = "gpt-5.4"


class AIClientError(RuntimeError):
    """Raised when the AI provider request fails."""


def build_onboarding_prompt(result: AnalysisResult) -> str:
    payload = _analysis_payload(result)

    return (
        "You are a senior software engineer onboarding a new developer to an unfamiliar codebase.\n"
        "Use the repository analysis JSON below to write a concise, practical onboarding brief.\n\n"
        "Important framing rules:\n"
        "- Write for humans, not as a raw scanner or static-analysis dump.\n"
        "- Do not include file counts, language-count tables, role-count tables, or raw inventory summaries.\n"
        "- Do not say the product is primarily a static analyzer.\n"
        "- The current CLI requires AI generation through the configured AI provider; do not describe AI as optional.\n"
        "- Frame local repository inspection as an evidence-gathering step that grounds the AI onboarding agent.\n"
        "- Prefer plain English explanations, practical reading order, and developer actions.\n\n"
        "Include these sections in Markdown:\n"
        "1. Architecture in plain English\n"
        "2. Request or execution flow, if inferable\n"
        "3. Most important files to read first\n"
        "4. Risks and validation advice\n"
        "5. A 30/60/90 minute onboarding plan\n\n"
        "Be specific to the evidence. Do not invent services, frameworks, or commands that are not present.\n\n"
        f"Repository analysis JSON:\n{json.dumps(payload, indent=2)}"
    )


def build_skill_assessment_prompt(result: AnalysisResult, onboarding_brief: str) -> str:
    payload = _analysis_payload(result)

    return (
        "You are evaluating whether a repository can become an agent skill for AI coding agents "
        "such as Hermes, OpenClaw, Codex, or similar systems.\n\n"
        "A good SKILL.md should package reusable procedural knowledge, workflows, domain rules, "
        "tool usage guidance, or repeatable project operations. It should not merely summarize a "
        "generic codebase unless the repo itself provides a reusable workflow other agents can follow.\n\n"
        "Return JSON only, with this exact shape:\n"
        "{\n"
        '  "is_skill_candidate": true,\n'
        '  "confidence": "high|medium|low",\n'
        '  "reason": "short explanation",\n'
        '  "recommended_skill_name": "lowercase-hyphen-name or null",\n'
        '  "skill_md": "full SKILL.md content or null"\n'
        "}\n\n"
        "If is_skill_candidate is true, skill_md must be complete Markdown with YAML frontmatter. "
        "Use only these frontmatter fields: name and description. The description must clearly say "
        "when an agent should use the skill. Keep the body concise, procedural, and useful to another agent. "
        "Do not create README-style marketing copy.\n\n"
        "If is_skill_candidate is false, set recommended_skill_name and skill_md to null.\n\n"
        f"Repository analysis JSON:\n{json.dumps(payload, indent=2)}\n\n"
        f"Generated onboarding brief:\n{onboarding_brief}"
    )


def _analysis_payload(result: AnalysisResult) -> dict[str, object]:
    return {
        "repo_name": result.root.name,
        "total_files": result.total_files,
        "total_lines": result.total_lines,
        "languages": result.language_counts,
        "roles": result.role_counts,
        "frameworks": result.frameworks,
        "package_managers": result.package_managers,
        "entrypoints": result.entrypoints[:10],
        "config_files": result.config_files[:20],
        "test_files": result.test_files[:20],
        "risks": result.risks,
        "recommended_reading_path": result.recommended_path[:20],
        "important_symbols": [
            {
                "name": symbol.name,
                "kind": symbol.kind,
                "file": symbol.file,
                "line": symbol.line,
            }
            for symbol in result.symbols[:60]
        ],
        "largest_files": [
            {
                "path": file.relative_path,
                "lines": file.line_count,
                "bytes": file.size,
                "language": file.language,
            }
            for file in result.largest_files[:10]
        ],
        "selected_file_excerpts": [
            {
                "path": excerpt.file,
                "language": excerpt.language,
                "role": excerpt.role,
                "line_range": f"{excerpt.start_line}-{excerpt.end_line}",
                "truncated": excerpt.truncated,
                "content": excerpt.content,
            }
            for excerpt in result.file_excerpts
        ],
    }


def generate_ai_onboarding_brief(
    result: AnalysisResult,
    *,
    api_key: str | None = None,
    api_base: str = DEFAULT_API_BASE,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    timeout: int = 120,
) -> str:
    return _chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You create accurate codebase onboarding reports from grounded repository evidence.",
            },
            {"role": "user", "content": build_onboarding_prompt(result)},
        ],
        api_key=api_key,
        api_base=api_base,
        model=model,
        temperature=temperature,
        timeout=timeout,
    )


def assess_skill_candidate(
    result: AnalysisResult,
    onboarding_brief: str,
    *,
    api_key: str | None = None,
    api_base: str = DEFAULT_API_BASE,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    timeout: int = 120,
) -> SkillAssessment:
    content = _chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You evaluate whether repositories should become reusable agent skills and draft SKILL.md files.",
            },
            {"role": "user", "content": build_skill_assessment_prompt(result, onboarding_brief)},
        ],
        api_key=api_key,
        api_base=api_base,
        model=model,
        temperature=temperature,
        timeout=timeout,
    )
    return _parse_skill_assessment(content)


def _chat_completion(
    *,
    messages: list[dict[str, str]],
    api_key: str | None,
    api_base: str,
    model: str,
    temperature: float,
    timeout: int,
) -> str:
    api_key = api_key or os.environ.get("AI_API_KEY")
    if not api_key:
        raise AIClientError("AI_API_KEY is not set.")

    url = f"{api_base.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise AIClientError(f"AI provider HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AIClientError(f"AI provider request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AIClientError("AI provider request timed out.") from exc

    try:
        data = json.loads(raw)
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise AIClientError(f"Unexpected AI provider response: {raw[:500]}") from exc


def _parse_skill_assessment(content: str) -> SkillAssessment:
    raw = _extract_json_object(content)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIClientError(f"Skill assessment response was not valid JSON: {content[:500]}") from exc

    is_candidate = bool(data.get("is_skill_candidate"))
    confidence = str(data.get("confidence") or "low")
    reason = str(data.get("reason") or "No reason provided.")
    name = data.get("recommended_skill_name")
    skill_md = data.get("skill_md")

    if is_candidate and not skill_md:
        raise AIClientError("Skill assessment marked the repo as a skill candidate but did not return skill_md.")

    return SkillAssessment(
        is_skill_candidate=is_candidate,
        confidence=confidence,
        reason=reason,
        recommended_skill_name=str(name) if name else None,
        skill_md=str(skill_md) if skill_md else None,
    )


def _extract_json_object(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AIClientError(f"Skill assessment response did not contain a JSON object: {content[:500]}")
    return stripped[start : end + 1]
