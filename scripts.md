# Script specs

Spec for regenerating `scripts/` (gitignored, generated). Together with
`plan.md`, `prompt.md`, `rubric.md` and `CLAUDE.md` this should be enough to
rebuild them. If a script's behavior changes, change it here too.

Common: Python 3 stdlib only, run with `python3 -I`. Every
`argparse.ArgumentParser` gets `color=False`. `ROOT` is the parent of
`scripts/`. A repo is written `owner/name` for GitHub and `owner_name` on disk.
Each script starts with a comment saying it is AI generated.

Default repo: no repo name is hardcoded. A `default_repo()` helper reads
`REPO.md` and returns the first `github.com/<owner>/<name>` match as
`owner/name`; that is the canonical repo. `--repo` overrides it.

## fetch_prs.py

Args: `--repo` (default: `default_repo()`), `--limit` (default 25).

1. `gh pr list -R <repo> --state all --limit <n> --json number`.
2. For each PR, skip it if `data/<owner_name>/prs/<n>/diff.patch` exists.
3. Otherwise write into that directory:
   - `meta.json`: from `gh pr view --json number,title,author,body,labels,
     state,commits`, without `commits`, with `author` reduced to the login and
     `labels` to a list of names.
   - `commits.json`: list of `{oid, message}`, message being the headline, a
     blank line, then the body.
   - `diff.patch`: output of `gh pr diff`.
4. Print `fetched <n>` per PR.

## grade.py

Args: `--repo` (default: `default_repo()` in the on-disk form),
`--run-id` (required), `-j` (default 4 workers).

For each `data/<repo>/prs/<n>` directory, in parallel, skipping any that
already have `results/<run-id>/<n>.json`:

1. Build the prompt, concatenated in this order: `prompt.md`; the output format
   block below (a constant in the script); `# Guidelines` + `guidelines.md`;
   `# Rubric` + `rubric.md`; `# PR meta` + `meta.json`; `# Commits` +
   `commits.json`; `# Diff` + `diff.patch`. A diff over 150,000 characters is
   cut and gets `[diff truncated]` appended.
2. Run `claude -p --model sonnet --tools "" --no-session-persistence` with the
   prompt on stdin.
3. Take the text from the first `{` to the last `}`, parse it as JSON and write
   it, indented, to `results/<run-id>/<n>.json`. On a parse failure print the
   PR number, the first 200 characters of stdout and of stderr to stderr, and
   write nothing.
4. Print `graded <n>`.

Output format block (the only place the JSON shape is defined for the model;
wording and nature of the grading stay in `prompt.md`):

```
Return ONLY a JSON object, no prose, no code fences:
{"pr": <number>, "overall": <integer 1-5>, "comments": [{"sentiment": <integer 1-5>, "text": "<comment>"}, ...]}
```

## serve.py

Args: `run_id` (positional), `--repo` (as above), `--port` (default 8765).
Serves on 127.0.0.1, silences request logging, opens the page in the browser,
creates `grades/` if missing, writes `summary.txt` at startup.

Data per PR, for each `results/<run-id>/<n>.json` in numeric order: `pr`,
`title`, `author` (from `meta.json`), `url`
(`https://github.com/<owner>/<name>/pull/<n>`), `model` (the `overall`),
`comments`, and the human fields `mine` and `notes` from `grades/<n>.txt`.
A comment that is a plain string (older runs) is treated as
`{sentiment: null, text: <string>}`.

`grades/<n>.txt`: `overall: <1-5 or empty>`, then `notes:`, then the notes.
Missing file means no grade and no notes.

Routes:
- `GET /data`: JSON list of the data above.
- `POST /save`: body `{pr, mine, notes}`. If both are empty delete the file,
  otherwise write it in the format above. Then regenerate `summary.txt`.
- Any other GET: the page.

`results/<run-id>/summary.txt`: per PR a line
`<n>\tmodel=<N>\tmine=<N or ->`, then one line per comment
`  - [<sentiment or ?>] <text>`.

Page: a single self-contained HTML document with inline JS. Follows the system
light/dark theme (`color-scheme`, CSS variables, `prefers-color-scheme`),
including form controls. One card per PR: link `#<n> <title>` to the GitHub
URL, author and the model's `N/5`, the comments as a list each prefixed with a
colored sentiment badge (1 red, 2 orange, 3 gray, 4 green, 5 strong green, `?`
if unknown), an optional 1-5 select for my grade, and a notes textarea. Saving
happens on select change and on notes blur, via `POST /save`, showing "saved".
A checkbox filters to PRs where my grade differs from the model's by 2 or more;
those cards get a red border. No diff links. The sentiment is display only and
never affects any score or filter.
