# Script specs

Spec for regenerating `scripts/` (gitignored, generated). Together with
`plan.md`, `prompt.md`, `rubric.md` and `CLAUDE.md` this should be enough to
rebuild them. If a script's behavior changes, change it here too.

Common: Python 3 stdlib only, run with `python3 -I`. Every
`argparse.ArgumentParser` gets `color=False`. `ROOT` is the parent of
`scripts/`. A repo is written `owner/name` for GitHub and `owner_name` on disk.
Each script starts with a comment saying it is AI generated.
<!-- AI BEGIN -->Right after that comment each script exits with a clear message unless it runs on
Python 3.14 or newer (`argparse` `color=False` needs it). The scripts are
committed, so a clone runs as is, and each needs only the standard library,
the files of this repo, the sibling scripts it launches, `git`/`gh` where it
uses them, and the agent CLI for model calls. Because `-I` keeps the script
directory off `sys.path` they do not import each other: the shared parts
(config loading, `ignored()`) are repeated in each, and the model call is the
separate command `agent.py`.<!-- AI END -->

Config: every script except `ci_grade.py` accepts `--config <file>`; else
`$PRDOCS_CONFIG`; else `active-config.cfg` (a symlink to the
active `<name>.cfg`). The file has `key=value` lines (blank and `#`
lines ignored); `repo=` is a path relative to the project root naming the repo
file (`repos/<name>.md`). Each script exports the chosen config in
`$PRDOCS_CONFIG` for the scripts it launches. It exits with an error if the
config or its `repo=` line is missing. "The repo file" below means that file.

Default repo: no repo name is hardcoded. A `default_repo()` helper reads
the repo file and returns the first `github.com/<owner>/<name>` match as
`owner/name`; that is the canonical repo. `--repo` overrides it.

<!-- AI BEGIN -->
Mirror repo: a `mirror_repo()` helper reads the repo file and returns, as
`owner/name`, the first `github.com/<owner>/<name>` match on a line that
contains `mirror` (case-insensitive). It returns `None` if there is none: a mirror
is optional, needed only without write access to the main repo.
`collect_ci.py` then uses the main repo; `mirror_prs.py` exits with an error for
`--pr`, `--selected`, `--open` and `--close`, and `--push-grader` pushes to the
main repo.
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
   path from the `Size classification` section of the repo file, not counting blank
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

Ignore lists: the repo file may have `## Ignored authors` and `## Ignored titles`
sections, each holding a bullet list (`- item`; other text is ignored, and so
is anything after ` (` in a bullet, which is a comment). A PR is
ignored if its author login equals an ignored author, or its title contains an
ignored title, both case-insensitive. A small `ignored()`
helper does this and is shared by `fetch_prs.py` and `grade.py`.

## grade.py

Args: `--repo` (default: `default_repo()` in the on-disk form),
`--run-id` (required), `-j` (default 4 workers), `--pr` (repeatable; grade
only these PR numbers)<!-- AI BEGIN -->, `--effort` (default `medium`; one of low, medium, high,
xhigh, max), `--agent` (see `agent.py`)<!-- AI END -->.

For each PR listed in `data/<repo>/selected.json` (all directories under
`prs/` if that file is missing), in parallel, skipping any whose `meta.json` is
ignored and any that already have `results/<owner_name>/<run-id>/<n>.json`:

1. Build the prompt, concatenated in this order: `prompt.md`; the output format
   block below (a constant in the script); `# Guidelines` + `guidelines.md`;
   `# Rubric` + `rubric.md`; <!-- AI BEGIN -->`# Test paths` + the test path prefixes of the repo
   file's `Size classification` section, one bullet each, introduced by "Files
   under these path prefixes are test files; all other files are not." (omitted
   if there are none); <!-- AI END -->`# Examples` + the files in `learning/` (see
   below); <!-- AI BEGIN -->`# Interactive feedback` + the reviewer's Q&A files (see below,
   omitted if there are none);<!-- AI END --> `# PR meta` + `meta.json`; `# Commits` + `commits.json`; `# Diff` +
   `diff.patch`. A diff over 150,000 characters is cut and gets
   `[diff truncated]` appended.
