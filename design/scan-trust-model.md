# Scan Trust Model

## Overview

Scan results are data, and the person reading them is often not the person who wrote them: scan directories are shared for analysis, copied from a colleague's bucket, or attached to a report. Whoever writes a scan controls every field of its `_scan.json`, including source file paths, registry parameters and the model configuration. They do not control the reader's installed packages, project directory or command line.

Scout splits operations on a scan into two kinds:

- **Run operations** exist to run the scan's scanners again. They import files the scan names and build objects and models from its values. `scout scan resume` / `scan_resume()` is the only one.
- **Read operations** list, view, export or analyze a scan. They never import a file because the scan names it, never construct a scanner, validation predicate or model from the scan's values, and never unpickle scan data.

This follows Inspect's trust model for eval logs (`design/malicious-log-code-execution.md` in inspect_ai, UKGovernmentBEIS/inspect_ai#5728), where `eval-retry` is the run operation and recompute, recovery and viewing are read operations.

## What a scan names

`ScanSpec` (`_scan.json`) fields that would run code or contact a server if acted on:

| Field | Acted on by |
|---|---|
| `scanners.<name>.file` | resume: `load_module()` in `load_scanner_file()` |
| `scanners.<name>.name`, `.params` | resume: `scanner_create()`, which looks the name up in the registry and builds params with `registry_kwargs()`. A params dict shaped like a registry object or a model config becomes that object or a `get_model()` call. |
| `validation.<scanner>.predicate` (`RegisteredPredicateSpec`: `file`, `name`, `args`) | resume: `validation_sets_from_specs()` imports `file`, then `create_registered_predicate()` builds `args` with `registry_kwargs()` |
| `model`, `model_roles` | resume: `model_config_to_model()` and `model_roles_config_to_model_roles()`, with the recorded base URL, config and model args |
| `transcripts` (`location`, `transcript_ids`) | resume: transcripts are read from these locations |
| `scan_file`, `scan_args` | nothing; informational |

Parsing a spec does none of this. `ValidationSetSpec` turns a legacy pickled predicate into `UnavailablePredicateSpec(reason="legacy")` without decoding it (#479), and the other models are plain pydantic data.

## Operations

| Operation | Kind | Notes |
|---|---|---|
| `scout scan resume`, `scan_resume()`, `scan_resume_async()` | run | Imports the scanner and predicate files the scan names, builds its scanners, predicates and model. The model uses the recorded base URL, so its requests carry the user's provider credentials there. `predicate_overrides` replaces a recorded predicate with the caller's own. |
| `scout scan status`, `scan_status()` | read | `FileRecorder.status()`: parses `_scan.json`, `_summary.json`, `_errors.jsonl` and the local buffer. |
| `scout scan list`, `scan_list()` | read | `FileRecorder.status()` for each scan. |
| `scout scan complete`, `scan_complete()` | read | Status, then `FileRecorder.sync(complete=True)`, which compacts buffered results into parquet. |
| `scan_results_df()`, `scan_results_arrow()`, `scan_results_batches()`, `scan_results_db()` | read | Parquet and DuckDB reads. DuckDB connections are locked to the scan's files (`restrict_external_access()`), and identifiers are quoted. |
| `scout view` scans endpoints (`/scans/...`, including zip download and delete) | read | The functions above, plus the SQLite scan index (`_scanjobs`), which stores rows derived from status. |
| `scout view` transcripts endpoints, `transcripts_from()` | read | Eval logs through inspect_ai's readers; parquet databases through DuckDB with external access restricted. |
| `scout view` validation endpoints | read | Read and write CSV, JSON, JSONL and YAML (`yaml.safe_load`) files inside the project directory. |

Two inputs are trusted in every operation, as Inspect trusts its working directory:

- **Installed packages.** A registry name with a package prefix loads that package's entry point (`registry_lookup()`); `GET /scanners` loads all of them. Only code the user installed runs.
- **The project directory.** `scout.yaml`, `scout.local.yaml` and `.env` are the user's configuration, and a scanner `file` in a project or scan job config is loaded like a file the user passed on the command line. Opening `scout view` on a project directory someone else wrote trusts that project.

The viewer's `POST /startscan` and `POST /search` start scans from the request body, not from scan data. They are run operations on behalf of the viewer's user; the viewer's network policy decides who that is.

`cloudpickle` is used only to pass scanner callables from the parent process to its own worker processes (`_concurrency/_mp_common.py`). Nothing persisted or served is unpickled.

## Decisions

- **Resume is documented, not restricted.** `scout scan resume --help`, `scan_resume()`'s docstring and the user docs say it runs code the scan names and should only be used on scans you trust. As with `eval-retry`, there is no way to make resume safe on an untrusted scan: it exists to run the scan's scanners.
- **Resume does not limit params-built registry objects.** inspect_ai limits metric options from an untrusted log to metrics and reducers because those operations otherwise import nothing. Resume already imports the scan's source files and builds the scan's model with its recorded base URL, so restricting scanner and predicate params would not change what a hostile scan can do. Run operations in inspect_ai (`eval-retry`, `inspect score` with the log's scorers) are likewise unrestricted.

## Testing

`tests/test_untrusted_scans.py` writes a real incomplete scan, then rewrites its `_scan.json` so that the scanner, scan job and predicate files are marker modules that record their import, and the scanner params, predicate args, model and model roles all point at a distinctive base URL. A spy on `ModelAPI.__init__` records providers built with that URL. Every read operation in the table runs against it and must import nothing and build nothing. A final test resumes the same scan and asserts that resume imports the scanner and predicate files (not the scan job file) and builds the model, which also proves the fixture's references are live.

`tests/validation/test_predicate_specs.py` covers the predicate-specific cases: legacy pickled predicates are never decoded by status or the scan list endpoint, and status never loads a registered predicate's source file.

## Follow-ups

- **`POST /startscan` accepts any `ScanJobConfig`.** The viewer only sends `llm_scanner` configs, but the endpoint also accepts scanner `file` paths, model base URLs and model args. Narrowing it to what the viewer sends would limit what a forged or misdirected request can run.
