# ATIF test fixtures

These ATIF `trajectory.json` files are copied from harbor's golden tests (MIT
licensed), prefixed with the agent name:

- `openhands_hello-world.trajectory*.json` — from `tests/golden/openhands/hello-world.trajectory*.json`
  at harbor [`de2f043d`](https://github.com/harbor-framework/harbor/tree/de2f043d/tests/golden/openhands)
  (that directory was later removed upstream in
  [harbor#1936](https://github.com/harbor-framework/harbor/pull/1936), so it's pinned to the
  last commit that had it).
- `terminus_2_hello-world-context-summarization-linear-history.trajectory*.json` — from
  [`tests/golden/terminus_2/`](https://github.com/harbor-framework/harbor/tree/v0.16.1/tests/golden/terminus_2)
  at harbor `v0.16.1`. Copied post [harbor#1844](https://github.com/harbor-framework/harbor/pull/1844),
  so the summarization handoff step carries `extra.context_management` (exercises the compaction path).