2. Run `agent.py --config <config> --effort <effort> [--agent <agent>]` with the
   prompt on stdin and take its stdout (with the default agent that is
   `claude -p --model sonnet --effort <effort> --tools ""
   --no-session-persistence`). <!-- AI BEGIN -->`--effort` is always passed, so the agent's own default
   effort level is not inherited. A failing agent is reported as `PR <n>: agent
   failed: ...` with the last 300 characters of its stderr, and nothing is written.<!-- AI END -->
3. Take the text from the first `{` to the last `}`, parse it as JSON and write
   it, indented, to `results/<owner_name>/<run-id>/<n>.json`. On a parse failure print the
   PR number, the first 200 characters of stdout and of stderr to stderr, and
   write nothing. <!-- AI BEGIN -->Before writing, check that `scores` has the three integer
   scores 1-5 (else it is a parse failure) and set `overall` to the weighted
   average `0.75 * readability + 0.125 * atomicity + 0.125 * description`,
   rounded half up (`WEIGHTS` constant and `overall()` in the script); any
   `overall` from the model is replaced. Keys are written in the order `pr`,
   `scores`, `overall`, `overall_with_tests`, `files`, `dirs`, then the rest.
   Results from before this have `overall` only, and every reader must cope
   with a missing `scores`.

   Test scores and per-file scores (all in `grade.py`): `scores` also has
   `test_readability`, an integer 1-5 or null (anything else is a parse
   failure). A file is a test file if its path starts with a test path prefix
   (`is_test()`). `changed_lines(diff)` gives each file's added plus deleted
   lines, not counting blank or comment-only lines (the rule `fetch_prs.py`
   uses). `files` keeps the model's entries for files that are in the diff
   (others, duplicates and bad scores are dropped) as `{path, readability,
   tests, lines}`. `overall_with_tests` is the `overall` formula with
   readability replaced by `(1 - s) * readability + s * test_readability`,
   `s` being the test files' share of all changed lines; it equals `overall`
   if `test_readability` is null or no test lines changed. `dirs` has, for
   every directory above a scored file, `{path, readability, files, lines}`:
   the mean file readability weighted by changed lines (at least 1 per
   file), to one decimal.<!-- AI END -->
4. Print `graded <n>`.

<!-- AI BEGIN -->
With `--pr`, grade `prs/<n>` for each given number whether or not it is in
`selected.json` (it must have been fetched).
<!-- AI END -->

Examples: every `learning/*.md`, in name order, each under a `## <file name
without extension>` header. Omit the `# Examples` section when there are none.
A small helper builds this and is shared by `grade.py` and `explain.py`.

<!-- AI BEGIN -->
Interactive feedback: every `learning/interactive-feedback/<owner_name>/*.md`
of the repo being graded, oldest first (by the 15-character timestamp at the end
of the name), each
under a `## <file name without extension>` header, with its leading `<!-- ... -->`
comment removed, except the file(s) of the PR being graded, so a regrade does not
see the reviewer's answer to that PR. Only this repo's folder is read. A
helper `interactive_feedback(repo, pr)` does this in `grade.py` and `explain.py`
(which also adds `# Test paths`, as `grade.py` does, so its input stays the
same as the grader's). These files do not change the run id of the web UI,
since feedback keeps accumulating and is not a version of the rubric.
<!-- AI END -->

Output format block (the only place the JSON shape is defined for the model;
wording and nature of the grading stay in `prompt.md`):

```
Return ONLY a JSON object, no prose, no code fences:
{"pr": <number>, "scores": {"atomicity": <integer 1-5>, "description": <integer 1-5>, "readability": <integer 1-5>, "test_readability": <integer 1-5, or null if no test files changed>}, "files": [{"path": "<path as in the diff>", "readability": <integer 1-5>}, ...], "comments": [{"sentiment": <integer 1-5>, "text": "<comment>"}, ...], "effort": {"author_minutes": <integer>, "review_minutes": <integer>}}
```

## extract_feedback.py

<!-- AI BEGIN -->
Args: `run_id` (positional), `pr` (positional number), `--repo` (as in
`grade.py`), `--config`. No model call.

Turns the reviewer's feedback on one PR into a Q&A file for the grader (see
"Interactive feedback" above), so that feedback can improve later grades without
a rubric change after every response. Called by the web UI on every feedback
save and by the grade-review skill after every recorded reply.

