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
| `transcript_score` | JsonValue<br/><small>JSON</small> | Value indicating score on task. |
| `transcript_success` | bool |  Boolean reduction of `score` to succeeded/failed. |
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
| `validation_result` | JsonValue<br/><small>JSON</small> | Result returned from comparing `validation_target` to `value`. |
| `scan_error` | str | Error which occurred during scan. |
| `scan_error_traceback` | str | Traceback for error (if any) |
| `scan_error_type` | str | Error type (either "refusal" for refusals or null for other errors). |
| `scan_events` | list\[Event\]<br/><small>JSON</small> | Scan events (e.g. model event, log event, etc.) |
| `scan_total_tokens` | number | Total tokens used by scan (only included when `rows = "transcripts"`). |
| `scan_model_usage` | dict \[str, ModelUsage\]<br/><small>JSON</small> | Token usage by model for scan (only included when `rows = "transcripts"`). |

: {tbl-colwidths=\[20,20,60\]}

::: {.callout-note}
Note that the `transcript_*` fields are available only in the development version of Inspect Scout. Install the development version from GitHub with:

```python
pip install git+https://github.com/meridianlabs-ai/inspect_scout
```
:::