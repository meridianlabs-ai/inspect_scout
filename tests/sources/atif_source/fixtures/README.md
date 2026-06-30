# ATIF test fixtures

These ATIF `trajectory.json` files are copied from
[harbor's golden tests](https://github.com/harbor-framework/harbor/tree/main/tests/golden)
(MIT licensed):

- `openhands_hello-world.trajectory*.json` — from `tests/golden/openhands/`.
- `terminus_2_hello-world-context-summarization-linear-history.trajectory*.json` — from
  `tests/golden/terminus_2/`. Copied post
  [harbor#1844](https://github.com/harbor-framework/harbor/pull/1844), so the summarization
  handoff step carries `extra.context_management` (exercises the compaction path).
