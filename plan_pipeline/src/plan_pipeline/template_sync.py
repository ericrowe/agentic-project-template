"""
Bidirectional Synchronization & GitHub Template Publisher for `agentic-project-template`.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from typing import Any, Dict, List, Optional

from .scaffolder import CANONICAL_IDEA_TRIAGE_SKILL_MD, CANONICAL_PLAN_PIPELINE_SKILL_MD
from .workspace import load_workspace_manifest


DEFAULT_GITHUB_TEMPLATE_REPO = "ericrowe/agentic-project-template"
DEFAULT_GITHUB_TEMPLATE_URL = f"https://github.com/{DEFAULT_GITHUB_TEMPLATE_REPO}.git"

UNIVERSAL_SKILLS: List[str] = [
    "plan-pipeline",
    "idea-triage",
    "security-auditor",
    "requirements-engineering",
    "cad-openscad",
    "cad-python",
    "cad-renderer",
    "mesh-auditor",
    "hardware-prototyper",
    "operational-cadence",
    "architecture-auditor",
    "learning-loop",
    "adversarial-debate",
    "benchmark-alpha",
]

SERVER_RACK_ONLY_SKILLS: List[str] = [
    "rack-ops",
    "personal-assistant-ops",
    "school-homework-tracker-ops",
    "project-router",
    "trade-decision-analyzer",
]


def _sanitize_skill_markdown(text: str) -> str:
    """Strip any Server-Rack-specific phrasing so exported skills are 100% project-agnostic."""
    out = text.replace("In the **Server Rack** master workspace,", "In this workspace,")
    out = out.replace("across all Server Rack sub-projects", "across all projects in the workspace")
    out = out.replace("for all sub-projects in the Server Rack workspace", "for all projects in the workspace")
    out = re.sub(r"tasker-pi(?:\.local)?", "app-host.local", out)
    return out


def _copy_or_extract_universal_skill(
    skill_name: str,
    workspace_root: Path,
    dest_skill_dir: Path,
) -> None:
    """Locate a universal skill in workspace_root, subprojects, or starter-kit archive and export cleanly."""
    dest_skill_dir.mkdir(parents=True, exist_ok=True)

    if skill_name == "plan-pipeline":
        (dest_skill_dir / "SKILL.md").write_text(CANONICAL_PLAN_PIPELINE_SKILL_MD, encoding="utf-8")
        return

    # 1. Check root .agents/skills/<skill_name>
    candidates = [
        workspace_root / ".agents" / "skills" / skill_name,
        workspace_root / "Trade-Execution-Engine" / ".agents" / "skills" / skill_name,
    ]
    for src_dir in candidates:
        if (src_dir / "SKILL.md").is_file():
            for item in src_dir.rglob("*"):
                if item.name.endswith(".metadata.json") or item.name == ".DS_Store":
                    continue
                rel = item.relative_to(src_dir)
                target_path = dest_skill_dir / rel
                if item.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    if item.suffix.lower() in (".md", ".py", ".sh"):
                        raw = item.read_text(encoding="utf-8", errors="ignore")
                        target_path.write_text(_sanitize_skill_markdown(raw), encoding="utf-8")
                    else:
                        shutil.copy2(item, target_path)
            return

    # 2. Check Trade-Execution-Engine/project-starter-kit.zip for hardware skills (cad-renderer, mesh-auditor, hardware-prototyper)
    starter_zip = workspace_root / "Trade-Execution-Engine" / "project-starter-kit.zip"
    if starter_zip.is_file():
        prefix = f"project-starter-kit/.agents/skills/{skill_name}/"
        with zipfile.ZipFile(starter_zip, "r") as zf:
            matched = [n for n in zf.namelist() if n.startswith(prefix) and not n.endswith("/")]
            if matched:
                for member in matched:
                    rel_str = member[len(prefix) :]
                    if rel_str.endswith(".metadata.json"):
                        continue
                    target_path = dest_skill_dir / rel_str
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    data = zf.read(member)
                    if target_path.suffix.lower() in (".md", ".py", ".sh"):
                        target_path.write_text(
                            _sanitize_skill_markdown(data.decode("utf-8", errors="ignore")),
                            encoding="utf-8",
                        )
                    else:
                        target_path.write_bytes(data)
                return

    # 3. Fallback minimal skill stub if neither exists
    if skill_name == "idea-triage":
        (dest_skill_dir / "SKILL.md").write_text(CANONICAL_IDEA_TRIAGE_SKILL_MD, encoding="utf-8")
    else:
        (dest_skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Universal {skill_name} engineering skill.\n---\n\n# {skill_name}\n",
            encoding="utf-8",
        )


TEMPLATE_INIT_PROJECT_PY = '''#!/usr/bin/env python3
"""Universal Agentic Project Template Initializer (`init_project.py`).

Supports both interactive wizard mode and non-interactive CLI mode:
  python3 init_project.py --non-interactive --name "My-Project" --domain 1 --author "Your Name"
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

DEFAULT_GITHUB_TEMPLATE_URL = "https://github.com/ericrowe/agentic-project-template.git"