1. Delete every `learning/interactive-feedback/<owner_name>/<pr>-<digits>*.md`
   (not the diff examples `<pr>-example-<timestamp>.md` that the web UI writes). If
   `grades/<owner_name>/<pr>.txt` or the result `results/<owner_name>/<run-id>/<pr>.json`
   is missing, stop (so emptied feedback leaves no file).
2. Split the grade file: the grade (`overall:`), the general notes, and the
   `c<i>: <reply>` lines (as `webui.py` does), `i` numbering the result's
   comments from 1. If there is no grade, no notes and no reply, stop.
3. Write `learning/interactive-feedback/<owner_name>/<pr>-<YYYYmmdd-HHMMSS>.md`
   (one current file per PR; saving again replaces it with a newer timestamp):
   an AI-generated comment line, `# Feedback on PR <n>: <title>`, bullets
   `repo`, `run`, `saved`, `grader overall: N/5` (if the result has it) and
   `reviewer grade: N/5` (if given), then for each comment that has a reply
   `## Q: <comment text> [sentiment N]` and `A: <reply>`, and if there are
   general notes `## Notes` and the notes. Comments without a reply are left
   out. Whitespace in a comment or reply is collapsed to single spaces.
   Print `wrote <file name>`.
<!-- AI END -->

## agent.py

