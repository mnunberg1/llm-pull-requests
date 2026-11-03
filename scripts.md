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

<!-- AI BEGIN -->
Mirror repo: a `mirror_repo()` helper reads `REPO.md` and returns, as
`owner/name`, the first `github.com/<owner>/<name>` match on a line that
contains `mirror` (case-insensitive). It exits with an error if there is none.
`--mirror` overrides it. Only the mirroring scripts use it.
<!-- AI END -->

## fetch_prs.py

Args: `--repo` (default: `default_repo()`), `--per-bucket` (default 10),
`--scan-limit` (default 300 PRs to look at), `--refresh`.

Picks `per-bucket` PRs each of small, medium and large size, open and closed.

1. If `data/<owner_name>/selected.json` exists, print it and stop, unless
   `--refresh` was given (the sample is fetched once).
2. `gh pr list -R <repo> --state all --limit <scan-limit> --json
   number,title,author`, newest first.
3. For each PR in order, until every bucket is full: skip it if it is ignored
   (see below); get its diff (the cached `diff.patch` if present, else
   `gh pr diff`); compute its size and bucket; skip it if that bucket is full.
4. Size is the number of added plus deleted lines in files under a core source
   path from the `Size classification` section of `REPO.md`, not counting blank
   lines or comment-only lines (after stripping, starting with `//`, `#`,
   `/*`, `*` or `*/`). Test files are not counted, except when a PR has zero
   core lines and changes test files: then size is its test lines (a test
   infrastructure PR). A PR with neither counts as size 0. Buckets: small is
   under 150, medium 150 to 500 inclusive, large over 500.
5. For each selected PR, write into `data/<owner_name>/prs/<n>/` (unless
   `diff.patch` already exists there):
   - `meta.json`: from `gh pr view --json number,title,author,body,labels,
     state,commits`, without `commits`, with `author` reduced to the login and
     `labels` to a list of names.
   - `commits.json`: list of `{oid, message}`, message being the headline, a
     blank line, then the body.
   - `diff.patch`: the diff.
6. Write `data/<owner_name>/selected.json`: `{"<n>": {"bucket": "small",
   "size": 12}, ...}`. Print `selected <n> <bucket> <size>` per PR, and a
   warning for any bucket that did not fill.

<!-- AI BEGIN -->
`--pr` (repeatable): fetch only these PRs and skip steps 1-4 and 6; the
sample and `selected.json` are left alone. Each PR is written as in step 5,
re-fetched if `--refresh` was given, and ignored PRs are skipped with
`ignored <n>`. Print `fetched <n>` per PR. Used by CI and by `collect_ci.py`.
<!-- AI END -->

Ignore lists: `REPO.md` may have `## Ignored authors` and `## Ignored titles`
sections, each holding a bullet list (`- item`; other text is ignored, and so
is anything after ` (` in a bullet, which is a comment). A PR is
ignored if its author login equals an ignored author, or its title contains an
ignored title, both case-insensitive. A small `ignored()`
helper does this and is shared by `fetch_prs.py` and `grade.py`.

## grade.py

Args: `--repo` (default: `default_repo()` in the on-disk form),
`--run-id` (required), `-j` (default 4 workers), `--pr` (repeatable; grade
only these PR numbers).

For each PR listed in `data/<repo>/selected.json` (all directories under
`prs/` if that file is missing), in parallel, skipping any whose `meta.json` is
ignored and any that already have `results/<run-id>/<n>.json`:

1. Build the prompt, concatenated in this order: `prompt.md`; the output format
   block below (a constant in the script); `# Guidelines` + `guidelines.md`;
   `# Rubric` + `rubric.md`; `# Examples` + the files in `learning/` (see
   below); `# PR meta` + `meta.json`; `# Commits` + `commits.json`; `# Diff` +
   `diff.patch`. A diff over 150,000 characters is cut and gets
   `[diff truncated]` appended.
2. Run `claude -p --model sonnet --tools "" --no-session-persistence` with the
   prompt on stdin.
3. Take the text from the first `{` to the last `}`, parse it as JSON and write
   it, indented, to `results/<run-id>/<n>.json`. On a parse failure print the
   PR number, the first 200 characters of stdout and of stderr to stderr, and
   write nothing.
