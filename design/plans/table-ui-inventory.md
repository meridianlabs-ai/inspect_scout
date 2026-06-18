# Table/Grid UI inventory — inspect_scout vs inspect_ai

## Why this document exists — what's actually wrong with the status quo?

Before any inventory or proposal, the motivating question: *what problem are we trying
to solve?* This document and the discussion it feeds exist to answer that explicitly,
rather than jumping straight to "share more code."

Each item below is a **hypothesis to validate**, not an asserted fact — for several,
the honest answer may be "that's fine, leave it." The first goal of the discussion is
to agree which of these are real pains worth carrying a cost to fix, and which are
acceptable as-is. That alignment then prunes the goals in §2.4: **don't spend cost
solving a non-problem.**

| # | Claimed problem with status quo | Who feels it | Validate / open question |
|---|---|---|---|
| P1 | **Grid machinery built twice** — two generic wrappers (`DataGrid`/TanStack, `SamplesGrid`/ag-grid) + two filter/sort/keyboard/column stacks live side-by-side in one monorepo; features & bugfixes done twice; two grid libs in the bundle | frontend maintainers | How often is grid work actually done? Are the two visibly diverging, or stable enough that duplication is cheap? |
| P2 | **Inconsistent table UX across products** — single- vs multi-select, server faceted filters vs client ag-grid filters, find-band vs column filters | users who use *both* inspect and scout | Is there meaningful user overlap? Do they actually notice/complain? |
| P3 | **inspect's whole-log-in-memory ceiling** — large logs / many samples / cross-log views bounded by client memory; no server query path | inspect users with big evals | Is anyone hitting the ceiling today, or projected to? |
| P4 | **scans backend doesn't scale** — per-request full directory scan + load-all (§1.3.1); latency grows with scan count | scout users with many scans | At what scan-count does it bite? Are we near it? |
| P5 | **Conceptual divergence** — transcript vs log+sample makes shared tooling/abstractions harder and onboarding more confusing | maintainers / new devs | Is the divergence essential to the two jobs, or incidental friction we'd remove if free? |

> **Cross-cutting requirement (R): scale to arbitrarily large data.** P3 and P4 are
> specific symptoms of one broader, long-term requirement we expect to face: handling
> data that is large along **two independent axes** — (1) the *number* of records
> (logs / evals / scans / transcripts) and (2) the *size of an individual record's
> contents* (samples, scanner results, messages/events). They need different
> solutions (server-side query/pagination vs streaming/virtualization/ranged reads),
> and today several surfaces meet **neither**. Treat R as the lens behind the
> scalability goals; current state per surface is mapped in §1.7.

The rest of the document supports this conversation in two parts:
1. **Dimensional inventory** — what exists, how it's built, comparison matrix, and a
   conceptual-model alignment section. (The evidence base for the claims above.)
2. **Discussion guide** — sharing candidates, divergences worth debating, a
   cost/priority assessment, and open roadmap questions framed for the team.

---

# Part 1 — Dimensional inventory

## 1.1 The headline difference

| | **inspect_scout** | **inspect_ai** |
|---|---|---|
| Primary grid lib | TanStack Table v8.21.3 (custom `DataGrid`) for the main views; ag-grid-community v34.3.1 for the in-memory results dataframe | ag-grid-community v34.3.1 everywhere |
| ag-grid edition | Community (minimal modules registered) | Community (`AllCommunityModule`) |
| Compute locus (main views) | **Server-side** filter/sort/paginate via a pluggable query API | **Client-side** filter/sort/paginate in ag-grid |
| Data protocol | **Formalized generic wire contract** (`Condition` / `OrderBy` / `Pagination`), keyset cursor pagination | **Bespoke, file-oriented** endpoints; ETag caching; no generic query protocol |
| Shared frontend code | `ts-mono` is **one shared monorepo mounted into both** repos; both consume the same `@tsmono/inspect-components`, `@tsmono/react`, `@tsmono/inspect-common` | same |

