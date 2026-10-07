# Content Trust

## Overview

Scout shows model output: transcript messages and events, scanner explanations, values and metadata. A hostile model can put markdown, links, media or ANSI escapes into that output. When the content isn't trusted, the viewer should show it as plain text, so it can't load anything, link anywhere or disguise itself.

Inspect added this in inspect_ai#5566 and ts-mono#713. That work provides two settings:

- **A per-log setting:** `Task(viewer=ViewerConfig(trust_content=False))`, recorded in the log header as `eval.viewer.trust_content`.
- **A viewer-wide cap:** `inspect view --no-trust-content` / `INSPECT_VIEW_TRUST_CONTENT`.

The frontend machinery is shared through the monorepo:

- `ContentTrustProvider` and `ContentTrustCeilingProvider` in `packages/react`.
- The gated renderers in `packages/react` and `packages/inspect-components`.
- The `require-media-permission` lint rule.

Inspect's design notes are in ts-mono `apps/inspect/design/content-rendering.md`.

This document covers how Scout adopts it. Scout has a project (`scout.yaml`) where Inspect has none. Its content also arrives through transcripts and scan results rather than directly from a log, so the per-log setting has to be carried along to reach the viewer.

## Rules

1. **Lowest trust wins.** Content renders richly only if every applicable setting allows it. No setting can raise trust that another setting has lowered.
2. **Unset means trusted.** A missing or `null` setting, and data written before this feature existed, render as they do today. Only an explicit `false` lowers trust.
3. **Unrecognized means untrusted.** In a log, a setting that is neither a boolean nor `null` counts as `false`, matching inspect_ai's `ViewerConfig` validator and ts-mono's `trustContentSetting()`. In `scout.yaml` such a value fails schema validation, so the viewer doesn't start.
4. **Loading means untrusted.** If the trust of a piece of content isn't known yet, it renders as plain text.

## Settings

### Viewer-wide cap

These settings feed the cap. The effective cap is `false` if any of them is `false`:

| Source | Form |
|---|---|
| Command line | `scout view --trust-content/--no-trust-content` |
| Environment | `SCOUT_VIEW_TRUST_CONTENT` (the envvar for the same click option) |
| Project file | top-level `trust_content: false` in `scout.yaml` |
| Local project file | top-level `trust_content: false` in `scout.local.yaml` |

- Scout doesn't read `INSPECT_VIEW_TRUST_CONTENT`; Inspect's viewer settings don't apply to Scout.
- `--trust-content`, like leaving the option unset, defers to the other sources. It never raises trust.
- `trust_content` is a field on `ProjectConfig` only, not `ScanJobConfig`. It configures the viewer, not scans: `scout scan` and scan jobs don't accept it, and `merge_project_into_scanjob` ignores it.
- **`scout.local.yaml` merge:** for simple fields `merge_configs` currently lets the local file win. `trust_content` is an exception: the merged value is the stricter of the two, so a local file can lower trust but never raise it.
- **Serving the cap:** the server computes the effective cap and returns it as `AppConfig.trust_content` from `GET /api/v2/app-config`. The project value is re-read on every request, as the rest of the project config is, so a change takes effect without restarting the viewer.

### Per-transcript trust

- **Field:** `TranscriptInfo` gains `trust_content: bool | None = None`. It's a first-class field, not metadata, so it doesn't depend on any source's metadata conventions and it's reserved in the database schema.
- **Eval logs:** the eval-log importer reads `eval.viewer.trust_content` as an `EvalColumn` with a string path. Inspect writes this field only from 0.3.275 on, and older versions drop it when parsing. So Scout must require `inspect-ai>=0.3.275`, or untrusted logs would import as trusted. The current minimum, 0.3.277, already satisfies this; don't lower it.
- **Other importers** (Claude Code, LangSmith, etc.) leave it `None`. Users who don't trust those sources use the viewer-wide cap.

### Scan results

- **Column:** a scan records each result's transcript trust as a `transcript_trust_content` column, next to the other `transcript_*` columns in `_recorder/buffer.py`. A scanner's output is model output derived from the transcript, so it can't be more trusted than its input.
- **Why record it:** the scanner result page and the scan results list read from the results data, not the transcript source, so trust has to be stored there.

## Data paths

`trust_content` has to survive every path from an eval log to the screen. Each of the following is a place a dropped value would fail open:

