<!-- AI BEGIN -->

# Quick start: grade PRs on your own repo

You need: `git`, [`gh`](https://cli.github.com/) (run `gh auth login`),
Python 3.14 or newer (the scripts use `ArgumentParser(color=False)`, new in
3.14), and [Claude Code](https://claude.com/claude-code) (`claude`, logged
in). Grading calls `claude -p`, so it uses your Claude Code login; no API key
is needed. <!-- AI BEGIN -->To use Codex or another agent instead of Claude, see "Using another agent
than Claude" below.<!-- AI END -->

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

3. <!-- AI BEGIN -->The scripts in `scripts/` are committed, so there is nothing to generate;
   skip to step 4. They are generated from `scripts.md`, so if you change that
   spec, regenerate them (do not edit them by hand). Start Claude Code in this
   directory and run:<!-- AI END -->

   ```
   claude --permission-mode acceptEdits \
     "Regenerate scripts/ from scripts.md, following plan.md and CLAUDE.md"
   ```

   This opens an interactive session; wait for it to finish and exit, then
   check that `scripts/` was updated. (Adding `-p` runs it non-interactively.)

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

   <!-- AI BEGIN -->Or use the web UI, which does steps 2 to 7 in a browser. Start it with:

   ```
   python3 -I scripts/webui.py          # http://127.0.0.1:8766/
   ```

   - Pick Single PR (paste a pull request link) or Iterative (paste a repo link,
     or pick an existing repo; it takes the 10+10+10 sample and shows one PR at a
     time). A repo without a config gets `<name>.cfg` and `repos/<name>.md` made
     from `repos/example.md`; check its `Size classification`.
   - The result shows the scores (readability, atomicity, description, test
     readability), the PR description, and the diff with each comment placed at
     the code it is about. Reply to a comment, set your grade, add notes, or ask
     the grader why. Select lines of the diff and comment on them to save an
     example for the grader.
   - "Save & propose changes" asks the model for edits to `rubric.md`,
     `prompt.md` or the repo file. Switch to `root` (top right) to apply them
     at once; as `user` you can only queue them for review as Markdown files in
     `webui-review-queue/`. There is no login: the switch is a convenience, not
     security, and the server listens on 127.0.0.1 only.
   - Your replies are also kept as Q&A files in
     `learning/interactive-feedback/<owner_name>/`, which the grader reads on
     later runs, so feedback can improve grades without a rubric change.<!-- AI END -->

7. Tune the grader to your taste. In Claude Code, run `/grade-review`: it walks
   through the graded PRs, records your feedback in `grades/`, explains the
   grader's reasoning, and proposes changes to `rubric.md`, `prompt.md` and
   the repo file for your approval. Then grade again into a new run id (step 5)
   and compare. Repeat until the grades match your judgement.

   `guidelines.md` is the standard the PRs are graded against. Replace it
   with your own guidelines if they differ.

   <!-- AI BEGIN -->`/grade-review` is a Claude Code skill. Any other coding agent (Codex and
   others) can follow the same loop: `AGENTS.md` points it at
   `.claude/skills/grade-review/SKILL.md`.<!-- AI END -->

8. Optional, once calibrated: run the grader as a GitHub Action on a mirror
   repo, using your own machine as the runner. See `integration.md`.

Files you edit: `<name>.cfg`, `repos/<name>.md`, `guidelines.md`, `rubric.md`, `prompt.md` and the
examples in `learning/`. Generated and gitignored: `data/`, `grades/`,
`results/`. <!-- AI BEGIN -->`scripts/` is generated from `scripts.md` and committed.

## Using another agent than Claude

Every model call (grading, the grader's rationale, the web UI's proposals) goes
through `scripts/agent.py`, which reads a prompt on stdin and prints the reply.
Claude Code (`claude`, logged in) is the default; choose another one with, in
order of priority, `--agent` on `grade.py`, `explain.py`, `webui.py`,
`$PRDOCS_AGENT`, or an `agent=` line in the `<name>.cfg`:

```
python3 -I scripts/grade.py --run-id v1 --agent codex
PRDOCS_AGENT=codex python3 -I scripts/webui.py
agent=codex                        # in <name>.cfg
```

- `claude`: `claude -p --model sonnet`, no tools.
- `codex`: `codex exec` in a read-only sandbox (untested: it was not installed
  where this was written). `$PRDOCS_MODEL` or `agent.py --model` picks its
  model.
- anything else is a command line that reads the prompt on stdin and prints
  the reply on stdout, for example `agent=gemini -p`. It gets `$PRDOCS_EFFORT`
  and `$PRDOCS_MODEL` in its environment. The reply must be the model's answer
  only: the grader asks for a JSON object and takes the text between the first
  `{` and the last `}`.

`grade.py` passes `--effort medium` to the agent by default (`--effort` changes
it). `python3 -I scripts/agent.py --help` lists the rest. Another model may grade
differently from Claude: use a new run id and compare before trusting it.
<!-- AI END -->

<!-- AI END -->
