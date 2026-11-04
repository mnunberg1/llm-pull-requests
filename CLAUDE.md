# LLM Pull Request Analyzer

LLM grader for GitHub PRs, scored against the Pull Request Guidelines. See
`plan.md` for the full plan and workflow.

## Layout

- `guidelines.md` – the guidelines doc, unchanged; do not edit
- `rubric.md` – criteria and review order; self-updating with human approval
- `prompt.md` – grading prompt sent to the model; self-updating with human
  approval
- <!-- AI BEGIN -->`<name>.cfg` configs (`valkey.cfg`, `valkey-search.cfg`, ...), each with
  `repo=repos/<name>.md` naming the repo file; `active-config.cfg` is a
  gitignored symlink to the active one (default for all scripts)
- `repos/` – target repo info, one `<name>.md` per repo; `example.md` is a
  generic template<!-- AI END -->
- `scripts/` – `fetch_prs.py`, `grade.py`, `explain.py`, `serve.py`,
  <!-- AI BEGIN -->`mirror_prs.py`, `ci_grade.py`, `collect_ci.py`,
  `pr-grader.yml`<!-- AI END --><!-- AI BEGIN -->, `webui.py`, `extract_feedback.py`, `agent.py`<!-- AI END --> - generated
  from `scripts.md` and committed<!-- AI BEGIN -->; model calls go through `agent.py` (claude by default,
  `codex` or a command via `--agent`, `$PRDOCS_AGENT` or `agent=` in the config)<!-- AI END -->
- `.claude/skills/grade-review/` – the interactive review-refine loop; use it
  to review grades and ask the grader for its rationale
- <!-- AI BEGIN -->`.claude/skills/grade-change-config/` – `/grade-change-config`
  switches the active config (repoints `active-config.cfg`)<!-- AI END -->
- `learning/` – small example PRs and why they were accepted or not, named
  `accepted-<topic>.md` or `rejected-<topic>.md`; added to the grading prompt
  after the rubric
  <!-- AI BEGIN -->- `learning/interactive-feedback/<owner_name>/<pr>-<timestamp>.md` – the
  reviewer's replies to grader comments as Q&A, written by
  `scripts/extract_feedback.py` (from the web UI and the grade-review skill);
  read by the grader after the examples. Not edited by hand.<!-- AI END -->
- `data/`, `results/`, `grades/` – generated, gitignored
- `checksums.md` – md5 of the files the grade-review skill depends on; the
  skill rewrites it, gitignored

## Commands

```
python3 -I scripts/fetch_prs.py
python3 -I scripts/grade.py --run-id <run-id>
python3 -I scripts/explain.py <run-id> <pr> ["question"]   # grader's rationale
python3 -I scripts/serve.py <run-id>      # grading page at http://127.0.0.1:8765/
<!-- AI BEGIN -->python3 -I scripts/webui.py                # web UI at http://127.0.0.1:8766/ (see webui.md)<!-- AI END -->
```

<!-- AI BEGIN -->
All scripts except `ci_grade.py` accept `--config <file.cfg>` (e.g.
`valkey.cfg`, `valkey-search.cfg`) to pick which repo to work on. The config
holds `repo=repos/<name>.md`. `$PRDOCS_CONFIG` works too, and `ci_grade.py`
only honours the env var. The flag wins over the env var; the default is
`active-config.cfg`. Data lives under `data/<owner>_<name>/`, so each repo stays
separate.
<!-- AI END -->

<!-- AI BEGIN -->
GitHub integration (see `integration.md`):

```
python3 -I scripts/mirror_prs.py --push-grader          # publish grader bundle
python3 -I scripts/mirror_prs.py --pr <n> [--dry-run]   # recreate PR in mirror
python3 -I scripts/mirror_prs.py --open --close         # sync open PRs
python3 -I scripts/collect_ci.py                        # CI grades -> results/
```
<!-- AI END -->

## Manually (Co-) Authored Files

These files are controlled by humans. Take care to reflect style and annotate
AI additions properly:

- `guidelines.md`
- `plan.md`
- `rubric.md`
- `plan.md`
- `README.md`
- <!-- AI BEGIN -->`repos/*.md` (repo files) and `<name>.cfg` files<!-- AI END -->

Any modification to these files should be done by requesting explicit approval.

## Conventions

- Never edit `guidelines.md`, `plan.md`, or `rubric.md` without showing the diff
  and getting approval first
- Don't modify repo files (`repos/*.md`) data unless asked
- Rubric changes come from the user's grades and notes in <!-- AI BEGIN -->`grades/<owner_name>/<n>.txt`<!-- AI END -->, not
  from the model's own judgement.
- Use a new <!-- AI BEGIN -->`results/<owner_name>/<run-id>`<!-- AI END --> for each rubric or prompt version; never
  overwrite old runs.
- When generating/reformatting md files, wrap at 80 chars.
- Comment in the file if the file is AI generated
- The target repo name lives only in the repo file (`repos/<name>.md`, chosen
  by the config's `repo=` line). Do not write it in any other file; scripts and
  specs must read it from there (first `github.com/<owner>/<name>` link is the
  canonical repo).
- Rules in rubric.md, prompt.md and plan.md must be generic: no PR numbers or
  repo names. Repo-specific rules go only in the repo file.
- When modifying/adding/applying diffs in manually-controlled files,
  be sure to ANNOTATE the beginning and end of LLM-generated blocks with
  `<!-- AI BEGIN -->` and `<!-- AI END -->` markers

## TODO

- Fill in anything missing here as the project settles.
- Don't use browser/chrome MCP for this project, just do best-effort at web
    layout.