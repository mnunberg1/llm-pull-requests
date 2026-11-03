# REPO

github.com/<owner>/<name> (canonical main copy)

github.com/<mirror-owner>/<name> (writable mirror; optional)

The mirror line is optional. A mirror is only needed to test the grader in a
GitHub workflow when you have no write access to the main repository; the PRs
are recreated there. Leave the line out if you can run the workflow on the main
repository.

## Ignored authors

PRs from these authors (GitHub login, bullet list) are not fetched or graded.

- <login>

## Ignored titles

PRs whose title contains one of these (bullet list, case-insensitive) are not
fetched or graded.

- <substring>

## Size classification

Used to sample PRs by size (see plan.md). Paths are prefixes relative to the
repo root.

Core source paths:

- src/

Test paths:

- tests/

Every other path (docs, CI, build files) is not counted.
