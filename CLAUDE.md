# prdocs

LLM grader for GitHub PRs, scored against the Pull Request Guidelines. See
`plan.md` for the full plan and workflow.

## Layout

- `guidelines.md` – the guidelines doc, unchanged; do not edit
- `rubric.md` – criteria and review order; self-updating with human approval
- `prompt.md` – grading prompt sent to the model; self-updating with human
  approval
- `REPO.md` – target repo info
- `scripts/` – `fetch_prs.py`, `grade.py`, `explain.py`, `serve.py`,
  <!-- AI BEGIN -->`mirror_prs.py`, `ci_grade.py`, `collect_ci.py`,
  `pr-grader.yml`<!-- AI END --> - generated
- `.claude/skills/grade-review/` – the interactive review-refine loop; use it
  to review grades and ask the grader for its rationale
- `learning/` – small example PRs and why they were accepted or not, named
  `accepted-<topic>.md` or `rejected-<topic>.md`; added to the grading prompt
  after the rubric
- `data/`, `results/`, `grades/` – generated, gitignored
- `checksums.md` – md5 of the files the grade-review skill depends on; the
  skill rewrites it, gitignored

## Commands

```
python3 -I scripts/fetch_prs.py
python3 -I scripts/grade.py --run-id <run-id>
python3 -I scripts/explain.py <run-id> <pr> ["question"]   # grader's rationale
python3 -I scripts/serve.py <run-id>      # grading page at http://127.0.0.1:8765/
```

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
- `REPO.md`

Any modification to these files should be done by requesting explicit approval.

## Conventions

- Never edit `guidelines.md`, `plan.md`, or `rubric.md` without showing the diff
  and getting approval first
- Don't modify REPO.md data unless asked
- Rubric changes come from the user's grades and notes in `grades/<n>.txt`, not
  from the model's own judgement.
- Use a new `results/<run-id>` for each rubric or prompt version; never
  overwrite old runs.
- When generating/reformatting md files, wrap at 80 chars.
- Comment in the file if the file is AI generated
- The target repo name lives only in `REPO.md`. Do not write it in any other
  file; scripts and specs must read it from `REPO.md` (first
  `github.com/<owner>/<name>` link is the canonical repo).
- Rules in rubric.md, prompt.md and plan.md must be generic: no PR numbers or
  repo names. Repo-specific rules go only in REPO.md.
- When modifying/adding/applying diffs in manually-controlled files,
  be sure to ANNOTATE the beginning and end of LLM-generated blocks with
  `<!-- AI BEGIN -->` and `<!-- AI END -->` markers

## TODO

- Fill in anything missing here as the project settles.
