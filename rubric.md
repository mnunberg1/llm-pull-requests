# Rubric (rubric.md)

Criteria to weigh qualitatively (not scored individually):

1. Commit atomicity – each commit is one conceptual change.
2. Description quality – concise, explains the problem and why; not a long
   LLM-style layout with tables.
3. Comment style – no multi-line LLM rationale comments.
4. LLM annotation – LLM-generated files/functions are declared.
5. LLM/human separation – LLM code isolated in its own functions/modules, not
   interleaved.
6. API surface – does not extend or modify existing APIs/structures without
   justification.
7. Test proportionality – good coverage, minimal code; readable in reasonable
   time.
8. Golden rule – reviewer effort is unlikely to exceed author effort.


Place priority on the natural review order:

1. Does the title make sense?
2. Is the description easy to read?
3. Are potential compatibility/API changes documented in the description?
4. Can I get a sense of what's happening by just skimming through the diff?
5. Can I get a sense of what's happening by just looking at the commit titles
   and descriptions?

<!-- AI BEGIN -->Out of scope: correctness and design burden (per the guidelines).

<!-- AI BEGIN -->
When the PR's stated purpose is a refactor that enables a feature, the
refactor is part of the change. Do not lower the readability or atomicity
score, or raise a negative comment, merely because the refactor and the
feature are in the same PR. Judge how clearly the refactor is explained and
how cleanly it is organized across commits.
<!-- AI END --><!-- AI END -->


Things to consider:

Long descriptions/LLM tables may be justified for PRs which substantially
change or modify performance (e.g. CPU consumption, memory footprint).

Tables are acceptable and informative when it compares performance across
different workloads or configurations, but are unacceptable when the same
performance metric can be restated in a simple sentence. For example>

| | Before | After |
|---|---|---|
| `eventloop_duration_max` | 1141 / 1283 ms | 25 / 33 ms |
| Max PING latency | 1124 / 1249 ms | 21 / 17 ms |
| Total backfill time | 12.4 / 12.6 s | 34.8 / 34.6 s |

is not a helpful table, and it would have been easier to say "this increases
backfill time by 34.8%, however, it reduces latency and this is the correct
and intended behavior".

Long descriptions are more justified for larger PRs than they are for
smaller ones, but ideally the explanations should be present within
each commit message.

<!-- AI BEGIN -->

Description length should be proportional to the size (and/or impact) of
the change. A performance table or multi-section description on a small fix is
a negative even when accurate because it adds line noise.
It is justified only when the PR's purpose is performance and the table is the
evidence.

Judge a table on what it shows, not on its size. In a performance PR, do not
penalize a results table; penalize the prose around it (implementation
detail, repeated sections) on its own merits.

Comments that explain WHY (rationale, history, design choices) are a
negative, however short. Comments should say what the code does or document
parameters and return values. Never praise rationale comments.

Do not penalize terse descriptions or commit messages on trivial docs, CI or
tooling changes. Expectations scale with the size and risk of the change.

<!-- AI BEGIN -->A compatibility break is not a readability negative by itself. When the
description states it clearly, do not count it against the PR or lower the
readability score for it, and do not raise it as a negative comment. When it is
undocumented or unclear, count that against the description score.<!-- AI END -->

Automated PRs from bots are not graded; the repo file <!-- AI BEGIN -->(`repos/<name>.md`)<!-- AI END --> lists which to skip.

<!-- AI END -->

<!-- AI BEGIN -->

Use established terminology: the words in the issue, the code and the project
docs. Invented or coined terms for ordinary concepts, in the title,
description, names or comments, are a negative.

A large amount of generated code, such as tests or tooling, needs a short
human-written message saying what it checks and why, even when the fix is
tiny. The size of the generated part should match what the human-provided
information (the issue, the fix) justifies; scaffolding beyond that is a
negative.

The description must match the final state of the PR. Text about work that
was reverted or replaced is a negative.

Where LLM-generated code is a black box, the PR must say where it is used, so
the reviewer knows where to look and where not to look. A bare "LLM-generated"
note without locations is not enough.

<!-- AI END -->

<!-- AI BEGIN -->

Scores. Give three separate 1-5 scores (5 is best). This replaces "not scored
individually" above: the criteria are grouped into three scores, and the
criteria inside a group are still weighed qualitatively. The final grade is
the weighted average, so the code itself counts most:

- Code readability, 75% of the final grade: criteria 3 and 5, 6 and 8 (comment
  style, LLM/human separation, API surface, golden rule) and
  review step 4 (a sense of what is happening from skimming the diff). Judge
  the non-test files only; test files get their own score, below.
- Commit atomicity, 12.5%: criterion 1, and review step 5 (commit titles and
  messages).
- Description quality, 12.5%: criteria 2 and 4, and review steps 1-3 (title,
  description, compatibility notes).

Judge each score on its own criteria; do not lower one because another is
weak. A rule below belongs to the score of the part it is about (a rationale
comment is readability, a long description is description).

Test readability. Also give a 1-5 test readability score for the test files
(omit it if the PR changes none). Judge it on its own merit: only the test
files' code and comments (criteria 3 and 7), never the source code, the
description or the commits, and do not let the quality of the source raise or
lower it. Use a looser threshold than for other code: repetition, fixture and
table boilerplate and longer bodies are normal in tests. Judge whether a
reviewer can see what each test checks in reasonable time. The grade without
tests ignores it; the grade with tests counts it in
proportion to the test files' share of the changed lines.

Per-file scores. Also give a 1-5 readability score for each changed file that
has code or comments to read (skip generated, data and lock files), with the
threshold for its kind: the test threshold above for test files, the
readability criteria for the rest. Judge each file on its own changes. These
are not averaged into the grades.

<!-- AI END -->

<!-- AI BEGIN -->

Readability depends on how much the reviewer has to hold in mind, not on how
many lines changed:

- A large amount of code that is self-contained and reached from a single
  place (for example a new file with one call site) is a small readability
  burden. Do not lower the readability score for its size alone.
- A small edit of a few lines repeated across many places is a larger burden
  than its line count suggests: the reviewer must find and re-check each site.
- Consistent changes are cheap to review: the same type of change everywhere,
  such as a renamed type or function, a swapped call or an added parameter.
  Check one instance and skim the rest. Varied, disparate changes spread over
  many places are expensive even when each is small. Weigh that difference,
  not the number of files or lines touched.

<!-- AI END -->

Sometimes, no comment is better than some comment. LLM generated comments
are often BEYOND useless simply because they interrupt the natural flow of
code reading, so be strict with LLM generated comments that add no value
to human comprehension


# Learning and Training

This file should be self-updating (with human approval), meaning that user
feedback should be used as a suggestion to add or refine these rubrics

Rules added from feedback must be generic: no PR numbers, repo names or
examples copied from a specific PR.

<!-- AI BEGIN -->

Instead of changing this file after every response, the reviewer's replies to
the grader's comments can be kept as question and answer files under
`learning/interactive-feedback/`, one folder per repo. If an "Interactive
feedback" section follows the examples, read it as the reviewer's judgement on
earlier grades of this repo: make the kinds of comments the reviewer asked for
and avoid the kinds they rejected.

<!-- AI END -->
