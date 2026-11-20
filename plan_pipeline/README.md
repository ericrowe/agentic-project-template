# `plan-pipeline` — Standardized Plan-Driven Feature Development Lifecycle

`plan-pipeline` is a standalone, zero-dependency Python package, CLI tool, and AI coding agent skill bundle (`plan-pipeline` + `idea-triage`) that enforces a rigorous **5-Step Plan-Driven Feature Development Lifecycle** across single-project repositories and multi-project workspaces:

1. **Step 0: Asynchronous Idea Intake & Interactive Triage (`docs/plans/IDEAS.md`)**
2. **Step 1: Formal 7-Section Plan Creation (`docs/plans/NN_<name>_plan.md`)**
3. **Step 2: Human-in-the-Loop (HITL) Approval Gate**
4. **Step 3: 3-Phase Test-First Execution (`RED/Baseline` $\rightarrow$ `GREEN` $\rightarrow$ `Full Regression`)**
5. **Step 4: Interactive User Validation**
6. **Step 5: Coverage Ratchet Check, Link-Safe Archival (`docs/plans/complete/YYYY-MM-DD-<plan>.md`), Walkthrough & Git Commit**

---

## CLI Commands

```bash
# 1. Initialize plan-pipeline skills, pointer files, and docs/plans/ in any repository
python3 -m plan_pipeline.cli init --path /path/to/repo --name "My-Project"

# 2. View active, proposed, queued, and on-hold plans across a workspace
python3 -m plan_pipeline.cli status

# 3. Validate one or all active plans against the 7 mandatory sections & portable link rules
python3 -m plan_pipeline.cli validate --all

# 4. Scaffold a new 7-section plan and register it in docs/plans/AGENTS.md
python3 -m plan_pipeline.cli new --id 01 --slug feature_name --title "Feature Title"

# 5. Archive a validated plan (moves to complete/YYYY-MM-DD-..., re-anchors relative links, writes walkthrough, updates AGENTS.md)
python3 -m plan_pipeline.cli archive --plan docs/plans/01_feature_name_plan.md --summary "Implemented feature and verified tests."

# 6. Check plan risk tier and ## Supervisor Sign-off status (Gate A / Gate B)
python3 -m plan_pipeline.cli supervisor-check --all

# 7. Enforce supervisor sign-off on high-risk plans in validate or archive (or override with --skip-supervisor)
python3 -m plan_pipeline.cli validate --all --require-supervisor
python3 -m plan_pipeline.cli archive --plan docs/plans/01_feature_name_plan.md --require-supervisor
```

---

## Risk-Tiered `supervisor` Configuration (`plan-pipeline.yaml`)

Add an optional `"supervisor"` block to `plan-pipeline.yaml` to trigger Gate A (pre-HITL plan review) and Gate B (pre-deploy diff review) only on higher-risk plans:

- `mode`: `"auto_on_risk"` (default), `"always"`, or `"off"`.
- `reviewer_model`: Subagent model alias for supervisor gates (e.g., `"pro"`).
- `min_modified_files`: Unique `[NEW]` / `[MODIFY]` / `[DELETE]` file count in Section 3 that triggers high risk (default `4`).
- `require_for_macro_plans`: Boolean; flags `M*` Macro Plans as high risk when `true`.
- `risk_keywords`: Substrings (e.g., `"database.py"`, `"migration"`, `"firmware"`, `"deploy.sh"`, `"agy_bridge"`, `"sudoers"`) that elevate a plan to `HIGH RISK`.

## Opt-In Template Publish Drift Check (`plan-pipeline.yaml`)

Template publisher workspaces can set `"template_publish_check": true` in `plan-pipeline.yaml` (omitted / `false` by default for downstream consumers). When enabled, `status` and `archive` compare a SHA-256 digest of `plan_pipeline/` and configured `universal_skills` against `.git/plan_pipeline_template_sync.json` and print a non-blocking reminder to run `sync-template --push` when changes are unpublished.
