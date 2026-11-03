# Accepted: results table in a performance PR

Verdict: accepted. The description is fine as written.

## The pull request

Title: Restore indexing throughput after the allocator change

Description (abridged):

    Indexing got slower after the allocator change. This restores it.

    Results, ops/sec before and after:

    | Workload              | Before | After |
    |-----------------------|--------|-------|
    | Bulk insert, 128-dim  | 41k    | 58k   |
    | Bulk insert, 768-dim  | 9k     | 13k   |
    | Mixed read/write 50/50| 22k    | 27k   |
    | Search only           | 80k    | 80k   |

    The commits are one change each, so details live in the commit messages.

## Why it was accepted

- The PR's purpose is performance, so the table is the evidence for the claim,
  not decoration.
- It compares several workloads, including one that did not change, so a
  reviewer can see where the gain is and that nothing else regressed.
- The prose is short. The table carries the numbers and the sentences carry
  the reason.

## Contrast

The same table on a small bug fix, or a table with two rows that one sentence
would cover, is a negative. The table is not what makes a description too long;
repeated sections and implementation detail are.
