# REPO

github.com/valkey-io/valkey-search (canonical main copy)

github.com/mnunberg1/valkey-search (writable mirror)

## Ignored authors

PRs from these authors (GitHub login, bullet list) are not fetched or graded.

- app/valkeyrie-ops

## Ignored titles

PRs whose title contains one of these (bullet list, case-insensitive) are not
fetched or graded. None for now.

- backport
- sweep

## Size classification

Used to sample PRs by size (see plan.md). Paths are prefixes relative to the
repo root.

Core source paths:

- src/
- vmsdk/src/
- third_party/hnswlib (despite being third party, they belong to the core)
- third_party/simsimd

Test paths:

- testing/
- integration/
- vmsdk/testing/

Every other path (docs, CI, build files) is not counted.