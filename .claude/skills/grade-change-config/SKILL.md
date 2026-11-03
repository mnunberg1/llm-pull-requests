---
name: grade-change-config
description: Switch the active PR-grader configuration by repointing the
  active-config.cfg symlink. Use when the user runs /grade-change-config, or
  asks to switch, change or select the repo or config being graded.
---

<!-- AI generated -->

# Change the active configuration

The active configuration is the symlink `active-config.cfg` in the project
root, pointing at a `<name>.cfg` whose `repo=` line names a file in `repos/`.
The status bar and every script read it. See `plan.md` ("Active
configuration").

1. Show the current one: `readlink active-config.cfg` (or "none" if missing or
   dangling).
2. Pick the target:
   - The argument, if given (`valkey` or `valkey.cfg`; add `.cfg` if missing).
   - Otherwise list the `*.cfg` files in the project root, except
     `active-config.cfg`, mark the current one, and ask which to use.
3. Validate the target: the file exists, has a `repo=<path>` line, and that
   path exists. If not, say what is wrong and change nothing.
4. If it is already active, say so and stop.
5. Switch: `ln -sfn <name>.cfg active-config.cfg`. Never edit or delete a
   `.cfg` or `repos/*.md` file.
6. Confirm in one line: `active: <old> -> <new> (<owner/name>)`. The status bar
   updates by itself on the next refresh.
7. If the `grade-review` loop is in progress, say that the run in use may
   belong to the previous repo, and that the loop will re-run its change check
   and re-pick the run (see "Active configuration" in that skill).