4. Print `graded <n>`.

<!-- AI BEGIN -->
With `--pr`, grade `prs/<n>` for each given number whether or not it is in
`selected.json` (it must have been fetched).
<!-- AI END -->

Examples: every `learning/*.md`, in name order, each under a `## <file name
without extension>` header. Omit the `# Examples` section when there are none.
A small helper builds this and is shared by `grade.py` and `explain.py`.

Output format block (the only place the JSON shape is defined for the model;
wording and nature of the grading stay in `prompt.md`):

```
Return ONLY a JSON object, no prose, no code fences:
{"pr": <number>, "overall": <integer 1-5>, "comments": [{"sentiment": <integer 1-5>, "text": "<comment>"}, ...], "effort": {"author_minutes": <integer>, "review_minutes": <integer>}}
```

## explain.py

Args: `run_id` (positional), `pr` (positional number), `question` (optional
positional), `--repo` (default: `default_repo()` in the on-disk form).

Asks the model to explain a stored grade. Never writes to `results/` or
`grades/`.

1. Build the same input as `grade.py` (prompt, guidelines, rubric, examples,
   PR meta, commits, diff, same truncation), but without the output format block. The
   prompt is under a `# Grading prompt you were given` header.
2. Append `# Your previous answer` + `results/<run-id>/<pr>.json`.
3. Append `# Question` + the question. With no question use: "Explain why you
   gave this overall rating and each comment. Quote the rubric or guideline
   text you relied on, and say where it was ambiguous."
4. Prefix an instruction: answer in plain text (not JSON); the length limits in
   the grading prompt apply to the grade, not to this answer; be honest if the
   rubric is ambiguous or you would now weigh something differently.
5. Run `claude -p --model sonnet --tools "" --no-session-persistence` with the
   prompt on stdin and print its stdout.

## serve.py

Args: `run_id` (positional), `--repo` (as above), `--port` (default 8765).
Serves on 127.0.0.1, silences request logging, opens the page in the browser,
creates `grades/` if missing, writes `summary.txt` at startup.

Data per PR, for each `results/<run-id>/<n>.json` in numeric order: `pr`,
`title`, `author` (from `meta.json`), `url`
(`https://github.com/<owner>/<name>/pull/<n>`), `model` (the `overall`),
`comments`, `effort` (null if absent) and the human fields `mine` and `notes`
from `grades/<n>.txt`.
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
`  - [<sentiment or ?>] <text>`, then if present
`  effort: author ~<N>m, review ~<N>m (<review/author, 1 decimal>x)`.

Page: a single self-contained HTML document with inline JS. Follows the system
light/dark theme (`color-scheme`, CSS variables, `prefers-color-scheme`),
including form controls. One card per PR: link `#<n> <title>` to the GitHub
URL, author and the model's `N/5`, the comments as a list each prefixed with a
colored sentiment badge (1 red, 2 orange, 3 gray, 4 green, 5 strong green, `?`
if unknown), the effort line in the same format, an optional 1-5 select for my grade, and a notes textarea. Saving
happens on select change and on notes blur, via `POST /save`, showing "saved".
A checkbox filters to PRs where my grade differs from the model's by 2 or more;
those cards get a red border. No diff links. The sentiment is display only and
never affects any score or filter.

<!-- AI BEGIN -->

# GitHub integration (mirror)

See `integration.md`. Upstream PRs are recreated as PRs in the writable mirror
(`mirror_repo()`) so the grader can run as a GitHub Action there before it
goes anywhere near the canonical repo. Four generated files:

- `mirror_prs.py` – local; copies upstream PRs into the mirror
- `pr-grader.yml` – the workflow, copied into the mirror by `mirror_prs.py`
- `ci_grade.py` – runs inside the workflow
- `collect_ci.py` – local; pulls CI grades into `results/`

## mirror_prs.py

Needs `git` and `gh` (logged in, with push access to the mirror).

