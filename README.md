# Universal Agentic Project Template (`plan-pipeline`)

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

1. Click **"Use this template" $\rightarrow$ "Create a new repository"** on GitHub (or run `gh repo create my-project --template ericrowe/agentic-project-template --clone`).
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
  python3 scripts/plan_pipeline.py sync-template --push --repo ericrowe/agentic-project-template
  ```