The split is the story: **scout pushes table compute to the server behind a
backend-agnostic query protocol; inspect loads whole logs and does table work in
the browser.** The two apps already share a meaningful chunk of *presentational*
component code (one real shared monorepo, not copies) — and that sharing is
**bidirectional**: scout consumes `inspect-components`, and inspect consumes
`scout-components` to render scout-scanner-as-scorer results in its "scans" tab
(§1.4). What is *not* shared is the **interactive list-grid machinery and the
data-fetch/query protocols** — those are built independently in each app.

A second, independent axis on the scout side: even where the query *protocol* is
shared, the **storage engine behind it varies by source and is not uniformly
scalable** — Parquet-backed transcripts query DuckDB-over-Parquet (scalable),
eval-log transcripts materialize into in-memory SQLite, and scans re-scan the
directory and load every status into memory on every request (see §1.3.1).

## 1.2 Comparison matrix — main views

| View | Repo | Library | Filter/sort | Pagination | View abstraction | Backend scalable | Selection | Virtual | Domain coupling |
|------|------|---------|-------------|------------|------------------|------------------|-----------|---------|-----------------|
| Transcripts | scout | TanStack `DataGrid` | **server** | cursor (keyset, infinite) | `TranscriptsView` ABC | **source-dependent**: ✓ DuckDB-over-Parquet (db source) / ✗ in-mem SQLite (eval-log source) | multi | ✓ | moderate (wraps generic `DataGrid`) |
| Scans | scout | TanStack `DataGrid` | **server** | cursor (keyset, infinite) | `ScanJobsView` ABC | **✗** dir-walk + load-all per request | multi | ✓ | moderate (wraps generic `DataGrid`) |
| Scanner results dataframe | scout | ag-grid | client | none | — (in-memory `ColumnTable`) | n/a (client) | single | ✓ | high (Arquero `ColumnTable`) |
| Scanner results list | scout | custom `VirtualList` | client | none | — | n/a (client) | single | ✓ | high (`ScanResultSummary`) |
| Validation cases | scout | hand-rolled CSS grid | client | none | — | n/a (client) | multi | ✗ | very high |
| Log list | inspect | ag-grid | **client** | ag-grid virtual | none (file listing) | partial (lists files; loads on demand) | single | ✓ | high (builds `LogListRow`) |
| Samples (grid/list/panel/tab) | inspect | ag-grid (`SamplesGrid` wrapper) | **client** | ag-grid virtual | none (whole log in memory) | **✗** whole-log-in-memory | single | ✓ | medium (generic wrapper) |
| Scorecard (`ScoreAgGrid`) | inspect | ag-grid | none | none | none | n/a | none | ✗ | high (read-only) |

