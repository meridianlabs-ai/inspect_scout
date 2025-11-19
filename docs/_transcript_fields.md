
The `Transcript` type is defined somewhat generally to accommodate other non-Inspect transcript sources in the future. Here are the available `Transcript` fields and how these map back onto Inspect logs:

| Field | Type | Description |
|------------------------|------------------------|------------------------|
| `transcript_id` | str | Globally unique identifier for a transcript (maps to `EvalSample.uuid` in the Inspect log). |
| `source_type` | str | Type of transcript source (e.g. "eval_log"). |
| `source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in the Inspect log) |
| `source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `metadata` | dict\[str, JsonValue\] | Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.). See `LogMetadata` for details on metadata available for Inspect logs. |
| `messages` | list\[ChatMessage\] | Message history from `EvalSample` |
| `events` | list\[Event\] | Event history from `EvalSample` |

: {tbl-colwidths=\[20,30,50\]}

The `metadata` field includes fields read from eval sample metadata. For example:

{{< include _transcript_metadata.md >}}
