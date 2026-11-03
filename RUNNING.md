<!-- AI BEGIN -->

# Quick start: grade PRs on your own repo

You need: `git`, [`gh`](https://cli.github.com/) (run `gh auth login`),
Python 3.14 or newer (the scripts use `ArgumentParser(color=False)`, new in
3.14), and [Claude Code](https://claude.com/claude-code) (`claude`, logged
in). Grading calls `claude -p`, so it uses your Claude Code login; no API key
is needed.

1. Clone and enter the repo:

   ```
   git clone <this repo's URL> prdocs && cd prdocs
   ```

2. Point it at your repo. Copy `repos/example.md` to `repos/<name>.md`, write
   `repo=repos/<name>.md` in a new `<name>.cfg`, and point the symlink
   `active-config.cfg` at it (`ln -sfn <name>.cfg active-config.cfg`), and edit the repo file:
    - Replace the first `github.com/<owner>/<name>` link with the repo whose
      PRs you want to grade. This is the only place the repo name is written.
    - Fill in `Ignored authors` (bots), `Ignored titles`, and the
      `Size classification` paths (core source and test paths of your repo).
    - Optional, and only for testing the grader in a GitHub workflow when you
      cannot write to the main repo: a second link on a line containing the
      word "mirror" is a repo you can write to (see `integration.md`).

3. Generate the scripts. Only the specs are committed, so `scripts/` does not
   exist after a clone. Start Claude Code in this directory and run:

   ```
   claude --permission-mode acceptEdits \
     "Regenerate scripts/ from scripts.md, following plan.md and CLAUDE.md"
   ```

   This opens an interactive session; wait for it to finish and exit, then
   check that `scripts/` exists. (Adding `-p` runs it non-interactively.)

4. Fetch a sample of PRs (10 each of small, medium and large; once only):

   ```
   python3 -I scripts/fetch_prs.py
   ```

   For a quick trial (one PR per size, about 20 seconds), use
   `--per-bucket 1 --scan-limit 40`. The full sample scans up to 300 PRs.

5. Grade them. Use a new run id for every rubric or prompt change; old runs
   are never overwritten:

   ```
   python3 -I scripts/grade.py --run-id v1
   ```

6. Look at the grades and add your own (1-5 and notes):

   ```
   python3 -I scripts/serve.py v1      # http://127.0.0.1:8765/
   ```

7. Tune the grader to your taste. In Claude Code, run `/grade-review`: it walks
   through the graded PRs, records your feedback in `grades/`, explains the
   grader's reasoning, and proposes changes to `rubric.md`, `prompt.md` and
   the repo file for your approval. Then grade again into a new run id (step 5)
   and compare. Repeat until the grades match your judgement.

   `guidelines.md` is the standard the PRs are graded against. Replace it
   with your own guidelines if they differ.

8. Optional, once calibrated: run the grader as a GitHub Action on a mirror
   repo, using your own machine as the runner. See `integration.md`.

Files you edit: `<name>.cfg`, `repos/<name>.md`, `guidelines.md`, `rubric.md`, `prompt.md` and the
examples in `learning/`. Generated and gitignored: `scripts/`, `data/`,
`grades/`, `results/`.

<!-- AI END -->