Args: `--repo` (default `default_repo()`), `--mirror` (default
`mirror_repo()`), `--pr` (repeatable), `--selected` (every PR in
`selected.json`), `--open` (every open upstream PR, newest first, up to
`--limit`, default 50), `--close`, `--push-grader`, `--push-url` (default
`https://github.com/<mirror>.git`), `--dry-run`. With none of `--pr`,
`--selected`, `--open`, `--close` or `--push-grader`, print usage and exit.

Git work happens in a bare repo at `data/<owner_name>/git`, created on first
use. Upstream is fetched from `https://github.com/<repo>.git`. Never touch
any branch in the mirror other than `pr-grader`, `pr/<n>` and `base/<n>`.

Mirrored PR layout, per upstream PR `<n>`:

- `pr/<n>`: the upstream head commit, unchanged (same hashes and authors).
- `base/<n>`: the merge base of the upstream base and head, plus one harness
  commit (below). The mirror PR goes from `pr/<n>` into `base/<n>`, so its
  diff and commit list equal the upstream PR's, and the harness commit is
  not part of it.
- The workflow runs on `pull_request`, not `pull_request_target`: since
  November 2025 GitHub always takes a `pull_request_target` workflow from the
  default branch, which is the mirror owner's own branch and is left alone.
  `pull_request` takes the workflow from the PR's merge commit, which gets it
  from the harness commit. Head and base are in the same repo, so the run has
  secrets.

Harness commit, built with git plumbing (no work tree) on top of the merge
base: the merge base's tree, minus every file under `.github/workflows/`
that the PR does not touch (so the canonical repo's CI does not run on
mirrored PRs, without causing merge conflicts), plus
`.github/workflows/pr-grader.yml` from `scripts/pr-grader.yml`. Message:
`pr-grader harness for upstream PR <n> (not part of the PR)`. Author and
committer are `pr-grader <pr-grader@users.noreply.github.com>`, both dated
with the merge base's committer date, so the same inputs always give the same
commit and unchanged bases are not pushed again.

`--push-grader`: publish the grader bundle to branch `pr-grader` of the
mirror. The bundle is `prompt.md`, `rubric.md`, `guidelines.md`, `REPO.md`,
`learning/*.md` and `scripts/*.py` from this checkout. Commit it on top of the
mirror's current `pr-grader` (if any) with message `pr-grader bundle from
<short HEAD of this repo>` (`-dirty` appended if `git status --porcelain` is
not empty); skip the commit and push if the tree did not change. Runs first
when combined with other options. Mirroring a PR fails early if the mirror
has no `pr-grader` branch.

For each selected PR `<n>` (a failure on one PR is printed and the rest go
on):

1. `gh pr view <n> -R <repo> --json number,title,author,body,state,isDraft,
   baseRefOid,headRefOid,files,url`. Skip ignored PRs (`ignored()`), printing
   `ignored <n>`.
2. `git fetch --no-tags <upstream> +refs/pull/<n>/head:refs/upstream/pr/<n>
   <baseRefOid>`; the merge base is `git merge-base <baseRefOid>
   <headRefOid>`.
3. Parity check: the set of paths from `git diff --name-only <merge base>
   <headRefOid>` must equal the `files` paths. If not, print `skip <n>:
   diff differs from upstream` and go on.
4. Build the harness commit. Compare with `git ls-remote <push-url>` and
   force-push only the refs that changed: `<headRefOid>:refs/heads/pr/<n>`,
   `<harness>:refs/heads/base/<n>`.
5. Find the mirror PR: `gh pr list -R <mirror> --head pr/<n> --state all
   --json number,state`. Always pass `-R <mirror>`: the mirror may be a fork,
   and `gh` would otherwise target its parent.
   - none: `gh pr create -R <mirror> --head pr/<n> --base base/<n>` with the
     title and body below.
   - exists: `gh pr edit` the title and body if they changed. If it is
     closed and the upstream PR is open, reopen it.
6. Record it in `data/<owner_name>/mirror.json`: `{"<n>": {"mirror_pr": 12,
   "head": "<sha>", "base": "<sha>"}}`. Print `mirrored <n> -> <mirror>#<m>
   (<created|updated|unchanged>)`.

`--close`: for every PR in `mirror.json` whose upstream PR is no longer open
and whose mirror PR is open, close the mirror PR (never merge it) and print
`closed <n>`.

Title and body must not ping anyone or link back upstream (a link from the
mirror would add a "mentioned this" event to the upstream PR):

- Title: `<upstream title> (upstream <n>)`, with a zero-width space (U+200B)
  inserted after every `@` and `#`.
