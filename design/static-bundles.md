# Static Scout Bundles

Static Scout bundles are read-only snapshots of a Scout project that can be
served from ordinary static hosting. They package the Scout single-page app plus
enough static data for transcript and scan browsing without running the FastAPI
view server.

The implementation is designed around large scans. Metadata is stored in
queryable Parquet catalogs, transcript content is fetched only when opened, and
scanner result data remains in Parquet so the browser can run filtered queries
directly through DuckDB-WASM.

## Goals

- Deploy Scout results on simple static hosts such as S3, GitHub Pages, nginx,
  or a local `python -m http.server`.
- Preserve the core read workflows: transcript lists, transcript details, scan
  lists, scan result lists, dataframe views, and result detail views.
- Avoid eagerly loading huge transcript bodies or materializing per-row scan
  detail JSON.
- Keep the static bundle independent of a Python process after it is built.
- Make unavailable features explicit in the UI instead of leaving broken
  controls visible.

Static bundles are snapshots. They do not update when transcripts, scans, or
project configuration change.

## Command

Build a bundle with:

```bash
scout view bundle [PROJECT_DIR] -o OUTPUT_DIR [--transcripts PATH] [--scans PATH] [--force]
```

The command lives in `src/inspect_scout/_cli/bundle.py` and is registered as a
subcommand of `scout view`.

Important options:

- `PROJECT_DIR`: optional project directory. Defaults to the current directory.
- `--transcripts`: override the project transcripts location.
- `--scans`: override the project scans location.
- `-o, --output`: output directory. Required.
- `--force`: replace the output directory if it already exists.
- `--max-details`: deprecated and ignored. Scanner details are queried from
  Parquet on demand in static bundle v2.

The output directory can be served directly:

```bash
cd OUTPUT_DIR
python -m http.server 8080
```

Then open `http://127.0.0.1:8080/`.

## Host Requirements

Static bundle v2 requires a host that supports HTTP range requests.

DuckDB-WASM reads Parquet files through HTTP. Range support lets it fetch only
the file sections required for a query instead of downloading an entire large
scanner file or catalog up front. Most production static hosts support this, but
it is worth validating for custom infrastructure.

The bundle also includes DuckDB-WASM's Parquet extension under
`duckdb-extensions/` so the browser does not need to fetch extensions from
`extensions.duckdb.org`.

## Output Layout

Current bundle layout:

```text
my-scout-bundle/
|-- index.html
|-- assets/
|   |-- index-<hash>.js
|   |-- index-<hash>.css
|   |-- duckdb-*.wasm
|   `-- duckdb-browser-*.worker-*.js
|-- duckdb-extensions/
|   `-- v1.5.1/
|       |-- wasm_eh/parquet.duckdb_extension.wasm
|       `-- wasm_mvp/parquet.duckdb_extension.wasm
|-- api/
|   |-- config.json
|   |-- scanners.json
|   |-- project-config.json
|   |-- topics.json
|   |-- transcripts/
|   |   |-- catalog.parquet
|   |   `-- content/
|   |       `-- <bundle-id>.json.zst
|   `-- scans/
|       |-- catalog.parquet
|       `-- data/
|           `-- <bundle-id>/
|               |-- status.json
|               `-- scanners/
|                   `-- <scanner>.parquet
`-- scout-bundle.json
```

There is intentionally no `api/validations/` directory. Static mode hides
validation management and editing rather than bundling validation set files.
Validation results already present inside scan result Parquet files still render
as scan result data.

There are also no per-row detail JSON files and no scan archive ZIP files.
Result details are point queries against scanner Parquet files.

## Manifest

`scout-bundle.json` describes the snapshot:

```json
{
  "version": 2,
  "created_at": "2026-06-01T14:35:27.795394+00:00",
  "transcripts_dir": "./logs",
  "scans_dir": "./scans",
  "catalogs": {
    "transcripts": "api/transcripts/catalog.parquet",
    "scans": "api/scans/catalog.parquet"
  },
  "host_requirements": {
    "http_range_requests": true
  },
  "counts": {
    "transcripts": 209,
    "scans": 6
  }
}
```

The manifest is currently informational. The application switches into static
mode from the injected `scout_context` script in `index.html`, not by fetching
the manifest during boot.

## Build Process

The Python bundler is implemented in `src/inspect_scout/_view/_bundle.py`.

### 1. Copy the Frontend

The bundler copies the committed Scout distribution from
`src/inspect_scout/_view/dist` into the output directory.

It then injects this script before the app module runs:

```html
<script id="scout_context" type="application/json">
{"bundle": true, "bundleBaseUrl": "./api", "transcriptsDir": "...", "scansDir": "..."}
</script>
<script>window.__SCOUT_STATIC_BUNDLE__=true;</script>
```

The early `window.__SCOUT_STATIC_BUNDLE__` assignment matters because some
frontend modules compute static-mode UI at module initialization time.

### 2. Write Small Static Endpoints

The bundler writes JSON files that mirror simple server endpoints:

- `api/config.json`
- `api/scanners.json`
- `api/project-config.json`
- `api/topics.json`

Topic versions are frozen. Static bundles do not use live invalidation or SSE.

### 3. Bundle Transcripts

Transcript bundling opens the configured transcript store through
`transcripts_view()` and selects transcript metadata with the project's configured
filters applied.

For each transcript:

- A metadata row is written to `api/transcripts/catalog.parquet`.
- Complex fields are normalized to compact JSON strings for stable querying.
- The original metadata object is stored as `row_json` so the frontend can
  reconstruct the `TranscriptInfo` response shape.
- Full messages, events, timelines, and attachment data are written separately
  to `api/transcripts/content/<bundle-id>.json.zst`.

Large transcript content is not stored in the catalog. The browser fetches the
zstd content payload only when a user opens a transcript.

### 4. Bundle Scans

Scan bundling reads scan rows through `scan_jobs_view()` and writes
`api/scans/catalog.parquet`.

For each scan:

- The scan location is converted to a stable bundle id.
- `status.json` is written under `api/scans/data/<bundle-id>/`.
- Embedded transcript data in the status spec is cleared so the status snapshot
  stays small.
- Each scanner's Parquet file is copied to
  `api/scans/data/<bundle-id>/scanners/<scanner>.parquet`.
- The scan catalog stores `status_path` and `scanner_paths_json` so the frontend
  can resolve static files without guessing paths.

The scanner Parquet files are copied, not converted to Arrow or expanded into
detail JSON. This is the main scaling property for large scans.

## Runtime Architecture

The static frontend API lives in:

- `apps/scout/src/api/static-http/api-scout-static.ts`
- `packages/query`
- `packages/query-duckdb`

Scout owns the app-specific static API surface: endpoint names, bundle-relative
paths, transcript content decompression, scan status parsing, and scanner detail
expansion. The reusable query and DuckDB pieces live in packages so other apps,
including Inspect, can adopt the same condition DSL and browser-backed storage
approach without depending on Scout internals.

### Boot Detection

`apps/scout/src/main.tsx` selects the API implementation in this order:

1. VS Code webview API, when available.
2. Static bundle API, when a valid `scout_context` script or static test URL
   parameter is present.
3. Live FastAPI server API.

Static API instances set:

```ts
readOnly: true
capability: "workbench"
```

Components use `useStaticBundle()` or the early
`window.__SCOUT_STATIC_BUNDLE__` flag to hide server-only UI.

### DuckDB-WASM Queries

The static API creates a single DuckDB-WASM instance and registers static files
with DuckDB's HTTP file protocol.

DuckDB is treated as a storage-layer implementation detail. The Scout app passes
Vite-resolved DuckDB WASM/worker asset URLs and the local extension repository
URL into `@tsmono/query-duckdb`; consumers interact with the existing
`Condition`, `OrderByModel`, and pagination model rather than DuckDB APIs.

Catalog listings use SQL against Parquet:

- `getTranscripts()` queries `api/transcripts/catalog.parquet`.
- `getScans()` queries `api/scans/catalog.parquet`.
- column distinct values query the same catalogs.
- filters, sorting, and cursor pagination are translated from Scout's
  structured `Condition` and `OrderByModel` objects into DuckDB SQL.

This keeps listing/filtering work close to the data and avoids loading every
catalog row into JavaScript before filtering.

### Opening a Transcript

When a transcript is opened, the static API:

1. queries the transcript catalog by `transcript_id`,
2. parses `row_json` back into `TranscriptInfo`,
3. fetches `content_path`,
4. decompresses the zstd JSON payload,
5. expands compact event data and resolves attachments.

Only the opened transcript's content payload is fetched.

### Opening a Scan

When a scan is opened, the static API:

1. resolves the scan row from `api/scans/catalog.parquet`,
2. fetches that scan's `status.json`,
3. registers scanner Parquet files on demand,
4. queries scanner rows through DuckDB-WASM.

The scan result list and dataframe views read from scanner Parquet. Result detail
views are point queries by `uuid` against the same Parquet file, then the static
API parses `input`, `input_data`, and `scan_events` into the shape expected by
the existing UI.

## Available and Unavailable Features

Available in static mode:

- transcript listing, filtering, sorting, pagination, and column values,
- transcript detail views,
- scan listing, filtering, sorting, pagination, and column values,
- scan status views,
- scanner result lists,
- scanner dataframe views,
- scan result detail views,
- settings that are purely local UI state.

Unavailable in static mode:

- starting or resuming scans,
- active scan updates,
- live invalidation/SSE updates,
- project configuration mutation,
- search execution,
- code generation,
- validation set management and editing,
- validation set bundling,
- scan archive download.

Unsupported API methods reject with `StaticBundleError`, and the UI hides the
main controls that would call them.

## Why This Scales Better

The first static bundle implementation leaned toward prebaked JSON and Arrow
files. That worked for small projects but scaled poorly because it required
materializing large indexes, per-row details, and scan data in formats that were
awkward to query incrementally.

Static bundle v2 changes the scaling profile:

- metadata catalogs are Parquet and queryable in place,
- transcript bodies are compressed and fetched only on open,
- scanner data stays as Parquet,
- result details are point queries instead of prebaked JSON files,
- validation files are omitted because validation management is not part of
  static mode,
- DuckDB-WASM performs filtering, sorting, distinct values, and pagination in
  the browser.

This does not make bundle size disappear. A bundle still contains the transcript
content and copied scanner Parquet files needed for the snapshot. The important
difference is that the browser does not need to load all of that data to render
the first screen or answer a small query.

## Tradeoffs

### Pros

- No backend is required after bundling.
- Static hosting and sharing are simple.
- Large scanner Parquet files remain queryable without JSON expansion.
- Transcript content is lazy-loaded.
- The same React UI is reused with a different `ScoutApiV2` implementation.
- Local DuckDB extensions avoid runtime dependency on external extension hosts.

### Cons

- The first query pays DuckDB-WASM initialization cost.
- The bundle includes large WASM assets and copied data files.
- The host must support range requests for good performance.
- Some static hosts may require MIME or cache configuration for `.wasm` files.
- The snapshot can go stale.
- Static mode has no backend-only features.

## Verification Checklist

Build a bundle:

```bash
scout view bundle -o /tmp/scout-static --force
```

Inspect the manifest:

```bash
jq . /tmp/scout-static/scout-bundle.json
```

Confirm the expected data layout:

```bash
find /tmp/scout-static/api -maxdepth 4 -type f | sort | head -100
```

Serve it:

```bash
python -m http.server 8080 --directory /tmp/scout-static
```

Smoke test in a browser:

- open `http://127.0.0.1:8080/`,
- verify the nav shows Transcripts, Scans, and Settings,
- verify the Validation, Project, and Run Scan activity tabs are hidden,
- open the transcript list and a transcript detail,
- open the scan list, a scan, and a scan result detail,
- verify no `/api/v2/*` requests are made,
- verify no `api/validations/*` requests are made,
- verify DuckDB extension requests resolve under local `duckdb-extensions/`.

