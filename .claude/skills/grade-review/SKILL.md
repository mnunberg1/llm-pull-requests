---
name: grade-review
description: Interactive grade-review-refine loop for the PR grader. Shows
  graded PRs one at a time, records the user's inline feedback, answers
  questions about the grader's rationale, and proposes generic changes to
  rubric.md, prompt.md, guidelines.md, plan.md and REPO.md. Use when the user
  wants to review grader output, give feedback on grades, ask why the grader
  said something, or refine the rubric.
---

<!-- AI generated -->

# Grade-review loop

Drive the review of graded PRs and turn the user's feedback into proposed
rubric changes. The user is the authority on what a good grade is; the model
is only the thing being calibrated.

## Setup

1. Run the change check (below). It reads `CLAUDE.md`, `plan.md`, `rubric.md`,
   `prompt.md` and `REPO.md` the first time and whenever they change. Follow
   the conventions in `CLAUDE.md`, especially wrapping markdown at 80 columns.
2. Pick the run: the id the user names, else the newest folder in `results/`.
   If `results/` is empty or the user wants a fresh run, offer
   `python3 -I scripts/grade.py --run-id <run-id>` and wait for it.
3. Load every `results/<run-id>/<n>.json` and any `grades/<n>.txt`.

## Change check

The user edits the project files while this skill runs. `checksums.md` records
the md5 of every file this skill depends on as of the last time it was read, so
edits are noticed and acted on.

Tracked files: `CLAUDE.md`, `plan.md`, `rubric.md`, `prompt.md`,
`guidelines.md`, `REPO.md`, `scripts.md`, this `SKILL.md`, `learning/*.md` and
`scripts/*.py`. Not `grades/`, `results/` or `data/`.

`checksums.md` holds one list item per file, `- <md5>  <path>`, under a
heading. If it
does not exist, create it from the current files (treat them as just read).

Run the check at setup, before showing each PR, and before each Refine:
1. Compute the md5 of each tracked file (`md5 -q <file>` on macOS, else
   `md5sum`).
2. Compare with `checksums.md`. A file is changed if the md5 differs, new if
   unlisted, removed if listed but missing.
3. If nothing differs, carry on without comment.
4. Otherwise re-read each changed file and say in a line or two what changed.
   `git diff -- <file>` helps, but shows changes since the last commit, not
   since the last check.
5. Act on the consequences, asking before anything slow:
   - `SKILL.md`: follow the new version from here on.
   - `CLAUDE.md`, `plan.md`: follow the new conventions and workflow.
   - `REPO.md`: if the ignore lists or size classification changed, the PR
     sample is stale; offer `fetch_prs.py --refresh`, then a grade into a new
     run id.
   - `rubric.md`, `prompt.md`, `guidelines.md`, `learning/*.md`: the current
     run was graded with the old text; offer a re-grade into a new run id, and
     compare.
   - `scripts.md`: scripts may be stale; offer to regenerate them as `plan.md`
     describes. `scripts/*.py` changed with no spec change: just note it.
6. Rewrite `checksums.md` with the current md5s once the changes are handled or
   the user declines, so the same change is not reported twice.

When this skill itself applies an approved edit to a tracked file, update that
entry in `checksums.md` straight away, so its own edits are not reported as
outside changes.

## Review loop

Take PRs one at a time. Start with ungraded PRs, then those where the model and
the user disagree by 2 or more. Skip any with an existing grade unless asked.

For each PR show:
- `#<n> <title>`, author and the GitHub link (build it from the first
  `github.com/<owner>/<name>` link in `REPO.md`)
- the model's overall 1-5 score
- the effort estimate if the result has one, as `author ~Nm, review ~Nm (Rx)`
- summarize the comments. if the user asks for the exact verbatim comments or
  scores, then do that, otherwise don't flood the screen. Feel free to use
  color and other formatting.

Then stop and wait. The user replies in free text. Understand these forms:
- a score, such as "2" or "2.5/5"
- inline comments on a model comment, such as "c2 wrong, this is fine for
  small fixes" or "c3 not useful"
- general notes on the PR
- "next", "skip", "back", "stop"
- a question about the grader (see below)

Record each reply in `grades/<n>.txt`, the same format the web page writes:

```
overall: <integer 1-5, or empty>
notes:
<the user's words, with inline comments kept as "c2: ...">
```

Keep the user's wording. Set `overall` only when they gave an integer 1-5; keep
fractional scores in the notes text. Merge into the existing file, never
discard earlier notes. Confirm briefly, then show the next PR.

## Asking the grader why

When the user asks why the model gave a score or wrote a comment, run:

```
python3 -I scripts/explain.py <run-id> <n> "<the user's question>"
```

With no question the script asks for a full rationale. Show the answer, say
which rubric or guideline text it relied on, and point out where the rubric is
ambiguous or silent. Do not defend the model; if the explanation shows a gap in
the rubric or prompt, note it as a candidate change. This never changes the
stored grade or results.

## Refine

After every handful of PRs, or when the user says "refine" or "stop", look at
all feedback collected so far and find patterns: where the model is too
generous or too harsh, comments the user called wrong or useless, things the
user wants ignored.

Propose changes as diffs and wait for approval before editing anything:
- `rubric.md` and `prompt.md`: the main targets
- `plan.md`: process changes only
- `guidelines.md`: only for a real gap in the guidelines themselves, and say
  so; it is normally left unchanged
- `REPO.md`: anything specific to the target repo, such as ignored authors or
  titles
- `learning/`: a new example, proposed only occasionally (see below)

Rules for every proposal:
- Generic wording only: no PR numbers, repo names, author names or examples
  copied from a specific PR. Repo-specific rules go only in `REPO.md`.
- Base each change on the user's feedback, not on your own opinion of the
  grader. Say which feedback motivated it, outside the file text.
- Prefer a few sharp rules over many; check for conflicts with existing text.
- Wrap markdown at 80 columns.
- `guidelines.md`, `plan.md`, `rubric.md`, `README.md` and `REPO.md` are
  manually controlled (see `CLAUDE.md`): every edit needs explicit approval,
  and each generated block is wrapped in `<!-- AI BEGIN -->` and
  `<!-- AI END -->` markers, in the proposed diff and in the file.

Apply only the diffs the user approves, then update `checksums.md` for them.

### Learning examples

Now and then, not every round, propose a new file for `learning/`. Do it when
the user's feedback shows a judgement that is easier to show than to state as a
rule, such as a matter of degree, or when the rubric text alone keeps being
misapplied.

An example is a small snippet (about 10 to 30 lines) describing a pull request
and why it was accepted or not: a short description or diff excerpt, then the
reason. Rules:
- Name it `accepted-<topic>.md` or `rejected-<topic>.md`, with a topic that says
  what it teaches, such as `rejected-table-on-small-fix.md`.
- Keep it generic: invent or reduce the case, with no PR numbers, repo names,
  author names or text copied from a specific PR.
- One lesson per file. Do not restate the rubric; show the case.
- Show the proposed file in full and wait for approval before creating it.

## Re-grade and compare

After approved changes, offer to re-grade into a NEW run id (never overwrite a
run): `python3 -I scripts/grade.py --run-id <new-run-id>`. Then compare the
graded PRs old vs new against the user's grades: where the gap closed, where it
widened, and any new disagreements. Continue the loop on the new run, until the
user says agreement is good enough.
