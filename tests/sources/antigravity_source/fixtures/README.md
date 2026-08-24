# Antigravity test fixtures

These fixtures are hand-written miniatures, each distilled from an edge case
observed in a real Antigravity CLI corpus (agy 1.1.14–1.1.19). The `root/`
directory mirrors the on-disk layout of `~/.gemini/antigravity-cli`
(`brain/<id>/.system_generated/logs/transcript_full.jsonl` +
`annotations/<id>.pbtxt`); real conversations are not committed because they
embed prompts, paths, and account details.

- `aaaaaaaa-…0001` — simple conversation: `<USER_REQUEST>`/settings chrome,
  session-start `{{ CHECKPOINT 0 }}`, thinking + tool call/result, one
  malformed JSONL line (exercises skip-and-warn), and the tool result's line
  flushed before its planner step's (out-of-order write, exercises the
  `step_index` sort).
- `bbbbbbbb-…0002` — mid-conversation `{{ CHECKPOINT 1 }}` compaction, a
  resume seam with a verbatim-duplicated user request, and a stream-error
  `ERROR_MESSAGE`.
- `cccccccc-…0003` — parent that spawns a sub-agent (`invoke_subagent` call,
  spawn result carrying the child `conversationId`, subagent message).
- `dddddddd-…0004` — the spawned sub-agent: chrome-wrapped prompt (subagent
  prompts carry `<USER_REQUEST>` chrome like top-level ones), parallel tool
  calls, `send_message` report.

Tests that need a `conversations/<id>.db` (generation metadata / token
usage) construct one at runtime via `helpers.write_generation_db`.