| Path | Requirement |
|---|---|
| `.eval` directory as transcript source | `TranscriptColumns` entry, read in `EvalLogTranscriptsView.select()`. Bump `_CACHE_VERSION`, because a cached index without the column would read as trusted. |
| Full transcript reads | Every hand copy of `TranscriptInfo` fields (`load_filtered.py`, `transcript_no_content`, `filter_transcript`, etc.). `tests/transcript/test_read_preserves_info.py` enumerates `TranscriptInfo.model_fields` and fails on a missed copy site. |
| Parquet transcript database | `SchemaField` in `TRANSCRIPT_SCHEMA_FIELDS`, written by `_transcript_to_row`, read by `ParquetTranscriptsDB.select`. Databases built before the field existed read it as NULL (trusted) until they're re-imported. |
| Scan results | `transcript_trust_content` written by the recorder. Results written earlier have no column and read as trusted. |
| inspect_ai in-eval scanning | **Follow-up.** `transcript_info_from_eval_sample` doesn't receive the eval's `ViewerConfig`. See Follow-ups. |

## Frontend

### Providers

`ContentPolicyContext` defaults to untrusted, and the ceiling defaults to rich. Scout's root currently wraps the router in `<ContentTrustProvider value="trusted">`. With this change:

- **The ceiling.** A `ContentTrustCeilingProvider` above the router takes `trustContentSetting(appConfig.trust_content)`.
  - The router subtree is keyed on that value, so a change remounts it. Scout already rebuilds its router when the app config changes, but the explicit key keeps the guarantee from depending on that.
  - No renderer caches output across trust levels while policies are all-or-nothing; see ts-mono `content-rendering.md` and the `MarkdownDiv` cache.
- **The app default** stays `trusted`, under the ceiling. It covers surfaces that aren't model output from a transcript, such as scan specs, project settings and scan info.
- **Transcript surfaces** get a nearer `ContentTrustProvider` from the transcript's own trust:
  - The transcript page, from `TranscriptInfo.trust_content`. Untrusted until the info loads.
  - The scanner result page, from the result's `transcript_trust_content`.
  - Each row of the scan results list (`ScannerResultsRow`), from its result's `transcript_trust_content`. Rows from different transcripts can differ.
- Reference popovers (`MarkdownDivWithReferences` citations) render in portals, so they inherit the trust of the row or page they're opened from.

A nearer `ContentTrustProvider` replaces the app default, and the ceiling still caps the result. A trusted transcript in an untrusted viewer stays plain.

### Settings page

- **Toggle:** the Project settings page gains an editable trust toggle bound to `scout.yaml`'s `trust_content`.
- **Turning trust off** saves `trust_content: false`. It needs no confirmation.
- **Turning trust on** removes the key instead of writing `true`, and requires a confirmation dialog first: "Model output will render as markdown, with media and links. Only enable this for content you trust." Because `scout.yaml` is usually checked in, the dialog also notes that the change applies to everyone using the project.
- **Overridden setting:** if `AppConfig.trust_content` is `false` but `scout.yaml` doesn't set `false`, then the command line, the environment or `scout.local.yaml` is forcing plain text. The page says so, so nobody confirms a change that has no effect.
- **Saving:** the settings save uses top-level patch semantics (#687), so a save from a section that doesn't include `trust_content` leaves it alone.

## Testing

- **Python:**
  - The CLI and environment combinations, and their effect on `/app-config`.
  - The project / local / CLI combination rules.
  - Non-boolean values are untrusted.
  - The eval-log importer reads `eval.viewer.trust_content` from a real `.eval` written with `ViewerConfig(trust_content=False)`.
  - The field round-trips every read path (via `test_read_preserves_info.py`) and the parquet database.
  - The recorder writes `transcript_trust_content`.
- **Frontend:**
  - Ceiling from app config.
  - Per-transcript and per-row providers, including mixed trust in the results list.
  - Loading renders plain.
  - The settings toggle: confirmation on enable, none on disable, and the override notice.

## Follow-ups

- **In-eval scanning.** inspect_ai's `scan_eval_sample` builds transcripts with Scout's `transcript_info_from_eval_sample`, which takes no viewer configuration. Its scan results record no trust and render as trusted in Scout. Inspect's own scans sidebar is unaffected because it uses the log's trust. Fixing this takes two coordinated changes:
  - Scout accepts the trust value as an optional parameter.
  - inspect_ai passes `eval_spec.viewer.trust_content` and raises its required Scout version.
- **Importer-supplied trust.** Importers (or `db.insert`) could mark non-eval transcripts untrusted. `TranscriptInfo.trust_content` makes this possible, but no importer sets it yet.
- **Granular permissions.** `ContentRenderingPolicy` has per-renderer permissions, but only all-or-nothing policies are configurable. Partial policies would need the policy-keyed caches that ts-mono#713 removed (see `content-rendering.md`).
