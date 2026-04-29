# Codebase Onboarding Report: ai-codebase-research

Generated: 2026-04-29 12:30 UTC

# 1. Architecture in plain English

This repository is a small Python CLI that turns a local codebase into an onboarding brief.

At a high level, it does four things:

1. **Scans the repository** to collect basic file-level facts such as paths, roles, and line counts.
2. **Analyzes those files** to infer useful structure: likely entrypoints, package manager, important symbols, and a recommended reading path.
3. **Builds an AI prompt and calls the AI provider** to turn that evidence into a human-readable onboarding brief.
4. **Writes the result as Markdown**.

The code is split cleanly by responsibility:

- **`scanner.py`**: walks the repo and classifies files.
- **`analyzers.py`**: derives higher-level insights from the scan.
- **`models.py`**: defines the data structures that move between scan, analysis, and reporting.
- **`ai_client.py`**: builds the prompt from repository evidence and performs the AI request.
- **`cli.py` / `__main__.py`**: user-facing command entry and argument handling.
- **`report.py`**: renders Markdown output.

A useful way to think about it: local repository inspection is the grounding step, and the AI layer is the final synthesis step that converts grounded evidence into onboarding guidance.

# 2. Request or execution flow, if inferable

The flow is fairly inferable from the symbol layout and tests:

1. **CLI starts** in `src/codebase_onboarding/__main__.py`, which likely delegates into `cli.py`.
2. **Argument parsing** happens in `build_parser()` and `main()` in `cli.py`.
3. **Repository scan** runs through `scan_repository()` in `scanner.py`.
   - Files are filtered with helpers like `_is_ignored()` and `_has_hidden_part()`.
   - Files are tagged by role with `classify_role()`.
4. **Analysis phase** runs through `analyze_repository()` in `analyzers.py`.
   - Detects entrypoints with `detect_entrypoints()`
   - Detects package-manager/framework hints
   - Extracts symbols with `extract_symbols()`
   - Builds a recommended reading order with `build_recommended_path()`
5. **AI prompt generation** happens in `build_onboarding_prompt()` in `ai_client.py`.
6. **AI-backed generation** runs via `generate_ai_onboarding_brief()`.
   - Failures are surfaced through `AIClientError`.
7. **Markdown rendering/output** is handled by `render_markdown_report()` in `report.py` and then written by the CLI.

The tests strongly suggest the intended behavior is end-to-end: scan a repo, analyze it, require AI generation, and write a report.

# 3. Most important files to read first

Read these in this order:

1. **`README.md`**  
   Start here for the intended user workflow and project purpose.

2. **`pyproject.toml`**  
   Confirms packaging, dependencies, and how the CLI is exposed.

3. **`src/codebase_onboarding/cli.py`**  
   Best first code file because it shows the real execution path and what the CLI considers required inputs and outputs.

4. **`src/codebase_onboarding/analyzers.py`**  
   This is the core “reasoning from evidence” module. It tells you what the tool actually infers from a repository and how opinionated the output can be.

5. **`src/codebase_onboarding/scanner.py`**  
   Read this next to understand the quality of the raw input data. If the scan is incomplete or overly filtered, every downstream result will be skewed.

6. **`src/codebase_onboarding/ai_client.py`**  
   Important because the current CLI requires AI generation through the configured provider. This file defines how repository evidence is packaged and sent to the model, and where failures or prompt-quality issues will show up.

7. **`src/codebase_onboarding/models.py`**  
   Helps you understand the shape of the data passed between modules.

8. **`tests/test_analysis.py`**  
   This is the fastest way to learn the contract the code is trying to keep, especially around prompt building and the requirement that the CLI uses AI generation.

9. **`tests/fixtures/demo_project/README.md`**, **`main.py`**, and **`onboarding-test-output.md`**  
   These give you a miniature example of input repo → expected onboarding output, which is very useful for understanding intent.

# 4. Risks and validation advice

## Main risks

- **The analysis is heuristic-driven.**  
  Functions like `detect_entrypoints()`, `detect_frameworks()`, `classify_role()`, and symbol extraction helpers are only as good as their assumptions. Small repos will work well; unusual layouts may not.

- **Prompt quality depends on scan quality.**  
  Since the AI brief is grounded in local repository inspection, bad filtering or weak symbol extraction will produce a polished but incomplete result.

- **AI integration is a hard dependency in the current CLI.**  
  If AI configuration, network access, or provider behavior changes, the CLI's main user path is affected.

- **Tests appear focused on happy-path behavior.**  
  From the visible names, there is good coverage for report generation and prompt construction, but less evidence of broader edge-case coverage for odd repository layouts or malformed files.

## What to validate first

- Run the tests in **`tests/test_analysis.py`** and treat them as the behavioral spec.
- Compare the demo fixture project with **`onboarding-test-output.md`** to understand what “good enough” output looks like.
- Inspect `analyzers.py` for assumptions about:
  - file naming
  - entrypoint detection
  - language-specific symbol extraction
  - ignored paths
- Inspect `ai_client.py` for:
  - expected request/response format
  - error handling through `AIClientError`
  - how much of the repository analysis is actually included in the prompt

## Good practical checks when changing code

- If you touch scanning, confirm the same fixture project still yields the same important symbols and reading order.
- If you touch prompt generation, diff the generated prompt rather than just the final Markdown.
- If you touch CLI behavior, re-check the test asserting that AI generation is required and that output is written successfully with a mocked provider.

# 5. A 30/60/90 minute onboarding plan

## First 30 minutes

- Read **`README.md`** and **`pyproject.toml`**.
- Open **`src/codebase_onboarding/cli.py`** and trace `main()`.
- Skim **`tests/test_analysis.py`** to understand the expected end-to-end behavior.
- Goal: know what the tool does, how it is invoked, and what the primary success path looks like.

## By 60 minutes

- Read **`scanner.py`** and **`analyzers.py`** carefully.
- Make a quick note of:
  - what gets scanned
  - what gets ignored
  - how entrypoints and symbols are inferred
  - where the recommended reading path comes from
- Then read **`models.py`** so the analysis pipeline objects make sense.
- Goal: understand how local repository evidence is gathered and shaped before the AI step.

## By 90 minutes

- Read **`ai_client.py`** and **`report.py`** end to end.
- Compare the fixture repo files with **`onboarding-test-output.md`**.
- Run or mentally simulate the full flow: CLI -> scan -> analyze -> prompt -> AI provider -> Markdown output.
- Pick one small improvement area to explore, such as:
  - making an analyzer rule more robust
  - improving prompt clarity
  - tightening error handling around AI failures
- Goal: be ready to safely make a small change without breaking the scan-to-brief pipeline.

## Agentic Workflow

This report was produced by an AI-driven onboarding workflow. The local discovery layer collects repository evidence, then the AI provider generates the human-readable onboarding brief from that grounded context.