<!-- AI BEGIN -->
Args: `--agent`, `--effort` (low, medium, high, xhigh, max; default: the
agent's own), `--model`, `--config`.

The one place that calls a model, so the grader does not depend on Claude.
Reads the prompt from stdin, writes the agent's stdout to stdout and its stderr
to stderr, and exits with its exit code. Standard library only; the agent is
chosen by `--agent`, else `$PRDOCS_AGENT`, else the `agent=` line of the config
(`--config`, else `$PRDOCS_CONFIG`, else `active-config.cfg` if it exists;
a missing config or line is fine), else `claude`. The model is `--model`, else
`$PRDOCS_MODEL`, else `sonnet` for claude and the agent's own for the rest.

- `claude`: `claude -p --model <model> --tools "" --no-session-persistence`,
  plus `--effort <effort>` if given.
- `codex`: `codex exec --skip-git-repo-check --sandbox read-only
  [-c model_reasoning_effort="<effort>"] [-m <model>] -`, with the prompt on
  stdin (xhigh and max become high). Untested here: no `codex` was installed.
- anything else is a command line (split like a shell would, so `gemini -p`
  works) that reads the prompt on stdin and prints the reply on stdout. It
  gets `$PRDOCS_EFFORT` and `$PRDOCS_MODEL` in its environment (empty if
  unset).

If the command is not on `PATH`, exit with a message that says how to choose
another agent. The grading prompt asks for JSON only, so a custom agent must
return the reply text and not a transcript.
<!-- AI END -->

## explain.py

Args: `run_id` (positional), `pr` (positional number), `question` (optional
positional), `--repo` (default: `default_repo()` in the on-disk form), <!-- AI BEGIN -->`--resolve`<!-- AI END -->, <!-- AI BEGIN -->`--annotate-source`<!-- AI END -->.

Asks the model to explain a stored grade. Never writes to `results/` or
`grades/`.

1. Build the same input as `grade.py` (prompt, guidelines, rubric, examples,
   PR meta, commits, diff, same truncation), but without the output format block. The
   prompt is under a `# Grading prompt you were given` header.
   <!-- AI BEGIN -->The diff is numbered after truncation: `number_diff()` puts the
   new-file line number in front of every added or unchanged line of a hunk
   (`{n:>5}| <line>`, taken from the `@@ -a,b +c,d @@` header), and five spaces
   and `| ` in front of a removed one. It also returns an index `{path: {line:
   text}}`.<!-- AI END -->
2. Append `# Your previous answer` + `results/<owner_name>/<run-id>/<pr>.json`.
3. Append `# Question` + the question. With no question use: "Explain why you
   gave these scores (atomicity, description, readability) and each comment. Quote the rubric or guideline
   text you relied on, and say where it was ambiguous."
4. Prefix an instruction: answer in plain text (not JSON); the length limits in
   the grading prompt apply to the grade, not to this answer; be honest if the
   rubric is ambiguous or you would now weigh something differently.
   <!-- AI BEGIN -->The prefix also says: the diff has line numbers that are not code;
   when pointing at code, cite it as `[[<path>:<line>]]` or
   `[[<path>:<start>-<end>]]` (path as in the diff, new-file line numbers,
   ranges of about 10 lines at most, only lines that exist in the diff, next to
   the point they support, not for points about the title, description or
   commits). The web UI and the grade-review skill turn these into links.<!-- AI END -->
5. Run `agent.py --config <config> [--agent <agent>]` (no `--effort`) with the
   prompt on stdin and print its stdout. `--agent` is also accepted.
   <!-- AI BEGIN -->With `--resolve`, then print `Referenced code:` and, for each distinct
   citation in the reply, the citation line followed by the numbered diff
   lines it names (`resolve()`, at most 40 lines per citation; the path may be
   a suffix of the diff's path), or `  (not in the diff)`. This shows whether
   the model cited real lines.<!-- AI END -->

<!-- AI BEGIN -->
`--annotate-source`: instead of an explanation, find where each comment of the
stored grade points in the diff. Same input as above (numbered diff,
question omitted), with an instruction prefix asking, for each comment, for 0
to 3 locations of at most 10 lines each (none for comments about the title,
description, commits or the PR as a whole), as JSON only: `{"annotations":
[{"comment": <1-based>, "refs": [{"file", "start", "end"}]}]}`. The script
checks the reply against the diff index (`check_refs()`): a ref whose file or
start line is not in the diff is dropped, the path is made the diff's path,
and `end` is clamped to `start`..`start`+9 and to an existing line. It prints
the checked JSON and nothing else. This is the only extra keyword argument so
far; the grade-review skill has the matching keyword `annotate-source`.
<!-- AI END -->

## serve.py

Args: `run_id` (positional), `--repo` (as above), `--port` (default 8765).
Serves on 127.0.0.1, silences request logging, opens the page in the browser,
creates `grades/` if missing, writes `summary.txt` at startup.

Data per PR, for each `results/<owner_name>/<run-id>/<n>.json` in numeric order: `pr`,
`title`, `author` (from `meta.json`), `url`
(`https://github.com/<owner>/<name>/pull/<n>`), `model` (the `overall`),
`comments`, `effort` (null if absent) and the human fields `mine` and `notes`
from `grades/<owner_name>/<n>.txt`.
A comment that is a plain string (older runs) is treated as
`{sentiment: null, text: <string>}`.

`grades/<owner_name>/<n>.txt`: `overall: <1-5 or empty>`, then `notes:`, then the notes.
Missing file means no grade and no notes.

Routes:
- `GET /data`: JSON list of the data above.
- `POST /save`: body `{pr, mine, notes}`. If both are empty delete the file,
  otherwise write it in the format above. Then regenerate `summary.txt`.
- Any other GET: the page.

`results/<owner_name>/<run-id>/summary.txt`: per PR a line
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
mirror. The bundle is `prompt.md`, `rubric.md`, `guidelines.md`, `active-config.cfg` (a copy of the selected config) and the repo
file at its `repo=` path, `learning/*.md` and `scripts/*.py` from this checkout. Commit it on top of the
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
  macOS, ARM64]` (the user's Mac, using its logged-in agent; no API key),
  20 min timeout. Env: `GH_TOKEN` (the workflow token), `PR_GRADER_MODE`
  (repo variable, default `log`), <!-- AI BEGIN -->`PRDOCS_AGENT` (repo variable; empty means claude)<!-- AI END -->.
- Steps: check out branch `pr-grader` into `grader/` (never the PR's code);
  print `python3 --version` and, if there is one, `claude --version` (the runner's
  PATH must provide Python 3.14+, since the scripts use `color=False`, and the
  agent CLI); run
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
copy each `<n>.json` next to it to `results/<owner_name>/<run id>/<n>.json` unless that
exists, printing `collected <run id> <n>`. Then run `fetch_prs.py --pr` for
collected PRs that have no `meta.json`.

<!-- AI END -->

<!-- AI BEGIN -->

# Web UI

See `webui.md` for the requirements. `webui.py` is the one script that does
not take `--config`: a single server works on any repo, and picks (or creates)
the config per request from the repo link the user enters. Config files are
never repointed (`active-config.cfg` is left alone); every script it launches
is run as `python3 -I scripts/<name>.py --config <cfg>`.

## webui.py

Args: `--port` (default 8766), `--no-browser`, <!-- AI BEGIN -->`--agent` (sets `$PRDOCS_AGENT`, which
the scripts it runs inherit)<!-- AI END -->. Serves on 127.0.0.1 only
(`ThreadingHTTPServer`, silent), opens the page in the browser unless
`--no-browser`. POSTs are refused without an `X-Role` header (a custom header
forces a CORS preflight, which blocks other sites from posting), and any
request whose `Host` is not `127.0.0.1:<port>` or `localhost:<port>` is
refused (DNS rebinding).

Config for a repo: the `<name>.cfg` in `ROOT` (not the symlink) whose repo file
has the repo as its first `github.com/<owner>/<name>` link. If there is none,
create `repos/<name>.md` from `repos/example.md` and `<name>.cfg` with
`repo=repos/<name>.md` (`<owner>-<name>` as the name if `<name>` is taken):
the first link is replaced by the repo, the mirror paragraphs and the
`<login>` and `<substring>` placeholder bullets are removed, the file is
wrapped in `<!-- AI BEGIN -->`/`<!-- AI END -->`, and the `.cfg` gets a first
comment line saying it is AI generated. The page tells the user that the
repo file was created from the template and that its `Size classification`
should be reviewed.

Run id: `web-<first 8 hex of the md5 of prompt.md, rubric.md, guidelines.md,
learning/*.md and the repo file, concatenated>`. A new rubric, prompt or repo
file version therefore gets a new run, and an unchanged one reuses its cached
grades (`grade.py` skips existing results).

Roles: the page has a user switch, `user` or `root`, kept in the browser and
sent as the `X-Role` header. There is no authentication; the server only
enforces that `root` is required to apply changes. Everyone can submit them
to the queue.

Jobs: slow work (scripts and model calls) runs in a thread as a job, kept in
memory: `{id, status: running|done|error, log: [lines], result, error}`.
`GET /api/job/<id>` returns it. The page polls.

Routes (JSON in and out, errors are HTTP 400 with `{"error": ...}`). `repo` is
the on-disk form `owner_name`:

- `GET /`: the page.
- `POST /api/start` `{mode: single|iterative, url}`. Single takes a PR link
  (`https://github.com/<owner>/<name>/pull/<n>`), iterative a repo link (or
  `<owner>/<name>`). Finds or creates the config (above) and starts a job.
  Returns `{job, repo, run, created: [files]}`.
  - single: `fetch_prs.py --pr <n>`, then `grade.py --run-id <run> --pr <n>
    -j 1`. If fetch printed `ignored <n>`, the job ends with an error saying
    the repo file ignores it. Result: `{repo, run, prs: [n]}`.
  - iterative: `fetch_prs.py` (the 10+10+10 sample; reuses `selected.json`),
    then sets the result `{repo, run}` and goes on with `grade.py --run-id
    <run> -j 4`, so the page can start reviewing while grading continues.
- `GET /api/list?repo=&run=`: the PRs of `selected.json` (newest first) as
  `{pr, title, author, bucket, size, graded, model, reviewed, mine}`;
  `reviewed` means a `grades/` file exists.
- `GET /api/recent`: the 20 most recently saved `grades/` files across repos
  that have a config, newest first, as `{repo: owner/name, pr, title, mine,
  url}`. There is no user database, so "reviewed by the user" means having
  saved feedback.
- `GET /api/pr?repo=&run=&pr=`: `{pr, title, author, url, state, body, model,
  comments, effort, scores, with_tests, files, dirs, mine, notes, responses, refs,
  diff, run_stale}` (`with_tests` is `overall_with_tests`; `scores`, `with_tests`, `files` and
  `dirs` are null for results from before they existed). Comments are
  as in `serve.py`; a comment may also have `file` and `line` (optional; the
  grader's output contract does not ask for them yet), which the page uses to
  annotate the diff. `responses` is a list parallel to `comments` of strings (my reply to each
  comment, empty if none). `refs` is a list parallel to `comments`, each a list of `{file, start, end}`
  (where the comment points in the diff), or null if the PR is not annotated
  yet. `diff` is `diff.patch`. `run_stale` is true when the run
  id is no longer the current run id (the rubric, prompt or repo file changed).
- `POST /api/feedback` `{repo, run, pr, mine, notes, responses}`: writes
  `grades/<owner_name>/<n>.txt` in the `serve.py` format. The notes text
  comes first, then one line per comment with a reply,
  `c<i>: <text>` (`i` from 1; the same inline
  form the grade-review skill uses), so both tools read each other's files.
  Reading splits them back. If everything is empty, the file is deleted.
  <!-- AI BEGIN -->Then it runs `extract_feedback.py` for the PR (and `run`), so
  `learning/interactive-feedback/` follows the saved feedback; if that fails the
  save is reported as an error.<!-- AI END -->
- `POST /api/propose` `{repo, run, pr}`: job. Sends the model (through
  `agent.py`, like every model call) the current
  `rubric.md`, `prompt.md` and repo file, the PR meta, the stored grade and my
  feedback, and asks for JSON only: `{"proposals": [{"file", "old", "new",
  "why"}]}`. `file` is `rubric.md`, `prompt.md` or the repo file path
  (nothing else); `old` is exact existing text to replace, or empty to append;
  `why` names the feedback it is based on. Prompt rules: change only what the
  feedback motivates, none if it does not; generic wording, no PR numbers,
  repo names, authors; few sharp rules; no conflicts; wrap at 80 columns.
  Invalid proposals (bad file, `old` not found exactly once) are dropped. Job
  result `{proposals}`. With no feedback at all, error.
- `POST /api/apply` `{repo, proposals}`: `root` only (else 403). Validates all
  proposals first (same checks), then applies them in order: `old` replaced
  by `<!-- AI BEGIN -->new<!-- AI END -->` (just deleted if `new` is empty),
  or, for empty `old`, `new` appended wrapped in the markers. Returns
  `{ok, run}` with the new run id.
- `POST /api/queue` `{repo, run, pr, proposals}`: any role. Writes one
  Markdown file `webui-review-queue/<owner_name>/<timestamp>-<pr>.md` (a
  directory in the project root, not gitignored, so it can be reviewed and
  committed). The file starts with an AI-generated comment and a title line,
  then `- key: value` lines (`repo`, `run`, `pr`, `title`, `role`, `at`,
  `status`: pending|applied|dismissed), then per proposal a `## <i>. <file>`
  section with `Why:`, a `diff` block for reading, and `Old:` and `New:`
  blocks, which are what gets applied and parsed back. Code fences are one
  backtick longer than the longest run in their content. A status change
  rewrites the `- status:` line.
- `GET /api/queue`: every queue item parsed from those files (`{id, repo, run,
  pr, title, role, at, status, proposals}`), newest first, all repos.
- `GET /api/repos`: the existing configs as `[{repo: owner/name, cfg}]`
  (symlinks skipped), for the repo picker.
- `POST /api/queue/apply` `{repo, id}`: `root` only. Applies as `/api/apply`
  and sets `status: applied` (stale proposals: error, stays pending).
- `POST /api/queue/dismiss` `{repo, id}`: `root` only; `status: dismissed`.
- `POST /api/annotate` `{repo, run, pr}`: job. Runs `explain.py
  --annotate-source` once and caches its JSON in
  `results/<owner_name>/<run>/annotations/<n>.json` (a subdirectory, so
  `serve.py` does not read it as a result); later calls reuse it. Job result
  `{refs}` as in `/api/pr`.
- `POST /api/example` `{repo, run, pr, file, from, to, comment}`: any role, no
  approval. Saves part of the diff plus a comment as a Q&A file for the grader,
  `learning/interactive-feedback/<owner_name>/<pr>-example-<timestamp>.md`
  (a second in the future if that name exists). `file` is a path in the diff
  and `from`..`to` are indices into that file's diff lines (the lines after its
  `diff --git` line, as the page counts them, hunk headers included); the
  server takes the text from `diff.patch` itself, at most 200 lines, and
  refuses an empty comment or a selection that is not in the diff. File: an
  AI-generated comment, `# Example from PR <n>: <title>`, bullets `repo`, `saved`,
  `file` and `new-file lines` (first to last new-file line number of the
  selection, if it has any), `## Q: Code from the diff of <file>` with the
  lines in a `diff` block, and `A: <comment>`.
- `POST /api/explain` `{repo, run, pr, question}`: job running `explain.py`;
  result `{text}`.

Page: a single self-contained HTML document with inline JS, light/dark as in
`serve.py`, mobile-style: 17px text, 48px high inputs and buttons, segmented
controls, rounded cards, toggle chips and 1-5 buttons instead of selects, a
sticky action bar, and a 780px column. Sticky top bar: user switch (user /
root) and tabs Grade and Queue. Grade tab: a mode switch (Single PR /
Iterative), in single mode a select of recent PRs (`/api/recent`, refreshed
after each save) that fills the input so a PR can be graded again after the
rubric changed, in iterative mode a select of existing repos (`/api/repos`) that
fills the input, one input (PR link or repo link, by mode) and a Grade
button, with the job log underneath. Then the review
screen:

- the PR card: link, author, state, the model's `N/5` (`no tests N/5 · with
  tests M/5` when they differ), the scores with their weights (readability
  75%, atomicity 12.5%, description 12.5%, plus test readability when not
  null; hidden for older results without `scores`), a collapsed list of
  readability per file and directory (directories first, indented; a file
  opens in the diff when clicked), effort line, each
  comment with its sentiment badge, file:line if it has one, and a text box for
  my reply to it; my
  1-5 grade (buttons), notes, an "Ask the grader" box (runs `/api/explain`, shows the
  answer; every `[[path:line]]` or `[[path:start-end]]` citation in it becomes a
  link that opens that file in the diff, scrolls to the lines and highlights
  them, and is marked as missing if the file or lines are not in the diff);
- the PR description (`body`), rendered as Markdown (a small built-in
  renderer: headings, lists, tables, quotes, code, bold, italic, links; all
  text is HTML-escaped first and only http(s) links are kept), above the
  diff, open by default;
- the diff of the PR, collapsible per file (built when opened), annotated:
  each comment is shown under the first line of every location in `refs` and
  opens its file, and its card lists the locations as links that scroll to and
  highlight the lines. A comment with `file` and `line` of its own (grader
  output) is used if it has no refs. When `refs` is null the page calls
  `/api/annotate` in the background, says so under the Diff heading, and
  redraws when it returns (or says it failed). Comments with no location are
  listed only on the card;
- buttons: "Save" (iterative: "Save & next", which shows the next graded PR
  that has no feedback; once grading is done, then those where my grade and
  the model's differ by 2 or more; each PR is shown once per session; or waits
  for grading, or says it is done), plus "Skip" and "Back" (iterative only), and "Save &
  propose changes", which saves and shows the proposals as red/green diffs per
  file, with "Apply now" (disabled for `user`, with a hint) and "Queue for
  review"; after either, iterative moves on. Single mode also has "Regrade"
  (runs the job again, which uses the current run id);
- selecting any part of the diff: tap a line, tap another to extend the
  selection (within one file, removed lines and hunk headers included; tapping
  again starts a new one). A bottom sheet shows the selection, a comment box,
  "Submit as example" (`/api/example`, then a short confirmation) and "Clear".
  Selecting text by dragging does not select lines;
- a banner when `run_stale` is true.

Feedback forms are limited to what `plan.md` and the grade-review skill have:
a 1-5 grade, a reply to a comment (`c<i>`), general notes, a question to the
grader, a proposal of changes (applied or queued), and next, skip and back.
Nothing else is added (no per-comment ratings or verdict types).

Queue tab: items with status, PR, who queued them and their diffs; `root`
gets Apply and Dismiss on pending ones.

<!-- AI END -->
