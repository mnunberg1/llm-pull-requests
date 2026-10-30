# LLM PR Grader – Project Plan

Goal: grade PRs against the Pull Request Guidelines, refine offline until grades match human judgement, then wire into GitHub.

## Target Repo

To be read in file REPO.md

## Directory layout

```
prdocs/
    guidelines.md      # the Pull Request Guidelines doc, unchanged
    rubric.md          # scorable criteria derived from guidelines
    REPO.md             # repo-specific information
  data/<REPO>
    prs/<number>/      # cached PR data, fetched once
      meta.json        # title, author, description, labels, state
      commits.json     # commit list with messages and per-commit stats
      diff.patch       # full diff
  scripts/
    fetch_prs.py       # pulls recent PRs via gh CLI into data/prs
    grade.py           # sends rubric + PR to the model, writes JSON result
    serve.py           # local server: serves the grading page, saves grades to text files
  grades/
    <number>.txt       # my optional 1-5 grade ("overall: N") then "notes:" and free-form text
  results/
    <run-id>/          # one folder per rubric version
      <number>.json
      summary.txt      # one line per PR: number, model overall, my grade, verdict
```


## Model output contract

The grader must return only JSON, nothing else. No per-criterion scores; the comments carry the detail:

```json
{
  "pr": 123,
  "overall": 3,
  "comments": ["Short comment, ~150 chars max, no implementation details.", "..."]
}
```

## Workflow

1. Fetch the last 20–30 PRs (open and closed) once.
1. Grade them all into results/<run-id>/.
1. Run `scripts/serve.py <run-id>` and open the page in a browser. Each PR shows its GitHub link, title, author, the model's 1-5 score and assessment, an optional 1-5 grade of mine, and a notes box. Saving writes grades/<number>.txt.
1. The page can filter to PRs where the model and I differ by 2+ points. summary.txt is regenerated on each save.
1. Interactive LLM session prompts for adjustments to rubric.md and plan.md based on feedback.
1. Adjust rubric.md, re-run into a new results/\<run-id>, compare.
1. Repeat until agreement is good enough.

## Later: GitHub integration

Once calibrated, a GitHub Action on pull\_request (opened, synchronize) runs fetch + grade for that PR and posts a single short comment or check status. Start in a silent/log-only mode before posting publicly.
