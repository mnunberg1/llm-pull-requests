# prdocs

LLM grader for GitHub PRs, scored against the Pull Request Guidelines. See `plan.md` for the full plan and workflow.

## Layout

- `guidelines.md` – the guidelines doc, unchanged; do not edit
- `rubric.md` – criteria and review order; self-updating with human approval
- `prompt.md` – grading prompt sent to the model; self-updating with human approval
- `REPO.md` – target repo info
- `scripts/` – `fetch_prs.py`, `grade.py`, `serve.py` - generated
- `data/`, `results/`, `grades/` – generated, gitignored

## Commands

```
python3 -I scripts/fetch_prs.py --limit 25
python3 -I scripts/grade.py --run-id <run-id>
python3 -I scripts/serve.py <run-id>      # grading page at http://127.0.0.1:8765/
```

## Conventions

- Never edit `guidelines.md`, `plan.md`, or `rubric.md` without showing the diff and getting approval first.
- Rubric changes come from the user's grades and notes in `grades/<n>.txt`, not from the model's own judgement.
- Use a new `results/<run-id>` for each rubric or prompt version; never overwrite old runs.
- When generating/reformatting md files, wrap at 80 chars.

## TODO

- Fill in anything missing here as the project settles.