- Body:

  ```
  <!-- pr-grader upstream=<n> -->
  Mirror of an upstream pull request, for testing the PR grader. Do not merge.

  Upstream: `<url>` by `<author login>`

  <details><summary>Original description</summary>

  <fence>text
  <upstream body>
  <fence>

  </details>
  ```

  `<fence>` is a run of backticks one longer than the longest run in the
  body, and at least three. Nothing inside a code block is linked.

`--dry-run`: fetch and build commits as usual, but do not push, create, edit,
reopen or close anything, and do not write `mirror.json`; print each push and
`gh` write it would run.

## pr-grader.yml

GitHub Actions workflow, written to `scripts/` and copied into each
`base/<n>` by `mirror_prs.py`. No repo names in it.

- Name `pr-grader`. Trigger: `pull_request`, types `opened`, `synchronize`,
  `reopened`, branches `base/**`.
- `permissions`: `contents: read`, `pull-requests: write`.
- `concurrency`: group `pr-grader-<PR number>`, cancel in progress.
- One job, only if the head ref starts with `pr/`; `runs-on: [self-hosted,
  macOS, ARM64]` (the user's Mac, using its logged-in `claude`; no API key),
  20 min timeout. Env: `GH_TOKEN` (the workflow token), `PR_GRADER_MODE`
  (repo variable, default `log`).
- Steps: check out branch `pr-grader` into `grader/` (never the PR's code);
  print `python3 --version` and `claude --version` (the runner's PATH must
  provide Python 3.14+, since the scripts use `color=False`, and `claude`); run
  `python3 -I grader/scripts/ci_grade.py`; upload `grader/ci-out/` as
  artifact `pr-grade-<PR number>` even if the step failed.

## ci_grade.py

Runs inside the workflow, from the bundle (`ROOT` is the `grader/` checkout).

1. Upstream number `<n>` from `GITHUB_HEAD_REF` (`pr/<n>`); mirror PR number
   and head sha from the event payload (`GITHUB_EVENT_PATH`).
2. Run id: `ci-<short HEAD of ROOT>`, so each grade names the bundle that
   made it.
3. Run `fetch_prs.py --pr <n> --refresh` (upstream metadata, so the author is
   the real one), then `grade.py --run-id <run id> --pr <n> -j 1`.
4. Write `ROOT/ci-out/run-id.txt` and, if graded, copy the result to
   `ROOT/ci-out/<n>.json`.
5. Report, as markdown: a first line `<!-- pr-grader -->`; then
   `**PR grader: <overall>/5**` with the run id; one bullet per comment
   `[<sentiment>] <text>`; then the effort line in the `summary.txt` format.
   If there is no result: `skipped (ignored)` if `ignored()` says so, else
   `grading failed` and exit 1 after reporting.
6. Always append the report to `GITHUB_STEP_SUMMARY`. If `PR_GRADER_MODE` is
   `comment`, also put it on the mirror PR as a single comment: edit the
   existing comment whose body starts with `<!-- pr-grader -->`, else create
   one (`gh api`). Mode `log` posts nothing.

## collect_ci.py

Args: `--mirror` (default `mirror_repo()`), `--repo` (as in `grade.py`),
`--limit` (default 100).

Pulls CI grades back so `serve.py` and the grade-review skill work on them.
`gh run list -R <mirror> --json databaseId,workflowName,status -L <limit>`,
keeping completed runs of workflow `pr-grader` (filter by name: the workflow
file lives only on `base/*` branches, so `--workflow` may not find it); for
each run, `gh run download` into a temp
dir (no error if it has no artifacts); for every `run-id.txt` found in it,
copy each `<n>.json` next to it to `results/<run id>/<n>.json` unless that
exists, printing `collected <run id> <n>`. Then run `fetch_prs.py --pr` for
collected PRs that have no `meta.json`.

<!-- AI END -->
