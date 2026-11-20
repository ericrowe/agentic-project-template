# AI Assistant Directives

Refer to [`AGENTS.md`](./AGENTS.md), [`docs/plans/AGENTS.md`](./docs/plans/AGENTS.md), and [`.agents/skills/plan-pipeline/SKILL.md`](./.agents/skills/plan-pipeline/SKILL.md) for all workspace directives and skills.

- **5-Step Plan Lifecycle**: Every code change requires a 7-section plan in `docs/plans/NN_<name>_plan.md` approved before implementation.
- **Standardized Scripts**: Use `./run_tests.sh` and `python3 scripts/plan_pipeline.py status | validate | new | archive`.
- **Mid-Plan Planning Request Disambiguation**: Ask whether new mid-flight requests should be added to `docs/plans/IDEAS.md` or pause the current plan.
- **Tiered Test Execution**: Run tests only when code/scripts change; skip on documentation-only edits.
- **Unrelated Test Failure Protocol**: Fail-fast and defer unrelated test failures to `docs/plans/IDEAS.md`.
