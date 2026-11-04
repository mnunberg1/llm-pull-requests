<!-- AI generated -->

# Agent instructions

This repo is a grader for GitHub pull requests. Any coding agent can work on it
or use it; Claude Code reads `CLAUDE.md` and the skills under `.claude/`,
other agents (Codex and the like) read this file.

- Read `CLAUDE.md` first, all of it, and follow it (conventions, which files
  need approval before an edit, the AI BEGIN/END markers). `plan.md` has the
  plan and `RUNNING.md` how to run it. `scripts.md` is the spec the scripts in
  `scripts/` are generated from; change the spec, not the generated scripts.
- The review loop, `/grade-review` in Claude Code, is the procedure in
  `.claude/skills/grade-review/SKILL.md`; `/grade-change-config` is
  `.claude/skills/grade-change-config/SKILL.md`. If your agent has no skills,
  read the file and follow it as written (it works on `grades/` and
  `results/` and calls the scripts with `--config`).
- Model calls made by the scripts go through `scripts/agent.py`. To have them
  use this agent instead of Claude, set `PRDOCS_AGENT` (for example
  `PRDOCS_AGENT=codex`) or `agent=` in the `<name>.cfg`; see RUNNING.md.
- Do not use a browser or browser automation here; check the web UI with
  `node --check`, syntax checks and requests to its API.
