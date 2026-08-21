### Data Frames {#data-frames}

```{=html}
<style type="text/css">
#data-frames td:nth-child(2) {
  font-size: 0.9em;
  line-height: 1.2;
}
#data-frames small {
  font-size: x-small;
}
</style>
```

The data frames available for each scanner contain information about the source evaluation and transcript, the results found for each transcript, as well as model calls, errors and other events which may have occurred during the scan.

#### Row Granularity

Note that by default the results data frame will include an individual row for each result returned by a scanner. This means that if a scanner returned [multiple results](scanners.qmd#multiple-results) there would be multiple rows all sharing the same `transcript_id`. You can customize this behavior via the `rows` option of the scan results functions:

|  |  |
|------------------------------------|------------------------------------|
| `rows = "results"` | Default. Yield a row for each scanner result (potentially multiple rows per transcript) |
| `rows = "transcripts"` | Yield a row for each transcript (in which case multiple results will be packed into the `value` field as a JSON list of `Result`) and the `value_type` will be "resultset". |

: {tbl-colwidths=\[40,60\]}

#### Available Fields

The data frame includes the following fields (note that some fields included embedded JSON data, these are all noted below):

| Field | Type | Description |
|-------------------|-------------------|----------------------------------|
| `transcript_id` | str | Globally unique identifier for a transcript (e.g. sample `uuid` in the Inspect log). |
| `transcript_source_type` | str | Type of transcript source (e.g. "eval_log"). |
| `transcript_source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in the Inspect log and analysis data frames). |
| `transcript_source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `transcript_date` | str | ISO 8601 datetime when the transcript was created. |
| `transcript_task_set` | str | Set from which transcript task was drawn (e.g. Inspect task name or benchmark name) |
| `transcript_task_id` | str | Identifier for task (e.g. dataset sample id). |
| `transcript_task_repeat` | int | Repeat for a given task id within a task set (e.g. epoch). |
| `transcript_agent` | str | Agent used to to execute task. |
| `transcript_agent_args` | dict </br><small>JSON</small> | Arguments passed to create agent. |
| `transcript_model` | str | Main model used by agent. |
| `transcript_model_options` | JsonValue<br/><small>JSON</small> | Generation options for main model. |
| `transcript_score` | JsonValue<br/><small>JSON</small> | Value indicating score on task. |
| `transcript_success` | bool |  Boolean reduction of `score` to succeeded/failed. |
| `transcript_message_count` | number | Total messages in conversation | 
| `transcript_total_time` | number | Time required to execute task (seconds) |
| `transcript_total_tokens` | number | Tokens spent in execution of task. |
| `transcript_error` | str | Error message that terminated the task. |
| `transcript_limit` | str | Limit that caused the task to exit (e.g. "tokens", "messages, etc.) |
| `transcript_metadata` | dict <br/><small>JSON</small> | Source specific metadata. |
| `scan_id` | str | Globally unique identifier for scan. |
| `scan_tags` | list\[str\]</br><small>JSON</small> | Tags associated with the scan. |
| `scan_metadata` | dict<br/><small>JSON</small> | Additional scan metadata. |
| `scan_git_origin` | str | Git origin for repo where scan was run from. |
| `scan_git_version` | str | Git version (based on tags) for repo where scan was run from. |
| `scan_git_commit` | str | Git commit for repo where scan was run from. |
| `scanner_key` | str | Unique key for scan within scan job (defaults to `scanner_name`). |
| `scanner_name` | str | Scanner name. |
| `scanner_version` | int | Scanner version. |
| `scanner_package_version` | int | Scanner package version. |
| `scanner_file` | str | Source file for scanner. |
| `scanner_params` | dict<br/><small>JSON</small> | Params used to create scanner. |
| `input_type` | transcript \| message \| messages \| event \| events | Input type received by scanner. |
| `input_ids` | list\[str\]<br/><small>JSON</small> | Unique ids of scanner input. |
| `input` | ScannerInput<br/><small>JSON</small> | Scanner input value. |
| `input_storage` | inline \| reference | Whether `input` is a self-contained copy or a reference to the source transcript (see [Referenced Input](#referenced-input)). |
| `uuid` | str | Globally unique id for scan result. |
| `label` | str | Label for the origin of the result (optional). |
| `value` | JsonValue<br/><small>JSON</small> | Value returned by scanner. |
| `value_type` | string \| boolean \| number \| array \| object \| null | Type of value returned by scanner. |
| `answer` | str | Answer extracted from scanner generation. |
| `explanation` | str | Explanation for scan result. |
| `metadata` | dict<br/><small>JSON</small> | Metadata for scan result. |
| `message_references` | list\[Reference\]<br/><small>JSON</small> | Messages referenced by scanner. |
| `event_references` | list\[Reference\]<br/><small>JSON</small> | Events referenced by scanner. |
| `validation_target` | JsonValue<br/><small>JSON</small> | Target value from validation set. |
| `validation_predicate` | str | Predicate used for comparison (e.g. "eq", "gt", etc.). |
| `validation_result` | JsonValue<br/><small>JSON</small> | Result returned from comparing `validation_target` to `value` using `validation_predicate`. |
| `validation_split` | str | Validation split the case was drawn from (if any). |
| `scan_error` | str | Error which occurred during scan. |
| `scan_error_traceback` | str | Traceback for error (if any) |
| `scan_error_type` | str | Error type (either "refusal" for refusals or null for other errors). |
| `scan_events` | list\[Event\]<br/><small>JSON</small> | Scan events (e.g. model event, log event, etc.) |
| `scan_total_tokens` | number | Total tokens used by scan (only included when `rows = "transcripts"`). |
| `scan_model_usage` | dict \[str, ModelUsage\]<br/><small>JSON</small> | Token usage by model for scan (only included when `rows = "transcripts"`). |

: {tbl-colwidths=\[20,20,60\]}

#### Referenced Input

By default (`record_input="copy"`, the default `scan()` option) each result row is a self-contained copy of the scanner's input. Passing `record_input="reference"` instead records a pointer back to the source transcript, which keeps result files small when scanning large transcripts:

``` python
status = scan(
    transcripts=transcripts_from("./logs"),
    scanners=[ctf_environment(), java_tool_calls()],
    record_input="reference",
)
```

Whether a row is a copy or a reference is visible in the `input_storage` column, and the two other input columns are populated accordingly:

| Column | Inline row (`input_storage = "inline"`) | Reference row (`input_storage = "reference"`) |
|---|---|---|
| `input` | Serialized scanner input | NULL |
| `input_data` | Pools/attachments, or NULL | NULL |
| `input_content` | NULL | Content filters used to produce the input, as one JSON string (e.g. `{"messages": "all", "events": ["model"], "timeline": null}`), or NULL |

A NULL `input_content` on a reference row means the filters weren't available when the row was recorded, and resolving the reference falls back to full content (`messages="all", events="all"`).

Even a `record_input="copy"` scan can produce reference rows: when a transcript's serialized input is too large to store inline, or otherwise can't be read, Scout degrades that row to a reference rather than failing the scan. Filter by `input_storage == "reference"` to find these rows regardless of the scan's `record_input` setting.

Use `resolve_input_reference()` to turn a reference row back into the `Transcript` the scanner saw. It re-reads the source named by `transcript_source_uri`, selects the sample by `transcript_id`, and applies the recorded `input_content` filters. It's an `async` function, and it accepts any mapping of column name to value — for example a row obtained from the `duckdb` connection returned by `scan_results_db()`, or from a record batch returned by `scan_results_arrow()`:

``` python
from inspect_scout import resolve_input_reference

if row.get("input_storage") == "reference":
    transcript = await resolve_input_reference(row)
```

Result files written before these columns existed have no `input_storage` column at all; reading such a file, rows are treated as non-references.
