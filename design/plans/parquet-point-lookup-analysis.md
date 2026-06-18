# Parquet point-lookup efficiency analysis

Investigation into how efficiently Scout reads a single row's columns out of a
results parquet file, and what that costs over remote/S3.

## The question

`get_fields` (in `src/inspect_scout/_recorder/file.py`) fetches specific columns
for one row by id. If we need a value from the *last* row of a massive row group,
did we have to read the entire column?

## General Parquet read model

Physical layout:

```
File
└── Row Group            ← horizontal partition of rows (byte/row bounded)
    └── Column Chunk      ← all values of one column in this row group
        └── Page          ← atomic unit of compression/encoding (default ~1 MB uncompressed)
```

Three nested layers of pruning, each optional:

1. **Row-group pruning (almost always available)** — footer holds per-RG,
   per-column min/max stats + column-chunk byte offsets. Lets a reader skip whole
   row groups and seek directly to a column chunk via one ranged read.
2. **Page pruning (only with the Page Index)** — `ColumnIndex` + `OffsetIndex`
   give per-page min/max + offsets. Requires the writer to enable it AND a read
   path that pushes a filter down. `read_row_group(columns=...)` applies **no**
   row filter → reads the **entire column chunk** regardless.
3. **Within a page — no pruning.** Page is the smallest decodable unit.

The smallest readable unit is the **page**. You cannot read a single cell without
decompressing its whole page.

### "Last row of a massive row group"

- You never read the whole column across the file — RG pruning + chunk offset get
  you to the right row group's chunk.
- Whether you read the whole *column chunk* for that RG depends on the read path:
  - `read_row_group(columns=...)` → **entire chunk** (all pages), filter in memory.
    Position of the row is irrelevant — first vs last costs the same.
  - dataset `to_table(filter=...)` with a page index → can skip to matching pages
    of the **filter** column; projected columns still read for surviving rows.

### Why "huge cells" makes it worse

Page size is a **byte** budget (~1 MB), not a row count. Huge values (JSON blobs,
transcripts) → few rows per page. Over-read cost ≈
`row_group_size × avg_value_size` for the target columns. **Row group size is the
dominant tuning knob.**

## Scout-specific case: `get_fields(scanner, "uuid", uuid, ["input"])`

### How row groups are written (`_recorder/buffer.py`)

- Rows accumulate until `accumulated_bytes + size > MAX_BYTES` (`MAX_BYTES =
  100_000_000`), then one `writer.write_table(table)` → **one row group**.
- `accumulated_bytes` is `batch.nbytes` — in-memory Arrow size of **all** columns
  combined. `input` dominates, so it effectively *is* the row group.
- `compression="zstd"`, `use_dictionary=True`.

### `_point_lookup` (in `_recorder/file.py`)

**Remote path** (`s3://`, `gs://`, `abfs://`):

```python
pf = pq.ParquetFile(pa_path, filesystem=pa_fs)        # footer only
for i in range(pf.metadata.num_row_groups):
    rg_ids = pf.read_row_group(i, columns=["uuid"])   # uuid chunk for RG i
    mask = pc.equal(rg_ids["uuid"], id_value)
    if pc.any(mask).as_py():
        rg_data = pf.read_row_group(i, columns=["input"])  # ENTIRE input chunk for RG i
        return rg_data.filter(mask)                    # keep 1 row
```

- Random uuids → min/max stats useless → must linearly read each RG's uuid chunk
  until the match.
- On match: reads the **entire `input` column chunk for that row group**, then
  filters to one row. Position in RG irrelevant.

**Local path** (local disk, or `az://` slurped to BytesIO): dataset scanner with
`filter=(pc.field("uuid") == id_value)`. Same cost shape — one row group's `input`
chunk materialized to yield one row. (`az://` downloads the whole file first.)

### The trap: the page index does NOT save random-uuid lookups

- Page-skip pushdown prunes pages of the **filter** column by its min/max. Random
  uuids → page ranges overlap → nothing prunes.
- The thing that *would* work — read uuid chunk, find the match's ordinal row
  index R, then use `input`'s `OffsetIndex` to read only the page containing row R
  (immune to key randomness) — is **not exposed by pyarrow's high-level API**.
- So enabling `write_page_index` buys nothing through this code's read paths.

### Levers that actually work

| Lever | Effect | Cost |
|---|---|---|
| Lower `MAX_BYTES` / explicit `row_group_size` | Linear cut in over-read per lookup | More uuid round trips, marginally worse zstd, bigger footer |
| Sort rows by `uuid` at write + page index | uuid stats prunable → 1 RG, then page-skip works → ~page-granular reads | Writer must buffer+sort whole table, breaks bounded-memory streaming flush |
| Companion uuid → (row_group, offset) index | True point lookups | Extra artifact to maintain |
| API-layer cache (ParquetFile/row-group/table per scan) | Amortizes repeated reads when browsing one scan | Memory; partly defeats remote streaming |

## Where the input column renders (frontend)

