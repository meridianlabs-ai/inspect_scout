Here are the available `Transcript` fields:

| Field | Type | Description |
|------------------------|------------------|------------------------|
| `transcript_id` | str | Globally unique identifier for a transcript (maps to `EvalSample.uuid` in Inspect logs). |
| `source_type` | str | Type of transcript source (e.g. "eval_log", "weave", etc.). |
| `source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in Inspect logs) |
| `source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `date` | iso | Date/time when the transcript was created. |
| `task_set` | str | Set from which transcript task was drawn (e.g. benchmark name) |
| `task_id` | str | Identifier for task (e.g. dataset sample id). |
| `task_repeat` | int | Repeat for a given task id within a task set (e.g. epoch). |
| `agent` | str | Agent used to to execute task. |
| `agent_args` | dict </br><small>JSON</small> | Arguments passed to create agent. |
| `model` | str | Main model used by agent. |
| `score` | JsonValue<br/><small>JSON</small> | Value indicating score on task. |
| `success` | bool |  Boolean reduction of `score` to succeeded/failed. |
| `total_time` | number | Time required to execute task (seconds) |
| `total_tokens` | number | Tokens spent in execution of task. |
| `error` | str | Error message that terminated the task. |
| `limit` | str | Limit that caused the task to exit (e.g. "tokens", "messages, etc.) |
| `metadata` | dict\[str, JsonValue\] | Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.). |
| `messages` | [list\[ChatMessage\]](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#messages) | Message history. |
| `events` | [list\[Event\]](https://inspect.aisi.org.uk/reference/inspect_ai.event.html) | Event history (e.g. model events, tool events, etc.) |

: {tbl-colwidths=\[20,30,50\]}