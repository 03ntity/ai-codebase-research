# AI Codebase Onboarding Agent

AI Codebase Onboarding Agent is a Python CLI that turns an unfamiliar repository into a practical AI-written onboarding report. It scans the project locally, selects high-signal files, sends grounded context to an OpenAI-compatible model API, and writes a Markdown guide for new developers.

The project already supports end-to-end report generation, professional terminal logging, selective file reading, multi-language repository detection, and optional `SKILL.md` creation when the AI determines the target project can become a reusable agent skill.

<img width="1635" height="657" alt="image" src="https://github.com/user-attachments/assets/9f4a46b9-6b3d-4852-b9fb-bacaeb680a49" />


## What It Does

- Generates a clean onboarding report for a target repository.
- Detects project structure, entrypoints, manifests, configs, tests, frameworks, and package managers.
- Reads controlled excerpts from important files instead of sending the entire repo.
- Uses AI to explain architecture, execution flow, key files, risks, and a 30/60/90 minute onboarding path.
- Runs a second AI pass to decide whether the repository can become a reusable `SKILL.md`.
- Asks before writing `SKILL.md` into the analyzed project.

## Supported Project Types

The scanner is language-agnostic and recognizes common files from:

- Python
- JavaScript / TypeScript / React
- Rust
- Go
- Java / Kotlin
- C# / .NET
- PHP
- Ruby
- Swift
- Shell / PowerShell
- SQL
- HTML / CSS
- JSON / YAML / TOML / Markdown

## How It Works

1. **Discovery Agent** walks the repository and ignores generated/vendor folders such as `.git`, `node_modules`, `dist`, `build`, `.venv`, and `__pycache__`.
2. **Architecture Agent** detects entrypoints, frameworks, package managers, config files, test files, and major project modules.
3. **Code Understanding Agent** extracts symbols such as Python classes/functions, JS/TS exports, Go functions, Rust functions/types, and common class/function patterns in other languages.
4. **Context Selection Agent** reads controlled excerpts from high-signal files such as README files, manifests, entrypoints, configs, tests, and core source modules.
5. **Risk Agent** flags onboarding risks such as missing tests, missing README, unclear entrypoints, large files, TODO/FIXME markers, or committed environment files.
6. **Report Agent** sends the grounded context to the AI provider and writes a human-readable Markdown onboarding report.
7. **Skill Assessment Agent** asks the AI whether the target project can become a reusable `SKILL.md` for agent platforms such as Hermes, OpenClaw, Codex, or similar systems.

## Context Strategy

The agent does **not** send the whole repository to the model.

Instead, it selects a compact context package:

- repository metadata
- detected entrypoints
- frameworks and package managers
- important symbols
- onboarding risks
- recommended reading path
- selected file excerpts

Current excerpt limits:

```text
max 12 files
max 5,000 characters per file
max 30,000 characters total
```

This keeps reports useful while avoiding noisy full-repo dumps.

## Quick Start

PowerShell:

```powershell
cd D:\Portfolio\ai-codebase-research
$env:PYTHONPATH = "src"
$env:AI_API_KEY = "your_api_key_here"
python -m codebase_onboarding . --output reports/ai-onboarding.md
```

Analyze another repository:

```powershell
python -m codebase_onboarding "D:\Portfolio\monad-app" --output reports/monad-onboarding.md
```

After editable install:

```bash
python -m pip install -e .
AI_API_KEY=your_api_key_here codebase-onboard /path/to/repo --output reports/onboarding.md
```

## CLI

```bash
codebase-onboard TARGET_REPO --output reports/onboarding.md --max-file-size 250000
```

Options:

- `TARGET_REPO`: repository or folder to analyze.
- `--output`: Markdown report path. Defaults to `onboarding-report.md`.
- `--max-file-size`: skip files larger than this many bytes. Defaults to `250000`.
- `--include-hidden`: include hidden files and folders.
- `--temperature`: AI generation temperature. Defaults to `0.3`.

## Terminal Output

The CLI uses step-based logging and timing around AI calls. If `rich` is installed, output is rendered with panels, status spinners, and summary tables. If `rich` is unavailable, the CLI falls back to plain text logs.

Typical run:

```text
INFO  [1/5] Scanning repository
INFO  [2/5] Prepared 18 files for onboarding analysis
INFO  [3/5] Inferring repository structure
INFO  Selected 12 high-signal files for AI context
INFO  [4/5] Requesting onboarding brief from AI provider
OK    AI onboarding analysis completed in 34.1s
INFO  [5/5] Evaluating whether the project can become an agent skill
OK    AI skill assessment completed in 12.8s
```

## Skill Generation

After the onboarding report is written, the CLI performs a second AI pass to decide whether the project is suitable as an agent skill.

If suitable, the terminal shows the recommendation and asks:

```text
Create SKILL.md in the target project? [y/N]:
```

Answer `y` to write:

```text
TARGET_REPO/SKILL.md
```

If the target already has `SKILL.md`, the CLI asks before overwriting it. If the project is not suitable, the CLI prints the reason and does not create a skill file.

## AI Provider

The CLI uses an OpenAI-compatible chat completions endpoint internally and reads the API key from:

```text
AI_API_KEY
```

The provider name is intentionally abstracted in user-facing logs and reports. The app presents this as a generic AI provider integration.

## Tests

PowerShell:

```powershell
cd D:\Portfolio\ai-codebase-research
$env:PYTHONPATH = "src"
python -B -m unittest discover tests
```

Bash:

```bash
PYTHONPATH=src python -B -m unittest discover tests
```

Current test coverage includes:

- Python fixture analysis
- Go fixture analysis
- Rust fixture analysis
- AI prompt construction with selected file excerpts
- mocked AI report generation
- mocked `SKILL.md` creation flow

## Current Limitations

- The AI receives selected excerpts, not the entire repository.
- Deep semantic tracing across very large systems is not implemented yet.
- Symbol extraction is heuristic outside Python AST parsing.
- Dependency installation and runtime execution are not performed automatically.
- `SKILL.md` generation is AI-assisted and should be reviewed before use.

## Roadmap

- Add role-specific reports for backend, frontend, DevOps, and QA onboarding.
- Add optional dependency graph extraction.
- Add repository Q&A mode.
- Add deeper framework-specific analyzers.
- Add configurable context budgets.
- Add optional validation for generated `SKILL.md`.

## Submission Pitch

I built an AI-powered Codebase Onboarding Agent that helps developers understand unfamiliar repositories faster. The agent scans a codebase, infers architecture, detects frameworks and entrypoints, extracts important symbols, selects high-signal file excerpts, flags onboarding risks, and sends grounded repository evidence to an OpenAI-compatible model API using `gpt-5.4` to produce a natural-language onboarding brief.

The core logic is a multi-agent workflow: a Discovery Agent inventories files, an Architecture Agent maps frameworks and modules, a Code Understanding Agent extracts symbols, a Context Selection Agent selects important file excerpts, a Risk Agent identifies missing tests or unclear entrypoints, an AI Reasoning Agent writes a role-specific onboarding explanation, a Report Agent synthesizes the final guide, and a Skill Assessment Agent decides whether the project can be converted into a reusable `SKILL.md` for agent platforms such as Hermes, OpenClaw, and Codex.