The lookup is the interactive per-click path:

- Endpoint: `_view/_api_v2_scans.py:365` → `result.get_fields(scanner, "uuid", uuid, requested)`
- Request: `GET .../{scanner}/{uuid}?column=input&column=input_type&column=input_data&column=scan_events`
  (`api-scout-server.ts:268`, `getScannerDataframeDetail`)
- Fetch chain: `ScannerResultPanel.tsx:179` → `useSelectedScanResultDetail`
  → `useScanDataframeDetail.ts:30` → `getScannerDataframeDetail`
- Render: `ScannerResultPanel.tsx:180` (`inputData = detailData?.input`), shown in
  the **Input** tab and passed to `<ResultPanel inputData=… />` (`:388`).

So selecting one result triggers one on-demand point lookup, fetching **four**
heavy columns (`input`, `input_type`, `input_data`, `scan_events`) for that uuid —
each is a full column-chunk read of the matching row group on S3.

## Measured: `target_word_transcript.parquet`

`~/Documents/ScoutProjects/scans/scan_id=G3fBF6ywnoVUk3skPUFhmQ/target_word_transcript.parquet`

- **8 row groups**, 6968 rows, 56 columns, ZSTD.
- `input` at col index 34, `uuid` at col index 36 (BYTE_ARRAY).

### `input` column chunk per row group

| RG | rows | comp | uncomp | zstd | dict page | data pages |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 905 | 19.5 MB | 95.0 MB | 4.9× | 1 (~1.5 MB uncomp) | 75 |
| 1 | 987 | 21.5 MB | 94.6 MB | 4.4× | 1 | 78 |
| 2 | 895 | 20.6 MB | 95.0 MB | 4.6× | 1 | 78 |
| 3 | 931 | 19.6 MB | 95.0 MB | 4.9× | 1 | 80 |
| 4 | 901 | 18.3 MB | 94.8 MB | 5.2× | 1 | 76 |
| 5 | 867 | 20.9 MB | 94.7 MB | 4.5× | 1 | 75 |
| 6 | 898 | 19.6 MB | 95.0 MB | 4.9× | 1 | 76 |
| 7 | 584 | 12.4 MB | 59.9 MB | 4.8× | 1 | 47 |
| **tot** | 6968 | **152 MB** | **724 MB** | | | ~585 |

Findings:

- Row groups are byte-bounded at ~95 MB **uncompressed** = the `MAX_BYTES` cap;
  `input` alone accounts for essentially all of it. RG7 is the partial tail flush.
- Data pages are the default ~1 MB uncompressed (~0.2–0.35 MB compressed),
  ~75–80 per chunk, ~12 rows/page, ~105 KB uncompressed per `input` value avg.
- Encodings `PLAIN, RLE, RLE_DICTIONARY` with a tiny ~1 MB dict page = dictionary
  hit its 1 MB limit immediately and **fell back to PLAIN** for the other ~94 MB.
  Values are unique → dictionary buys nothing → relies entirely on zstd. Confirms
  the "one unique input per transcript" expectation.
- **No offset/page index** (`has_offset_index = False`).

### `uuid` column chunk per row group

| RG | rows | comp | uncomp | ratio |
|---:|---:|---:|---:|---:|
| 0 | 905 | 18.1 KB | 24.8 KB | 1.4× |
| 1 | 987 | 18.1 KB | 27.0 KB | 1.5× |
| 2 | 895 | 16.3 KB | 24.5 KB | 1.5× |
| 3 | 931 | 17.0 KB | 25.5 KB | 1.5× |
| 4 | 901 | 17.1 KB | 24.7 KB | 1.4× |
| 5 | 867 | 17.3 KB | 23.7 KB | 1.4× |
| 6 | 898 | 17.0 KB | 24.6 KB | 1.4× |
| 7 | 584 | 10.5 KB | 16.0 KB | 1.5× |
| **tot** | 6968 | **131 KB** | **191 KB** | |

~17 KB compressed per RG, 131 KB for all 8. Random uuids barely compress (~1.4×)
but are so small it doesn't matter.

## Bottom line

A single remote point lookup on this file:

- `uuid` scan across up to 8 row groups = **≤131 KB** (negligible, <1% of transfer).
- Matching `input` chunk = **~18–21 MB compressed over the wire** (→ ~95 MB
  decompressed) to return **one ~21 KB compressed value** — a **~900× over-read**,
  independent of row position.
- The live endpoint reads 4 such heavy columns per click, so real per-open
  transfer is this plus the other three columns' chunks.

The data is physically in ~0.25 MB pages (~12 rows each); a position-based
single-page read would cost ~0.25 MB instead of ~19 MB — but no offset index and
no pyarrow page-by-row-index read make that granularity unreachable here.

**Row group size (`MAX_BYTES`) is the only lever that matters for this file.** The
uuid scan, which looked alarming in the abstract, is a rounding error. Sort-by-uuid
would shrink the already-negligible 131 KB while doing nothing about the 19 MB.
