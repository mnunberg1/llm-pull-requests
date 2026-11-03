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

Out of scope: correctness and design burden (per the guidelines).


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

A compatibility break counts against the PR even when the description
documents it.

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

Sometimes, no comment is better than some comment. LLM generated comments
are often BEYOND useless simply because they interrupt the natural flow of
code reading, so be strict with LLM generated comments that add no value
to human comprehension


# Learning and Training

This file should be self-updating (with human approval), meaning that user
feedback should be used as a suggestion to add or refine these rubrics

Rules added from feedback must be generic: no PR numbers, repo names or
examples copied from a specific PR.