DOMAIN_CHOICES = {
    "1": (
        "Pure Software Engineering",
        "Software Engineering",
        "Automated hermetic test suites (`./run_tests.sh`), API contracts, CI/CD pipelines, and zero-regression coverage ratchets.",
    ),
    "2": (
        "Physical Hardware & CAD Prototyping",
        "Hardware Prototyping",
        "Dual OpenSCAD (`.scad`) & Python CAD (`build123d`/STL) modeling, mesh manifoldness validation, and tolerance ladders.",
    ),
    "3": (
        "Algorithmic Trading & Quantitative Finance",
        "Algorithmic Trading",
        "Quantitative signal generation, backtesting, benchmark alpha outperformance mandates, and hard risk-manager guardrails.",
    ),
    "4": (
        "Cyber-Physical / Embedded / Hybrid",
        "Cyber-Physical Hybrid",
        "Integrated software stack with physical CAD enclosures, embedded firmware (`secrets.h` isolation), and hardware prototyping.",
    ),
}


def configure_template(
    root: Path,
    project_name: str,
    domain_key: str = "1",
    author: str = "Engineering Team",
    description: str = "AI-assisted engineering repository governed by the 5-step Plan Pipeline.",
) -> None:
    domain_title, domain_short, domain_focus = DOMAIN_CHOICES.get(domain_key, DOMAIN_CHOICES["1"])

    # 1. Update plan-pipeline.yaml
    manifest_path = root / "plan-pipeline.yaml"
    manifest_path.write_text(
        f"""{{
  "version": "1.0",
  "name": "{project_name}",
  "domain": "{domain_short}",
  "author": "{author}",
  "mode": "single-project",
  "plans_dir": "docs/plans",
  "prefix": "",
  "test_command": "./run_tests.sh",
  "template_repo": "{DEFAULT_GITHUB_TEMPLATE_URL}"
}}
""",
        encoding="utf-8",
    )

    # 2. Update AGENTS.md header
    agents_path = root / "AGENTS.md"
    if agents_path.exists():
        text = agents_path.read_text(encoding="utf-8")
        text = text.replace("Universal Agentic Project Template", project_name)
        text = text.replace(
            "{{PROJECT_DESCRIPTION}}",
            f"**Domain**: {domain_title} — {description}\\n\\n**Primary Engineering Focus**: {domain_focus}",
        )
        agents_path.write_text(text, encoding="utf-8")

    # 3. Update docs/plans/AGENTS.md header
    plans_agents = root / "docs" / "plans" / "AGENTS.md"
    if plans_agents.exists():
        ptext = plans_agents.read_text(encoding="utf-8")
        ptext = ptext.replace("Universal Agentic Project Template", project_name)
        plans_agents.write_text(ptext, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize the Universal Agentic Project Template.")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts")
    parser.add_argument("--name", default="My-Agentic-Project", help="Project name")
    parser.add_argument("--domain", default="1", choices=["1", "2", "3", "4"], help="Domain profile (1..4)")
    parser.add_argument("--author", default="Engineering Team", help="Author or organization")
    parser.add_argument(
        "--description",
        default="AI-assisted engineering project governed by the 5-step Plan Pipeline.",
        help="Short project description",
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent

    if args.non_interactive:
        configure_template(
            root=root,
            project_name=args.name,
            domain_key=args.domain,
            author=args.author,
            description=args.description,
        )
        print(f"Configured project '{args.name}' (domain={args.domain}).")
        return 0

    print("=" * 70)
    print("   UNIVERSAL AGENTIC PROJECT TEMPLATE INITIALIZER")
    print("=" * 70)
    project_name = input(f"Project Name [{args.name}]: ").strip() or args.name
    print("\\nSelect Domain Profile:")
    for k, (title, _, _) in DOMAIN_CHOICES.items():
        print(f"  [{k}] {title}")
    domain_key = input(f"Domain [1-4, default={args.domain}]: ").strip() or args.domain
    author = input(f"Author [{args.author}]: ").strip() or args.author
    description = input(f"Description [{args.description}]: ").strip() or args.description

    configure_template(
        root=root,
        project_name=project_name,
        domain_key=domain_key,
        author=author,
        description=description,
    )
    print(f"\\nSuccessfully initialized {project_name}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def export_template_repository(workspace_root: Path, target_dir: Path) -> Dict[str, Any]:
    """
    Assemble a complete, standalone, self-tested GitHub Template Repository in `target_dir`:
    - 14 universal `.agents/skills/`
    - 6 AI assistant pointer files (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `CODEX.md`, `.cursorrules`, `.windsurfrules`, `.github/copilot-instructions.md`)
    - `plan_pipeline/` package + `scripts/plan_pipeline.py`
    - `docs/plans/AGENTS.md`, `docs/plans/IDEAS.md`, `docs/plans/01_initial_architecture_plan.md`, `docs/plans/complete/`
    - `docs/TEST_COVERAGE_METRICS.md`, `init_project.py`, `run_tests.sh`, `.github/workflows/ci.yml`, and `tests/test_template_integrity.py`
    """
    workspace_root = Path(workspace_root).resolve()
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Export all 14 universal skills
    skills_root = target_dir / ".agents" / "skills"
    for skill_name in UNIVERSAL_SKILLS:
        _copy_or_extract_universal_skill(skill_name, workspace_root, skills_root / skill_name)

    # 2. Export plugin.json
    plugin_dir = target_dir / ".agents" / "plugins" / "project-tools"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "name": "project-tools",
                "version": "1.0.0",
                "description": "Universal Agentic Plan Pipeline & Multi-Domain Engineering Skills Suite",
                "skills": UNIVERSAL_SKILLS,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # 3. Copy `plan_pipeline/` package & `scripts/plan_pipeline.py`
    src_pkg = workspace_root / "plan_pipeline"
    dst_pkg = target_dir / "plan_pipeline"
    if dst_pkg.exists():
        shutil.rmtree(dst_pkg)
    shutil.copytree(
        src_pkg,
        dst_pkg,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info", ".DS_Store"),
    )

    scripts_dir = target_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workspace_root / "scripts" / "plan_pipeline.py", scripts_dir / "plan_pipeline.py")

    # 4. Write `plan-pipeline.yaml`, `init_project.py`, `run_tests.sh`, `.gitignore`
    (target_dir / "plan-pipeline.yaml").write_text(
        json.dumps(
            {
                "version": "1.0",
                "name": "Universal Agentic Project Template",
                "mode": "single-project",
                "plans_dir": "docs/plans",
                "prefix": "",
                "test_command": "./run_tests.sh",
                "template_repo": DEFAULT_GITHUB_TEMPLATE_URL,
                "universal_skills": UNIVERSAL_SKILLS,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    init_py = target_dir / "init_project.py"
    init_py.write_text(TEMPLATE_INIT_PROJECT_PY, encoding="utf-8")
    init_py.chmod(init_py.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    run_tests_sh = target_dir / "run_tests.sh"
    run_tests_sh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
else
    PYTHON_BIN="python3"
fi

if "$PYTHON_BIN" -c "import pytest" >/dev/null 2>&1; then
    "$PYTHON_BIN" -m pytest "${@:-tests/}"
else
    "$PYTHON_BIN" -m unittest discover -s tests -v
fi
""",
        encoding="utf-8",
    )
    run_tests_sh.chmod(run_tests_sh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    (target_dir / ".gitignore").write_text(
        """__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/
*.db
*.sqlite3
.env
*secrets.h
.DS_Store
._*
""",
        encoding="utf-8",
    )

    # 5. Write `README.md`, `AGENTS.md`, and 6 compatibility pointers
    (target_dir / "README.md").write_text(
        f"""# Universal Agentic Project Template (`plan-pipeline`)

A production-tested, multi-agent project template and CLI framework for **Software Engineering**, **Quantitative / Algorithmic Systems**, and **Physical Hardware & CAD Prototyping**.

Out-of-the-box support for:
- **Google Antigravity & Gemini CLI** ([`AGENTS.md`](./AGENTS.md), [`GEMINI.md`](./GEMINI.md), [`.agents/skills/`](./.agents/skills/))
- **Anthropic Claude Code** ([`CLAUDE.md`](./CLAUDE.md))
- **OpenAI Codex** ([`CODEX.md`](./CODEX.md))
- **Cursor IDE** ([`.cursorrules`](./.cursorrules))
- **Windsurf / Codeium** ([`.windsurfrules`](./.windsurfrules))
- **GitHub Copilot** ([`.github/copilot-instructions.md`](./.github/copilot-instructions.md))

---

## Quickstart ("Use this template")

1. Click **"Use this template" $\\rightarrow$ "Create a new repository"** on GitHub (or run `gh repo create my-project --template {DEFAULT_GITHUB_TEMPLATE_REPO} --clone`).
2. Run the project initializer wizard:
   ```bash
   python3 init_project.py
   ```
3. Inspect the plan pipeline status, validate plans, scaffold a new plan, or run tests:
   ```bash
   python3 scripts/plan_pipeline.py status
   python3 scripts/plan_pipeline.py validate --all
   python3 scripts/plan_pipeline.py new --id 02 --slug my_feature --title "My Feature"
   ./run_tests.sh
   ```

---

## Synchronizing with Downstream Projects (`sync-template`)

- **All Downstream Projects (`--pull`)**: Any repository created from this template can pull the latest universal `.agents/skills/` and `plan_pipeline` CLI updates over public HTTPS with zero authentication required:
  ```bash
  python3 scripts/plan_pipeline.py sync-template --pull
  ```
- **Template Maintainer / Fork Owners (`--push`)**: If you maintain this template (or your own fork via `--repo <owner>/<repo>`), export and push generalized skill/CLI improvements over SSH:
  ```bash
  python3 scripts/plan_pipeline.py sync-template --push --repo {DEFAULT_GITHUB_TEMPLATE_REPO}
  ```
""",
        encoding="utf-8",
    )

    agents_md_content = """# Universal Agentic Project Template — Workspace Agent Directives

{{PROJECT_DESCRIPTION}}

Refer to [`.agents/skills/plan-pipeline/SKILL.md`](./.agents/skills/plan-pipeline/SKILL.md) and [`docs/plans/AGENTS.md`](./docs/plans/AGENTS.md) for the mandatory 5-step plan-driven development lifecycle.

---

## Core Engineering Invariants

1. **5-Step Plan-Driven Lifecycle & 7 Mandatory Sections**:
   - All features, bug fixes, and refactors follow: **Step 0** (`docs/plans/IDEAS.md` intake) $\\rightarrow$ **Step 1** (`docs/plans/NN_<name>_plan.md` with 7 mandatory sections) $\\rightarrow$ **Step 2** (HITL approval) $\\rightarrow$ **Step 3** (3-Phase RED/GREEN/Regression TDD execution) $\\rightarrow$ **Step 4** (Interactive user validation) $\\rightarrow$ **Step 5** (`python3 scripts/plan_pipeline.py archive` + coverage ratchet check + Git commit).
2. **Questions vs. Action Directives (Mandatory Plan Gate)**:
   - If the user asks a question, provide analysis and options without modifying files. If the user directs an implementation and no approved plan exists yet, enter **Step 1** first.
3. **Minimal Blast Radius & Root-Cause Resolution**:
   - Diagnose and fix fundamental root causes; keep changes small, targeted, and auditable.
4. **System & Data Safety (Pre-Execution Explanation)**:
   - Before running state-mutating commands, explain **What**, **Why**, and **Impact**.
5. **Native Edit Tool Invariant**:
   - Always use native file editing tools rather than shell `cat << 'EOF'` stream redirection.
6. **Zero Hardcoded Machine Paths & 100% Portable Relative Links**:
   - Never commit `/Volumes/`, `/Users/`, or `file:///` paths; all markdown links must resolve on disk.
7. **Continuous Coverage Ratchet (`docs/TEST_COVERAGE_METRICS.md`)**:
   - No plan or refactor may decrease statement coverage %, branch coverage %, or verified behavioral invariants.
8. **Universal Test-First & Red-Green Regression Gating**:
   - Bug fixes require a failing reproduction test (RED) before the fix (GREEN).
9. **Mid-Plan Planning Request Disambiguation Invariant**:
   - If an active plan is in Step 3 or Step 4 and a new task is requested, ask:
     > *"We are currently in the middle of implementing Plan `<ID>`. Would you like me to add this new request as an idea in `<project>/docs/plans/IDEAS.md` (to preserve a clean commit history and complete the current plan first), or would you prefer to pause/switch and formulate it as a full-fledged plan right now?"*
10. **Tiered Test Execution & Coverage Measurement Efficiency Invariant**:
    - **Code vs. Documentation Gate**: Only run tests when executable code, scripts, or configurations change.
    - **Coverage Measurement Gate**: Skip re-measuring coverage when no code or test files changed.
11. **Unrelated Test Failure Handling Protocol (Fail-Fast & Defer)**:
    - Do not fix unrelated test failures mid-plan; notify the user and log an entry in `docs/plans/IDEAS.md`.
"""
    (target_dir / "AGENTS.md").write_text(agents_md_content, encoding="utf-8")

    pointer_text = """# AI Assistant Directives

Refer to [`AGENTS.md`](./AGENTS.md), [`docs/plans/AGENTS.md`](./docs/plans/AGENTS.md), and [`.agents/skills/plan-pipeline/SKILL.md`](./.agents/skills/plan-pipeline/SKILL.md) for all workspace directives and skills.

- **5-Step Plan Lifecycle**: Every code change requires a 7-section plan in `docs/plans/NN_<name>_plan.md` approved before implementation.
- **Standardized Scripts**: Use `./run_tests.sh` and `python3 scripts/plan_pipeline.py status | validate | new | archive`.
- **Mid-Plan Planning Request Disambiguation**: Ask whether new mid-flight requests should be added to `docs/plans/IDEAS.md` or pause the current plan.
- **Tiered Test Execution**: Run tests only when code/scripts change; skip on documentation-only edits.
- **Unrelated Test Failure Protocol**: Fail-fast and defer unrelated test failures to `docs/plans/IDEAS.md`.
"""
    for pfile in ("GEMINI.md", "CLAUDE.md", "CODEX.md", ".cursorrules", ".windsurfrules"):
        (target_dir / pfile).write_text(pointer_text, encoding="utf-8")

    gh_dir = target_dir / ".github" / "workflows"
    gh_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / ".github" / "copilot-instructions.md").write_text(
        pointer_text.replace("(./", "(../"),
        encoding="utf-8",
    )

    (gh_dir / "ci.yml").write_text(
        """name: Plan Pipeline & Hermetic Tests

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  validate-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install pytest
        run: python -m pip install --upgrade pip pytest
      - name: Validate active plans (7 sections & portable links)
        run: python3 scripts/plan_pipeline.py validate --all
      - name: Run hermetic test suite
        run: ./run_tests.sh
""",
        encoding="utf-8",
    )

    # 6. Create `docs/plans/` and `docs/TEST_COVERAGE_METRICS.md`
    plans_dir = target_dir / "docs" / "plans"
    (plans_dir / "complete").mkdir(parents=True, exist_ok=True)
    (plans_dir / "complete" / ".gitkeep").write_text("", encoding="utf-8")

    (plans_dir / "AGENTS.md").write_text(
        """# Master Plan Registry & Active Queue (Universal Agentic Project Template)

## 1. Prioritized Active Execution Queue

| Priority | Plan ID | Title | Status |
| :---: | :---: | :--- | :---: |
| **P1** | **01** | Initial Architecture & Plan Pipeline Bootstrap ([`docs/plans/01_initial_architecture_plan.md`](01_initial_architecture_plan.md)) | `PROPOSED` |

---

## 2. Master Plan Registry

- **`01`**: Initial Architecture & Plan Pipeline Bootstrap ([`docs/plans/01_initial_architecture_plan.md`](01_initial_architecture_plan.md)) (`PROPOSED`)
""",
        encoding="utf-8",
    )

    (plans_dir / "IDEAS.md").write_text(
        """# Idea & Bug Intake Backlog

Add raw feature ideas, architectural notes, and bug reports below for interactive triage ([`.agents/skills/idea-triage/SKILL.md`](../../.agents/skills/idea-triage/SKILL.md)) into numbered plans.
""",
        encoding="utf-8",
    )

    (plans_dir / "01_initial_architecture_plan.md").write_text(
        """# Plan 01: Initial Architecture & Plan Pipeline Bootstrap

## 1. Goal Description

Initialize the repository domain profile, establish baseline architecture and test coverage, and verify the 5-step Plan Pipeline workflow.

---

## 2. Architecture & Workflow Diagram

```mermaid
flowchart LR
    Init["python3 init_project.py"] --> Plan["Step 1-2: Plan & HITL Approval"]
    Plan --> TDD["Step 3: 3-Phase RED/GREEN/Regression TDD"]
    TDD --> Archive["Step 4-5: Validation & plan_pipeline.py archive"]
```

---

## 3. Code Modifications

- **`[MODIFY]`** [`AGENTS.md`](../../AGENTS.md): Configure project domain and architecture overview.
- **`[MODIFY]`** [`plan-pipeline.yaml`](../../plan-pipeline.yaml): Set project name and test runner command.

---

## 4. Test Updates & Specifications

- **`[MODIFY]`** [`tests/test_template_integrity.py`](../../tests/test_template_integrity.py): Verify all universal skills, pointer files, and plan validation rules pass.

---

## 5. Documentation Updates

- **`[MODIFY]`** [`README.md`](../../README.md): Document project setup and architecture.

---

## 6. Verification Plan

### Automated Tests
```bash
./run_tests.sh
python3 scripts/plan_pipeline.py validate --all
```

### Manual Verification
1. Run `python3 scripts/plan_pipeline.py status` and confirm `Plan 01` is listed as `VALID`.
""",
        encoding="utf-8",
    )

    (target_dir / "docs" / "TEST_COVERAGE_METRICS.md").write_text(
        """# Test & Behavior Coverage Scorecard

| Subsystem | Test Suite Path | Tests | Statements Covered (%) | Branches Covered (%) | Critical Invariants Verified (%) | Target Goal | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Core Repository** | `tests/` | 4 | 90% | 85% | 100% | $\\ge 85\\%$ | Verified |

---

## Historical Milestone Log

| Date | Milestone / Plan | Total Tests | Stmt Cov (%) | Branch Cov (%) | Invariants (%) | Notes |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **2026-11-17** | Plan 01 (Initial Template Baseline) | 4 | 90% | 85% | 100% | Initial baseline established from `agentic-project-template`. |
""",
        encoding="utf-8",
    )

    # 7. Create hermetic self-test suite `tests/test_template_integrity.py` (compatible with both pytest and unittest)
    tests_dir = target_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_template_integrity.py").write_text(
        """from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_PIPELINE_SRC = REPO_ROOT / "plan_pipeline" / "src"
if str(PLAN_PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(PLAN_PIPELINE_SRC))

from plan_pipeline.schema import validate_plan_file
from plan_pipeline.template_sync import UNIVERSAL_SKILLS
from plan_pipeline.workspace import discover_workspace_status


class TestTemplateIntegrity(unittest.TestCase):
    def test_all_universal_skills_present_and_valid(self):
        skills_dir = REPO_ROOT / ".agents" / "skills"
        for skill in UNIVERSAL_SKILLS:
            skill_md = skills_dir / skill / "SKILL.md"
            self.assertTrue(skill_md.is_file(), f"Missing skill: {skill}")
            content = skill_md.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---"), f"Missing YAML frontmatter in {skill}")
            self.assertIn("description:", content)

    def test_all_assistant_pointers_present(self):
        for pointer in (
            "AGENTS.md",
            "GEMINI.md",
            "CLAUDE.md",
            "CODEX.md",
            ".cursorrules",
            ".windsurfrules",
            ".github/copilot-instructions.md",
        ):
            p = REPO_ROOT / pointer
            self.assertTrue(p.is_file(), f"Missing pointer file: {pointer}")
            self.assertIn("AGENTS.md", p.read_text(encoding="utf-8"))

    def test_initial_plan_and_workspace_status_valid(self):
        plan_file = REPO_ROOT / "docs" / "plans" / "01_initial_architecture_plan.md"
        res = validate_plan_file(plan_file, workspace_root=REPO_ROOT)
        self.assertTrue(res.is_valid, f"Initial plan invalid: {res.errors}")

        status = discover_workspace_status(REPO_ROOT)
        self.assertGreaterEqual(len(status["root"]["active_plans"]), 1)


if __name__ == "__main__":
    unittest.main()
""",
        encoding="utf-8",
    )

    return {
        "target_dir": str(target_dir),
        "skills_exported": len(UNIVERSAL_SKILLS),
        "universal_skills": list(UNIVERSAL_SKILLS),
    }


def pull_from_template_repository(
    workspace_root: Path,
    source: str | Path = DEFAULT_GITHUB_TEMPLATE_URL,
) -> Dict[str, Any]:
    """
    Pull updated universal skills and `plan_pipeline/` core package from a local template directory
    or remote Git URL (`https://github.com/ericrowe/agentic-project-template.git`) into `workspace_root`,
    while preserving workspace-only skills (`rack-ops`, etc.) and root `AGENTS.md` topology.
    """
    workspace_root = Path(workspace_root).resolve()
    temp_clone_dir: Optional[Path] = None

    try:
        source_str = str(source)
        if source_str.startswith(("http://", "https://", "git@")) or source_str.endswith(".git"):
            temp_clone_dir = Path(tempfile.mkdtemp(prefix="plan_pipeline_pull_"))
            subprocess.run(
                ["git", "clone", "--depth", "1", source_str, str(temp_clone_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            template_dir = temp_clone_dir
        else:
            template_dir = Path(source_str).resolve()

        if not template_dir.is_dir():
            raise FileNotFoundError(f"Template source directory not found: {template_dir}")

        # 1. Sync universal skills into workspace_root/.agents/skills/
        synced_skills: List[str] = []
        src_skills_root = template_dir / ".agents" / "skills"
        dst_skills_root = workspace_root / ".agents" / "skills"
        dst_skills_root.mkdir(parents=True, exist_ok=True)

        for skill_name in UNIVERSAL_SKILLS:
            if skill_name in SERVER_RACK_ONLY_SKILLS:
                continue
            src_skill = src_skills_root / skill_name
            if not (src_skill / "SKILL.md").is_file():
                continue
            dst_skill = dst_skills_root / skill_name
            if dst_skill.exists():
                shutil.rmtree(dst_skill)
            shutil.copytree(src_skill, dst_skill)
            synced_skills.append(skill_name)

        # 2. Sync `plan_pipeline/` package if present in template_dir
        src_pkg = template_dir / "plan_pipeline"
        dst_pkg = workspace_root / "plan_pipeline"
        if (src_pkg / "pyproject.toml").is_file() and src_pkg.resolve() != dst_pkg.resolve():
            if dst_pkg.exists():
                shutil.rmtree(dst_pkg)
            shutil.copytree(
                src_pkg,
                dst_pkg,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info", ".DS_Store"),
            )

        return {
            "workspace_root": str(workspace_root),
            "source": source_str,
            "skills_synced": len(synced_skills),
            "synced_skills": synced_skills,
        }
    finally:
        if temp_clone_dir and temp_clone_dir.exists():
            shutil.rmtree(temp_clone_dir, ignore_errors=True)


def _get_github_credentials() -> tuple[Optional[str], Optional[str]]:
    """Retrieve GitHub username and personal access token from env (`GITHUB_TOKEN`/`GH_TOKEN`), `gh auth token`, or `git credential fill`."""
    env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env_token:
        return os.environ.get("GITHUB_USER", "ericrowe"), env_token.strip()

    if shutil.which("gh"):
        gh_proc = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=False,
        )
        if gh_proc.returncode == 0 and gh_proc.stdout.strip():
            return "ericrowe", gh_proc.stdout.strip()

    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    username = None
    password = None
    for line in proc.stdout.splitlines():
        if line.startswith("username="):
            username = line.split("=", 1)[1].strip()
        elif line.startswith("password="):
            password = line.split("=", 1)[1].strip()
    return username, password


def _ensure_github_template_repo(
    repo_slug: str,
    token: str,
    is_public: bool = True,
    is_template: bool = True,
) -> Dict[str, Any]:
    """Create or update `repo_slug` on GitHub with `is_template: true` via GitHub REST API."""
    owner, repo_name = repo_slug.split("/", 1)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "plan-pipeline-publisher/1.0",
    }
    description = (
        "Universal Agentic Project Template: 5-step Plan Pipeline, 7-section validator, "
        "Step 5 link-safe archiver, and 14 modular AI coding skills."
    )

    repo_url = f"https://api.github.com/repos/{owner}/{repo_name}"
    req_get = urllib.request.Request(repo_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req_get, timeout=15) as resp:
            existing = json.loads(resp.read().decode("utf-8"))
        # Ensure `is_template` and visibility match requested settings
        patch_payload = json.dumps(
            {
                "name": repo_name,
                "description": description,
                "private": not is_public,
                "is_template": is_template,
            }
        ).encode("utf-8")
        req_patch = urllib.request.Request(repo_url, data=patch_payload, headers=headers, method="PATCH")
        with urllib.request.urlopen(req_patch, timeout=15) as resp_patch:
            return json.loads(resp_patch.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        create_payload = json.dumps(
            {
                "name": repo_name,
                "description": description,
                "private": not is_public,
                "is_template": is_template,
                "auto_init": False,
            }
        ).encode("utf-8")
        req_post = urllib.request.Request(
            "https://api.github.com/user/repos",
            data=create_payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req_post, timeout=15) as resp_post:
            return json.loads(resp_post.read().decode("utf-8"))


def _git_commit_cmd(repo_dir: Path, commit_message: str, env: Dict[str, str]) -> List[str]:
    """Build a git commit command, falling back to local identity only if git user.name/email are unset."""
    has_name = subprocess.run(
        ["git", "config", "user.name"], cwd=str(repo_dir), env=env, capture_output=True, text=True
    ).returncode == 0
    has_email = subprocess.run(
        ["git", "config", "user.email"], cwd=str(repo_dir), env=env, capture_output=True, text=True
    ).returncode == 0
    cmd = ["git"]
    if not has_name:
        cmd.extend(["-c", "user.name=plan-pipeline"])
    if not has_email:
        cmd.extend(["-c", "user.email=plan-pipeline@local"])
    cmd.extend(["commit", "-m", commit_message])
    return cmd


def _push_export_preserving_history(
    export_dir: Path,
    remote_url: str,
    commit_message: str,
) -> Dict[str, Any]:
    """
    Push `export_dir` to `remote_url` on `main` while preserving commit history when `refs/heads/main` exists.
    Never mutates `export_dir` and never silently falls back on auth/network/404 or non-`main` branch errors.
    """
    export_dir = Path(export_dir).resolve()
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    ls_res = subprocess.run(
        ["git", "ls-remote", "--heads", remote_url],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    head_lines = [line.strip() for line in ls_res.stdout.splitlines() if line.strip()]
    has_main = any(line.endswith("\trefs/heads/main") or line.endswith(" refs/heads/main") for line in head_lines)
    if head_lines and not has_main:
        raise RuntimeError(f"Remote {remote_url} has existing branches but no 'main' branch: {head_lines}")

    ignore_fn = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.pyo", "._*")
    repo_dir = Path(tempfile.mkdtemp(prefix="agentic_template_repo_"))
    try:
        if has_main:
            subprocess.run(
                ["git", "clone", "--branch", "main", "--single-branch", remote_url, str(repo_dir)],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            for entry in list(repo_dir.iterdir()):
                if entry.name == ".git":
                    continue
                if entry.is_symlink() or not entry.is_dir():
                    entry.unlink()
                else:
                    shutil.rmtree(entry)
            shutil.copytree(export_dir, repo_dir, dirs_exist_ok=True, ignore=ignore_fn)
            subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), env=env, check=True, capture_output=True)
            status_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(repo_dir),
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            if not status_res.stdout.strip():
                return {"pushed": False, "up_to_date": True}
            subprocess.run(
                _git_commit_cmd(repo_dir, commit_message, env),
                cwd=str(repo_dir),
                env=env,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=str(repo_dir),
                env=env,
                check=True,
                capture_output=True,
            )
            return {"pushed": True, "up_to_date": False}

        # Truly empty remote: initialize main in repo_dir and push initial commit
        subprocess.run(["git", "init", "-b", "main"], cwd=str(repo_dir), env=env, check=True, capture_output=True)
        shutil.copytree(export_dir, repo_dir, dirs_exist_ok=True, ignore=ignore_fn)
        subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), env=env, check=True, capture_output=True)
        subprocess.run(
            _git_commit_cmd(repo_dir, commit_message, env),
            cwd=str(repo_dir),
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", remote_url],
            cwd=str(repo_dir),
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=str(repo_dir),
            env=env,
            check=True,
            capture_output=True,
        )
        return {"pushed": True, "up_to_date": False}
    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)


def publish_template_to_github(
    workspace_root: Path,
    repo_slug: str = DEFAULT_GITHUB_TEMPLATE_REPO,
    is_public: bool = True,
    is_template: bool = True,
    commit_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Export the standalone template repository from `workspace_root`, verify its self-tests pass,
    create/configure the GitHub repository with `is_template: true`, and push `main` preserving history.
    """
    effective_message = (
        commit_message.strip()
        if isinstance(commit_message, str) and commit_message.strip()
        else "feat: publish Universal Agentic Project Template with 5-step plan-pipeline"
    )
    workspace_root = Path(workspace_root).resolve()
    staging_dir = Path(tempfile.mkdtemp(prefix="agentic_project_template_"))
    try:
        export_info = export_template_repository(workspace_root, staging_dir)

        # Run zero-dependency self-tests before pushing
        subprocess.run(
            [os.sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=str(staging_dir),
            check=True,
            capture_output=True,
            text=True,
        )

        _, token = _get_github_credentials()
        if token:
            gh_meta = _ensure_github_template_repo(
                repo_slug=repo_slug,
                token=token,
                is_public=is_public,
                is_template=is_template,
            )
            remote_url = f"https://github.com/{repo_slug}.git"
        else:
            # SSH push fallback (no token needed once the repository exists on GitHub)
            gh_meta = {
                "html_url": f"https://github.com/{repo_slug}",
                "is_template": is_template,
                "private": not is_public,
            }
            remote_url = f"git@github.com:{repo_slug}.git"

        push_res = _push_export_preserving_history(staging_dir, remote_url, effective_message)

        manifest_path = workspace_root / "plan-pipeline.yaml"
        manifest = load_workspace_manifest(manifest_path) if manifest_path.is_file() else {}
        skills = manifest.get("universal_skills") if isinstance(manifest.get("universal_skills"), list) else UNIVERSAL_SKILLS
        record_template_publish_state(workspace_root, compute_template_content_digest(workspace_root, skills))

        return {
            "html_url": gh_meta.get("html_url", f"https://github.com/{repo_slug}"),
            "is_template": gh_meta.get("is_template", is_template),
            "private": gh_meta.get("private", not is_public),
            "skills_exported": export_info["skills_exported"],
            "pushed": push_res["pushed"],
            "up_to_date": push_res["up_to_date"],
        }
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


TEMPLATE_SYNC_STATE_REL = Path(".git") / "plan_pipeline_template_sync.json"
_DIGEST_IGNORED_PARTS = {"__pycache__", ".DS_Store"}
_DIGEST_IGNORED_SUFFIXES = (".pyc", ".pyo", ".metadata.json")


def _is_truthy_flag(val: Any) -> bool:
    """Strictly coerce boolean or fallback YAML string flags without treating 'false' as truthy."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return False


def _should_ignore_digest_path(rel_path: Path) -> bool:
    """Return True if a path should be excluded from template drift hashing."""
    for part in rel_path.parts:
        if part in _DIGEST_IGNORED_PARTS or part.startswith("._") or part.endswith(".egg-info"):
            return True
    name = rel_path.name
    return name.endswith(_DIGEST_IGNORED_SUFFIXES)


def _hash_tree(hasher: "hashlib._Hash", base_dir: Path, label: str) -> None:
    """Deterministically feed sorted file paths and contents from base_dir into hasher."""
    if not base_dir.is_dir():
        return
    for item in sorted(base_dir.rglob("*")):
        if not item.is_file():
            continue
        rel = item.relative_to(base_dir)
        if _should_ignore_digest_path(rel):
            continue
        hasher.update(f"{label}/{rel.as_posix()}\n".encode("utf-8"))
        hasher.update(item.read_bytes())


def compute_template_content_digest(
    workspace_root: Path,
    universal_skills: Optional[List[str]] = None,
) -> str:
    """Compute a deterministic SHA-256 digest of template-synced files in workspace_root."""
    workspace_root = Path(workspace_root).resolve()
    skills = universal_skills if universal_skills is not None else UNIVERSAL_SKILLS
    hasher = hashlib.sha256()

    _hash_tree(hasher, workspace_root / "plan_pipeline" / "src", "plan_pipeline/src")
    for rel_str in ("plan_pipeline/pyproject.toml", "plan_pipeline/README.md", "scripts/plan_pipeline.py"):
        p = workspace_root / rel_str
        if p.is_file():
            hasher.update(f"{rel_str}\n".encode("utf-8"))
            hasher.update(p.read_bytes())

    for skill_name in sorted(skills):
        skill_dir = workspace_root / ".agents" / "skills" / skill_name
        if skill_dir.is_dir():
            _hash_tree(hasher, skill_dir, f".agents/skills/{skill_name}")

    return hasher.hexdigest()


def record_template_publish_state(workspace_root: Path, digest: str) -> None:
    """Persist the last-published template digest inside .git/ (no-op if .git/ is absent)."""
    workspace_root = Path(workspace_root).resolve()
    if not (workspace_root / ".git").is_dir():
        return
    state_path = workspace_root / TEMPLATE_SYNC_STATE_REL
    state_path.write_text(json.dumps({"digest": digest}, indent=2), encoding="utf-8")


def check_template_publish_drift(workspace_root: Path) -> Optional[Dict[str, Any]]:
    """
    Return drift status dict if template_publish_check is enabled and .git/ exists,
    otherwise return None (complete no-op for external/downstream users).
    """
    workspace_root = Path(workspace_root).resolve()
    manifest_path = workspace_root / "plan-pipeline.yaml"
    if not manifest_path.is_file():
        return None
    manifest = load_workspace_manifest(manifest_path)
    if not _is_truthy_flag(manifest.get("template_publish_check")):
        return None
    if not (workspace_root / ".git").is_dir():
        return None

    skills = manifest.get("universal_skills") if isinstance(manifest.get("universal_skills"), list) else UNIVERSAL_SKILLS
    current_digest = compute_template_content_digest(workspace_root, skills)
    state_path = workspace_root / TEMPLATE_SYNC_STATE_REL
    recorded_digest: Optional[str] = None
    if state_path.is_file():
        try:
            recorded_digest = json.loads(state_path.read_text(encoding="utf-8")).get("digest")
        except Exception:
            recorded_digest = None

    return {
        "has_drift": current_digest != recorded_digest,
        "current_digest": current_digest,
        "recorded_digest": recorded_digest,
    }
