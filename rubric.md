# Rubric (rubric.md)

Criteria to weigh qualitatively (not scored individually):

1. Commit atomicity – each commit is one conceptual change.
2. Description quality – concise, explains the problem and why; not a long LLM-style layout with tables.
3. Comment style – no multi-line LLM rationale comments.
4. LLM annotation – LLM-generated files/functions are declared.
5. LLM/human separation – LLM code isolated in its own functions/modules, not interleaved.
6. API surface – does not extend or modify existing APIs/structures without justification.
7. Test proportionality – good coverage, minimal code; readable in reasonable time.
8. Golden rule – reviewer effort is unlikely to exceed author effort.


Place priority on the natural review order:

1. Does the title make sense?
2. Is the description easy to read?
3. Are potential compatibility/API changes documented in the description?
4. Can I get a sense of what's happening by just skimming through the diff?
5. Can I get a sense of what's happening by just looking at the commit titles and descriptions?

Out of scope: correctness and design burden (per the guidelines).


Things to consider:

Long descriptions/LLM tables may be justified for PRs which substantially
change or modify performance (e.g. CPU consumption, memory footprint).
Tables, however, only make sense if there are more than two columns or
rows. For example

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

Sometimes, no comment is better than some comment. LLM generated comments
are often BEYOND useless simply because they interrupt the natural flow of
code reading, so be strict with LLM generated comments that add no value
to human comprehension


# Learning and Training

This file should be self-updating (with human approval), meaning that user feedback
should be used as a suggestion to add or refine these rubrics
