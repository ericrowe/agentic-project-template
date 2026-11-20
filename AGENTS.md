# Universal Agentic Project Template — Workspace Agent Directives

{{PROJECT_DESCRIPTION}}

Refer to [`.agents/skills/plan-pipeline/SKILL.md`](./.agents/skills/plan-pipeline/SKILL.md) and [`docs/plans/AGENTS.md`](./docs/plans/AGENTS.md) for the mandatory 5-step plan-driven development lifecycle.

---

## Core Engineering Invariants

1. **5-Step Plan-Driven Lifecycle & 7 Mandatory Sections**:
   - All features, bug fixes, and refactors follow: **Step 0** (`docs/plans/IDEAS.md` intake) $\rightarrow$ **Step 1** (`docs/plans/NN_<name>_plan.md` with 7 mandatory sections) $\rightarrow$ **Step 2** (HITL approval) $\rightarrow$ **Step 3** (3-Phase RED/GREEN/Regression TDD execution) $\rightarrow$ **Step 4** (Interactive user validation) $\rightarrow$ **Step 5** (`python3 scripts/plan_pipeline.py archive` + coverage ratchet check + Git commit).
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
