# Preserve transcript fields across JSON key order

## Scope and evidence

Fix defect 2 in the materialized transcript reader on `origin/main`, starting
from `b61f5c067`. The agreed scope protects messages, target, scores, and sample
metadata from the reader's premature exit at `events`.

The affected recovered `.eval` sample contains 31,596 inline message objects.
Its `events` key is at index 4 and its `messages` key is at index 24. Reading it
through `transcripts_from(...).reader().read(...)` with
`TranscriptContent(messages="all")` returns zero messages on the base commit.
An independent incremental parse of the archive confirmed the message count
and key positions.

A small sample reproduces the same failure without production data. Give it
two messages, a target string, nonempty scores and metadata, an empty events
array, and an empty attachments object. Serialize the same values in these
orders and call `load_filtered_transcript(..., messages="all", events=None)`:

| Top-level key order | Current result |
| --- | --- |
| target, messages, scores, metadata, events, attachments | Two messages and all three metadata fields |
| target, events, metadata, scores, messages, attachments | Zero messages; only target survives |
| target, messages, events, metadata, scores, attachments | Two messages; only target survives |

The third case demonstrates why checking messages alone is insufficient.

## Approaches considered

1. **Guard all needed fields, selected.** Preserve the existing exit at the
   start of `events`, but require evidence that every needed field has been
   read before that boundary. This retains the fast path when safe.
2. **Guard messages only.** Fixes the reported recovered sample but leaves the
   demonstrated scores and metadata loss under another ordering.
3. **Remove the early exit.** Avoids premature termination but requires parsing
   the entire sample for every messages-only read.

## Reader behavior

Keep the change local to `_parse_and_filter` in
`src/inspect_scout/_transcript/json/load_filtered.py`. Track top-level field
presence during the existing incremental parse. When the parser reaches the
start of a top-level `events` array, every preceding top-level value has been
fully consumed; nested keys must not count as top-level fields.

The reader may exit at that boundary only when:

- Events are excluded by the existing `events=None` filter.
- `target`, `scores`, and `metadata` have all appeared before `events`.
- `messages` has appeared before `events` if messages are requested.
- Retained content has no attachment references, using the existing guard.

For `messages=None`, messages need not precede `events`: they cannot contribute
retained content or attachment references. A role filter, including an empty
list or one that matches no messages, still counts as a messages request for
the completion check.

Presence is structural, independent of truthiness or retained item counts.
Empty arrays and objects, an empty target, and fields present with null values
count as encountered; their interpretation continues through the existing
reducers and metadata merge behavior.

If any required field has not appeared, continue the existing parse through
the end of the sample. Do not add a new exit point after `events`. Missing
fields remain valid under the current reader behavior and retain their
existing defaults or values from `TranscriptInfo`. An omitted field therefore
conservatively prevents early exit, since the reader cannot know it is absent
until the sample ends.

Continue using the current filtering, attachment resolution, validation, and
JSON fallback paths. During incremental parsing, excluded events and their
pools are traversed without being materialized by their reducers. Track fields
only at top-level key boundaries and avoid allocations in the common per-token
path.

## Boundaries and tradeoffs

This change addresses premature termination, not arbitrary field-order
dependencies elsewhere in the parser. In particular, it does not redesign
attachment lookup when attachments precede their references.

It adds no public API or schema changes. Metadata filtering and spooling from
defect 1, scanner streaming eligibility, event-pool expansion, and scanner
workarounds are separate work.

Normal samples with all required fields before `events` retain the existing
fast path. Samples with later or omitted fields require more parsing time,
including ordinary unscored samples that omit `scores`. This is the cost of
preserving fields whose absence cannot yet be established. Memory use still
depends on the content retained by the existing reader.

## Validation

Extend `tests/scanner/test_load_filtered.py` through
`load_filtered_transcript`, using table-driven cases and real JSON streams:

- The recovered ordering and cases placing each protected field after
  `events`; assert message contents and all expected metadata values.
- Empty fields, empty messages, filters matching no messages, and
  `messages=None`; distinguish field presence from nonempty output.
- Omitted fields; preserve defaults and any later fields without an error.
- Nested keys with protected names; they must not permit premature exit.
- Messages after `events` with an attachment reference and its subsequent
  attachment; verify the resolved message content.
- The normal ordering; retain the early-exit behavior covered by the existing
  callback tests, including the existing attachment guard coverage.

Demonstrate that new regression cases fail on the base reader before applying
the fix. Run the implicated reader tests during development. Before preparing
the PR, run repository lint, formatting, type checking, the suppression gate,
and the full default test suite. Re-read the available affected archive and
verify 31,596 returned messages and zero retained events.

The investigation baseline is 31 passing reader tests and one skipped S3 test.
The PR must include a self-contained minimal reproduction and an accurate
agent-review disclosure. PR creation remains pending user readiness.