Useful curl checks:

```bash
curl -I http://127.0.0.1:8080/index.html
curl -I http://127.0.0.1:8080/api/transcripts/catalog.parquet
curl -I http://127.0.0.1:8080/api/scans/catalog.parquet
curl -I http://127.0.0.1:8080/duckdb-extensions/v1.5.1/wasm_eh/parquet.duckdb_extension.wasm
curl -I http://127.0.0.1:8080/api/validations/sets.json
```

The validation URL should return `404` for current static bundles.

## Code Map

- `src/inspect_scout/_cli/bundle.py`: CLI command and option parsing.
- `src/inspect_scout/_cli/main.py`: registers `bundle` under `scout view`.
- `src/inspect_scout/_view/_bundle.py`: Python materialization logic.
- `apps/scout/src/main.tsx`: runtime API selection and static context parsing.
- `apps/scout/src/api/api.ts`: `ScoutApiV2` interface and read-only flag.
- `apps/scout/src/api/useStaticBundle.ts`: React hook for static-mode UI gates.
- `apps/scout/src/api/static-http/api-scout-static.ts`: static API
  implementation.
- `packages/query`: shared condition builder, condition types, order/pagination
  types, and in-memory condition evaluation helpers.
- `packages/query-duckdb`: condition-to-SQL translation, catalog listing and
  distinct-value helpers, DuckDB-WASM setup, HTTP file registration, and local
  extension repository configuration.
- `apps/scout/src/query`: Scout compatibility re-exports plus
  transcript-specific column definitions.
- `apps/scout/src/router/activities.tsx`: hides static-unavailable activity
  tabs during module initialization.
- `apps/scout/src/AppRouter.tsx`: redirects direct static `/validation` routes.

## Future Work

- Add a first-class local preview command, for example `scout view bundle serve`
  or `scout view --bundle`.
- Add host diagnostics for range request support and WASM MIME behavior.
- Add manifest compatibility checks if future bundle versions change layout.
- Add user-facing Quarto docs once the command and layout settle.
- Consider optional bundle pruning controls for deployments that only need scans
  or only need transcripts.
