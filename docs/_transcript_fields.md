Here are the available `Transcript` fields:

| Field | Type | Description |
|------------------------|------------------|------------------------|
| `transcript_id` | str | Globally unique identifier for a transcript (maps to `EvalSample.uuid` in Inspect logs). |
| `source_type` | str | Type of transcript source (e.g. "eval_log", "weave", etc.). |
| `source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in Inspect logs) |
| `source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `metadata` | dict\[str, JsonValue\] | Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.). |
| `messages` | [list\[ChatMessage\]](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#messages) | Message history. |
| `events` | [list\[Event\]](https://inspect.aisi.org.uk/reference/inspect_ai.event.html) | Event history (e.g. model events, tool events, etc.) |

: {tbl-colwidths=\[20,30,50\]}