**View abstraction** = is there a pluggable, backend-agnostic query interface behind
the view (scout's `…View` ABCs)? **Backend scalable** = does server-side
filter/sort/paginate run against a real indexed store, or materialize everything per
request?

Read-only / display-only surfaces (not interactive grids) summarized in §1.5.

## 1.3 inspect_scout — detail

### Transcripts & Scans (the two flagship views)
- **Library:** custom generic `DataGrid<TData, TColumn, TState>` built on TanStack
  Table + `@tanstack/react-virtual`.
  `apps/scout/src/app/components/dataGrid/DataGrid.tsx`.
- **Compute locus:** server-side. The grid sends filter/sort/pagination to the API;
  client only owns UI state (column resize/reorder/visibility, selection).
- **Fetching:** React Query infinite hooks —
  `useServerTranscriptsInfinite`, `useScansInfinite` (`apps/scout/src/app/server/`).
  Cursor-based; transcripts page size 50, scans 20. State held in Zustand
  (`transcriptsTableState`, `scansTableState`).
- **Features:** multi-select (shift/cmd, cmd-click → new tab), drag-to-reorder
  headers, resize, faceted per-column filters (`ColumnFilterControl`), infinite
  scroll (500px threshold), column visibility picker, full keyboard nav,
  fit-content auto-sizing that preserves manual resizes.
- **Reusable infra:** `DataGrid`, `columnTypes.ts` (`ExtendedColumnDef`),
  `columnSizing/` strategies, `columnFilter/` controls. Transcripts and Scans are
  thin domain wrappers over this.

### Scanner results dataframe
- ag-grid-community; `apps/scout/src/app/components/DataframeView.tsx`.
- Pre-loaded Arquero `ColumnTable`, **all compute client-side**. Minimal ag-grid
  module registration (`agGridSetup.ts`) to keep bundle small; row-number column
  hand-implemented to avoid an enterprise feature.

### Scanner results list / Validation cases / Timeline
- Scanner results list: custom `VirtualList` with text search, value filter,
  4 grouping strategies, dynamic CSS-grid column layout. High coupling.
- Validation cases: hand-rolled CSS grid + cards, bulk actions (assign split,
  copy/move, delete), checkbox multi-select. Very high coupling.
- Timeline events: virtualized via shared `TranscriptLayout` from
  `inspect-components`.

### 1.3.1 Backend scalability — the protocol is uniform, the storage is not
A crucial caveat: scout's server-backed views share the same `…View` ABC and the same
wire protocol, but the **storage engine behind a view depends on the source**, and
they scale very differently. Three distinct backends sit behind two view types:

- **Transcripts, parquet-database source → `ParquetTranscriptsDB` (scalable).** A
  DuckDB connection (in-memory *catalog*) querying `read_parquet(...)` over on-disk /
  remote Parquet files plus prebuilt index files; `Condition`/`OrderBy`/`Pagination`
  compile to SQL and push down into Parquet (predicate/projection pushdown, keyset
  seeks). The data is *not* loaded into memory — DuckDB reads only the needed row
  groups/columns. Cost scales with the page/filter, not the corpus. This is the read
  path analyzed in `parquet-point-lookup-analysis.md`.
- **Transcripts, eval-log source → `EvalLogTranscriptsView` (in-memory SQLite).**
  Indexes the eval logs into a pandas DataFrame, then loads it into an **in-memory
  SQLite** database (named in-mem dbs with L1 per-file + L2 sqlite caching); all
  queries run against that. Genuine SQL filter/sort/pagination, but it materializes
  the whole indexed corpus into memory. Better than scans (cached across requests, not
  rebuilt each call) but **not** a persistent/indexed store — memory-bound on the
  indexed set.
- **Scans → `DuckDBScanJobsView` (NOT scalable).** Constructed **fresh on every
  request** (`_api_v2_scans.py` → `scan_jobs_view(dir)`), which calls
  `FileRecorder.list()`: a recursive directory walk (`scan_id=*`) that reads *every*
  scan's `status` (parallel `FileRecorder.status` per dir) into memory, then loads
  them all into an **in-memory** DuckDB table and runs SQL over that snapshot
  (`_scanjobs/duckdb.py`). The SQL filter/sort/keyset-pagination is genuine, but it
  operates on a fully-materialized in-memory copy rebuilt per call. Cost is
  **O(total scans)** directory-walk + N status reads **regardless of page size or
  filter** — no persistence, no index, no incremental refresh. The keyset cursor
  saves the client bytes but saves the server nothing.

Net: the pluggable abstraction makes all three *look* equivalent from the API/UI, but
only the Parquet path is a real query-against-storage engine; the eval-log path is an
in-memory SQLite materialization, and scans is a per-request full scan dressed in SQL.
Any "scout's server-side model scales" claim holds only for the Parquet-backed
transcripts path — not for eval-log transcripts (memory-bound) or scans (full scan per
request) today.

### The server protocol (scout's distinctive asset)
Formalized, backend-agnostic wire contract (`src/inspect_scout/_view/_api_v2_types.py`):

```python
@dataclass
class PaginatedRequest:
    filter: Condition | None = None
    order_by: OrderBy | list[OrderBy] | None = None
    pagination: Pagination | None = None

@dataclass
class Pagination:
    limit: int
    cursor: dict[str, Any] | None
    direction: Literal["forward", "backward"]
```

- **`Condition`** (`_query/condition.py`): recursive Pydantic model — simple
  comparisons (`EQ/NE/LT/LE/GT/GE`, `IN`, `LIKE/ILIKE`, `IS_NULL`, `BETWEEN`) and
  compound `AND/OR/NOT`. Serializes to JSON, compiles to SQL.
- **`OrderBy`**: `{column, direction}`.
- **Keyset (cursor) pagination**, not offset — `_pagination_helpers.py` converts a
  cursor dict into an inequality `Condition` for index seeks; always appends a
  tiebreaker sort key (`transcript_id` / `scan_id`) for stable order; handles
  forward/backward.
- **Unified response:** `{ items, total_count, next_cursor }` for every table
  endpoint.
- **Pluggable backends:** `TranscriptsView` / `ScanJobsView` ABCs
  (`select/count/distinct/connect/disconnect`). Implementations: `ParquetTranscriptsDB`
  (DuckDB-over-Parquet), **`EvalLogTranscriptsView` (in-memory SQLite over indexed
  eval logs** — i.e. scout can already treat inspect eval logs as a transcript
  source), and `DuckDBScanJobsView` (in-memory DuckDB for scans). Same protocol, three
  very different storage profiles (see §1.3.1).
- **Endpoints:** `POST /transcripts/{dir}`, `POST /scans/{dir}`, `…/distinct`
  (faceted filter values), plus single-item + streaming endpoints.

The same `Condition`/`OrderBy`/`Pagination` models are **reused across every table
endpoint** — this is a genuine generic tabular query protocol, not per-endpoint
glue.

## 1.4 inspect_ai — detail

### Log list & Samples
- **Library:** ag-grid-community throughout. `SamplesGrid`
  (`apps/inspect/src/app/shared/samples-grid/SamplesGrid.tsx`) is a generic
  reusable wrapper reused by SampleList, SamplesPanel, SamplesTab. LogListGrid is
  its own grid.
- **Compute locus:** **client-side.** ag-grid does filter/sort; state persisted per
  scope in Zustand. Server is not told about sort/filter.
- **Eval-author customization:** `task_samples_view` descriptor can seed column
  order/visibility/sort/filter, score color scales, compact vs multiline.
- **Features:** single-select, column resize/reorder, find band (Cmd+F),
  follow-output auto-scroll for running evals, shared keyboard nav + grid
  utilities (`gridUtils.ts`, `useApplyColumnVisibility`, `gridComparators`,
  `useSampleGridState`).

### "scans" tab — scout scanner results inside inspect (shared rendering)
When scout scanners run as scorers, the sample/transcript view gains a **"scans"**
tab (`apps/inspect/src/app/samples/transcript/TranscriptPanel.tsx:474`) rendered by
`SampleScansSidebar` (`apps/inspect/src/app/samples/scans/`).
- **Not a list-grid.** It renders **one selected scanner's** result via scout's
  `ScannerResultDetailView` — collapsible sections (Value / Answer / Explanation /
  Validation / Metadata) plus a `SampleScannerPicker` to switch scanners. A detail
  panel, not a multi-row results table.
- **Grid-ish nesting only:** a tabular scanner *value* tabularizes inside the `Value`
  section (`maxTableSize={1000}`), and `Metadata` uses a key/value grid layout.
- **Cross-repo sharing (notable):** `SampleScansSidebar` imports from
  **`@tsmono/scout-components`** (`ScannerResultDetailView`, `inferValueType`,
  `resolveScannerResultView`, `metadataWithoutScannerKeys`). This is the concrete proof
  that sharing is *bidirectional* — inspect consumes scout's scanner-result rendering,
  not just scout consuming `inspect-components`.

### Data loading model (bespoke, file-oriented)
FastAPI "view server" (`_view/fastapi_server.py`); browser never parses logs
directly.
- `GET /log-files` → entire directory listing at once (`LogFilesResponse` with
  `LogHandle[]`); change detection via **weak ETag** `W/"<mtime>-<fileCount>"`,
  incremental vs full. **No pagination.** Sort/filter is client-side.
- `GET /logs/{log}` → full `EvalLog` (or header-only above an MB threshold). Samples
  arrive as one big payload of `EvalSampleSummary`.
- `GET /pending-samples` (running evals) → all summaries at once, ETag-cached.
- `GET /pending-sample-data` → **cursor-by-id incremental** event/attachment/message
  streaming ("give me what's new since id N") — note: a cursor pattern, but for
  *live append*, not table paging.
- No `Condition`/`OrderBy`/`Pagination` equivalent; loading is per-resource and
  domain-specific.

## 1.5 Shared / generic component layer (already common to both)
Sharing runs in **both directions** across the one shared monorepo — same code today:
- **scout ← `inspect-components`:** `MetaDataGrid` (nested key/value CSS grid),
  `ModelTokenTable` (usage HTML table), `RecordTree` (virtuoso tree),
  `ChatViewVirtualList`, `TranscriptVirtualList` / `TranscriptLayout`.
- **inspect ← `scout-components`:** `ScannerResultDetailView` (+ `inferValueType`,
  `resolveScannerResultView`, `metadataWithoutScannerKeys`), used by inspect's "scans"
  tab to render scout-scanner-as-scorer results (§1.4).
- **both ← shared infra:** `@tsmono/react` (`VirtualList`, async-data hooks),
  `@tsmono/inspect-common` (Event/JsonValue types).

So sharing already happens for **transcript/chat/metadata presentation** and (newly)
**scanner-result rendering**, in both directions. It does *not* happen for
**interactive list-grids** or **data-fetch/query protocols** — those are built
independently in each app.

## 1.6 Conceptual model alignment — same idea, modeled differently

This is the crux for a sharing/roadmap conversation: where do the two products name
the "same" thing but model it for different jobs?

| Concept | scout | inspect | Essential vs incidental divergence |
|---|---|---|---|
| The unit being listed | **Transcript** — a normalized, source-agnostic conversation/record (can come from eval logs *or* other sources) | **Eval log** (a file) containing **Samples** | **Essential.** Scout's transcript is a deliberately broader abstraction than an eval sample; it exists to scan heterogeneous sources, not just inspect evals. |
| "List of records" | one flat `TranscriptInfo` / `ScanRow` stream, server-queried | two-level: list of log *files*, then samples *within* a selected log | Partly essential (inspect is file-centric), partly incidental (could be flattened). |
| Filter/sort | server-side `Condition`/`OrderBy`, persisted as query | client-side ag-grid filter model, persisted per scope | **Incidental** — both express the same user intent (filter these columns); different execution locus. |
| Pagination | keyset cursor over a possibly-huge backend | none; whole log in memory + virtual scroll | Essential *today* (different data scale assumptions), but a candidate to converge. |
| Scale assumption | unbounded results across many runs → must page on server | one eval log fits in memory → load it all | Drives almost every other difference. |

**Transcript is a superset of an eval sample — in provenance, not schema.** Scout's
`Transcript` generalizes inspect's eval sample: an eval-log sample is one
`source_type` among others, with epoch / sample-id / benchmark mapped onto
source-agnostic fields (`task_repeat` / `task_id` / `task_set`). So a transcript is a
**superset in provenance** (it can represent more sources than just eval logs) but a
**normalization in schema** (`TranscriptInfo` is a common-denominator listing model,
not a strict superset of every `EvalSample` field — the richer per-sample data lives
behind separate read paths). This is exactly why the divergence is *essential, not
incidental* — and why scout can already read inspect logs (`EvalLogTranscriptsView`)
but not the reverse. Keep the distinction crisp in the meeting: don't let "superset"
get overclaimed as field-level superset.

**Same data, different use cases** (the framing to lead with):
- **inspect** is a *single-eval debugging / inspection* tool: open one log, see its
  samples, scores, transcript, drill in. Whole-log-in-memory + client grid is a
  reasonable fit for that job.
- **scout** is a *cross-corpus analysis / scanning* tool: query across many
  transcripts and scans, filter/sort/paginate over data too large to hold client
  side. Server-side query protocol is essential to that job.

A scan result and a sample score *look* tabular and similar, but one is "the output
of running a scanner across a corpus" and the other is "the grading of one sample in
one eval." Whether they should share a presentation/abstraction depends on whether
we expect their scale and interaction model to converge.

## 1.7 Scale envelope — current state vs the arbitrarily-large-data requirement (R)

The expected requirement R (see top of doc) has **two independent axes**:

- **Axis 1 — cardinality:** many records (logs / evals / scans / transcripts). The
  *listing/query* problem → solved by server-side filter/sort + pagination against an
  indexed store; broken by "list/load everything then work in memory."
- **Axis 2 — content size:** one record whose contents are huge (many samples, large
  scanner-result sets, long message/event streams, big attachments). The *load-one-
  big-thing* problem → solved by streaming / virtualization / ranged (point) reads;
  broken by "load the whole record."

These are orthogonal: a surface can pass one and fail the other. Current state:

| Surface | Axis 1 — cardinality | Axis 2 — content size |
|---|---|---|
| scout transcripts, Parquet source | ✓ server keyset paging + DuckDB pushdown | ✓ lazy message/event streaming; per-row column (point) reads — `get_fields`, see `parquet-point-lookup-analysis.md` |
| scout transcripts, eval-log source | ⚠ in-memory SQLite — memory-bound on the indexed set | ⚠ inherits underlying eval-log read path |
| scout scans (list) | ✗ full dir scan + load-all per request (§1.3.1) | n/a (metadata only) |
| scout scanner-results dataframe | ✗ whole `ColumnTable` held in browser | ✗ entire result set materialized client-side |
| inspect log list | ⚠ whole directory listing at once (names+mtime), client grid | n/a (listing only) |
| inspect samples | ✗ whole `EvalLog` (all sample summaries) in memory; header-only is the only escape hatch | ✗ whole log loaded to view a sample |
| inspect sample events (transcript) | — | ⚠ incremental cursor for live append; completed logs read segment ZIPs / presigned-S3 for big attachments |

Reading: **only the Parquet-backed scout transcript path passes both axes today.**
Everything else fails at least one — inspect samples and scout's dataframe/scans fail
both. R is therefore mostly a *gap*, not a met requirement, and it is the strongest
forcing function for the server-query and storage goals (G1/G3). Note Axis 2 is the
one most easily forgotten: server-side pagination (Axis 1) does nothing for a single
10-GB sample — that needs streaming/ranged reads, a separate investment.

---

# Part 2 — Discussion guide

Framed as talking points / decisions for the team.

## 2.1 Lead framing: same data, different jobs
Before debating shared code, align on this: inspect and scout often render the
*same underlying data* (eval logs, samples, model usage) but for **different user
jobs** — inspect for *debugging one eval*, scout for *analyzing across many*. That
difference, not technology preference, is what drives ag-grid-client-side vs
TanStack-server-side. Decide which divergences flow necessarily from the job and
which are just historical accident.

**Sharing is not hypothetical — it already ships, in both directions.** Scout
consumes `inspect-components`; inspect consumes `scout-components` to render
scout-scanner-as-scorer results in its "scans" tab (§1.4). So the question for the
meeting is not "should these products share code?" (they do) but "*how far* up the
stack does sharing go — presentation only, or also grids / query protocol / record
model?" The scans-tab integration is also a live instance of the "scout as analysis
layer over inspect" direction (Q5) already in production.

> Motivation for everything below — the "what's actually wrong with the status quo"
> problem set (P1–P5) — is at the **top of this document**. Validate those pains
> first; they gate the goals in §2.4.

## 2.2 Sharing candidates (ranked by leverage / feasibility)

1. **Presentational components — already shared; lean in.** `MetaDataGrid`,
   `ModelTokenTable`, `RecordTree`, chat/transcript virtual lists, all in the single
   shared `ts-mono` monorepo mounted into both repos. Low risk — this is genuinely
   one codebase, not copies. *Decision:* formalize ownership/versioning of
   `inspect-components` so a change for one app doesn't silently break the other.

2. **Scout's query protocol as a shared package.** `Condition` / `OrderBy` /
   `Pagination` + keyset helpers + the `…View` ABCs are clean, backend-agnostic, and
   already prove they can sit in front of inspect eval logs (`EvalLogTranscriptsView`).
   Highest-value *architectural* sharing candidate. Feasibility hinges on whether
   inspect wants server-side query at all (see 2.3.1). **Caveat:** a shared protocol
   only delivers scale if the *backend* behind it is scalable — and scout's own scans
   backend isn't yet (§1.3.1). Don't sell the protocol as "scalable" without the
   storage to back it.

3. **A shared interactive grid abstraction.** Today scout has `DataGrid` (TanStack)
   and inspect has `SamplesGrid` (ag-grid) — two parallel generic wrappers solving
   the same problem with different libs. Converging would remove real duplication,
   but requires picking a library (2.3.2). Medium-high effort.

4. **Faceted filter values / distinct endpoint pattern.** Scout's `distinct` endpoint
   is a clean primitive inspect could adopt if it ever moves filtering server-side.

## 2.3 Divergences worth debating (real design choices, not accidents)

1. **Compute locus: server vs client.** Is inspect's whole-log-in-memory model a
   constraint we want to keep (simplicity, offline/static hosting, VSCode/static-http
   backends) or a limit we want to lift (large logs, cross-log queries)? Scout
   already paid the cost of a server query protocol; does inspect's roadmap need it?

2. **Grid library: TanStack vs ag-grid.** Scout chose TanStack for its main views
   (headless, fully custom `DataGrid`) yet *also* ships ag-grid for the results
   dataframe. Inspect is all-in on ag-grid. Standardizing has bundle, feature, and
   licensing implications (both are Community today — if either wants grouping/
   pivoting that's ag-grid Enterprise $$). Three live options: standardize on
   TanStack, standardize on ag-grid, or keep both with a shared interface.

3. **Record model: transcript vs log+sample.** Is scout's flat, source-agnostic
   `Transcript` the right shared abstraction, or is inspect's file→sample hierarchy
   essential? This determines whether a shared grid/protocol is even coherent.

4. **Pagination model.** Keyset cursor (scout) vs load-everything (inspect) vs
   inspect's id-cursor live-append. If we share a protocol, which pagination
   semantics are canonical?

5. **"Scalable backend" is a per-source property, not a per-product one.** Scout looks
   uniformly server-scalable from the API surface, but its three backends span a
   spectrum (§1.3.1): DuckDB-over-Parquet transcripts (scalable) → in-memory-SQLite
   eval-log transcripts (memory-bound, cached) → per-request full-scan scans (not
   scalable). Debate: are the in-memory paths known-acceptable shortcuts (small
   corpora) or latent debt that needs real stores before data grows / before the
   protocol is pitched as the shared scalable path?

## 2.4 Goals, cost & priority (better ≠ worth doing)

Each goal below maps to the status-quo pain (P1–P5) or the cross-cutting requirement
**R** (top of document) it addresses, a **rough cost**, and a **priority
recommendation to debate** — not a decree. The point of the cost column is to resist
"X is better, so let's do X": several of these are genuine improvements that still
shouldn't be prioritized now.

Cost legend: **S** = days · **M** = weeks · **L** = months / multi-quarter.

| Goal | Addresses | Rough cost | Recommendation (to debate) |
|---|---|---|---|
| **G1. Extract query protocol as a shared package** (`Condition`/`OrderBy`/`Pagination` + `…View` ABCs) | P3, R-ax1 | **M** | **Defer until pulled.** Don't build speculatively — only when inspect concretely needs server-side query (see Q2). The protocol already exists in scout; extraction is cheap *when* there's a second consumer. |
| **G2. Converge on one grid library / shared interactive-grid abstraction** | P1, P2 | **L** | **Defer / only-if proven.** High effort, touches both apps. Justify only if P1/P2 are confirmed real and recurring. Cheaper interim: a thin shared interface over both libs. |
| **G3. Give scans a real persistent/indexed backend** (mirror transcripts' Parquet/DuckDB) | P4, R-ax1 | **M** | **Threshold-gated.** Accept the per-request scan until scan-counts cross an agreed number; define that trigger now so it's not a surprise later. |
| **G4. Unify table UX** (selection model, filter UX) across products | P2 | **M** | **Only-if shared users.** Worth it only if P2 is validated; otherwise per-product UX is fine and even desirable (different jobs). |
| **G5. Reconcile the record model** (transcript vs log+sample) | P5 | **L / strategic** | **Decide direction before building.** This is a strategy call (Q1/Q5), not an implementation task. No code cost until direction is set; large cost if pursued. |
| **G6. Scale per-record content** (streaming / virtualization / ranged-reads for huge samples / result-sets / event streams) | R-ax2 | **M–L** | **Requirement-gated, currently uncovered.** No other goal addresses Axis 2 — server-side pagination (G1/G3) does nothing for a single giant record. Scout's Parquet path already does point reads (`get_fields`); inspect samples and scout's dataframe load whole. Scope per surface once R is committed. |

Reading: nothing here is an unambiguous do-now. **G1** and **G3** are "prepare the
trigger, don't build yet" (and both advance R's cardinality axis). **G6** is the one
that covers R's content-size axis — easy to overlook because the pagination work
*feels* like it solves scale but doesn't touch it. **G2/G4/G5** are real improvements
gated on validating the underlying pain and/or a strategic decision — explicitly
*not* default-yes.

## 2.5 Open roadmap questions (decisions to make)

- **Q1.** Do we want *one* table architecture across both products, or accept two
  justified by different jobs? (Everything below depends on this.)
- **Q2.** Should inspect adopt scout's server-side query protocol for large logs /
  cross-log views — and is that on anyone's roadmap?
- **Q3.** If we converge grids, which library wins, and who owns the shared
  `DataGrid`/`SamplesGrid` successor?
- **Q4.** Should `Condition`/`OrderBy`/`Pagination` be extracted into a standalone
  package usable by both Python backends (and exported to TS once, not twice)?
- **Q5.** Given scout's `EvalLogTranscriptsView` already reads inspect logs — is the
  intended end state "scout is the analysis layer over inspect data," and if so does
  inspect's own viewer converge toward scout's protocol or stay independent?
- **Q6.** Does the scans backend need a real persistent/indexed store (mirroring the
  transcripts Parquet/DuckDB approach) before scans-per-directory grow, or is the
  per-request scan acceptable for the foreseeable scale? Owner + trigger threshold?
- **Q7.** Do we commit to **R (arbitrarily large data)** as a real requirement, and on
  what timeline? If so, sequence the two axes (§1.7): cardinality (G1/G3) vs
  content-size (G6) — which bites first, and which product/surface drives it? Only the
  Parquet transcript path clears both today; everything else needs work.
