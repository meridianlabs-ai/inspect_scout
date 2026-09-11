"""Static bundle generator: materializes a scout project view as a directory.

Produces the ``scout-static-bundle`` v1 layout consumed by the scout viewer's
static-bundle mode (see ts-mono docs/static-bundle-format.md): plain JSON
compressed with zstd — sharded catalogs with per-shard min/max stats, O(1)
per-transcript item files, Arrow IPC scanner dataframes. No parquet, no wasm.
"""

from __future__ import annotations

import base64
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path as PathlibPath
from typing import TYPE_CHECKING, Any

import zstandard
from inspect_ai._util.json import to_json_safe
from upath import UPath

from .._display._display import display
from .._project._project import read_project, read_project_config_with_etag
from .._util.constants import DEFAULT_SCANS_DIR
from ._api_v2_types import AppConfig, AppDir, ScannersResponse
from .server import _resolve_dist_directory
from .types import ViewConfig

if TYPE_CHECKING:
    from .._recorder.recorder import ScanResultsArrow
    from .._transcript.database.database import TranscriptsView
    from .._transcript.types import TranscriptInfo

BUNDLE_FORMAT = "scout-static-bundle"
BUNDLE_VERSION = 1
DEFAULT_SHARD_SIZE = 2000
MAX_COLUMN_VALUES = 1000
SCOUT_CONTEXT_PLACEHOLDER = "</head>"

# Heavy per-row columns served via details/<uuid>.json.zst rather than the
# scanner dataframe (the viewer always excludes them from grid fetches).
DATAFRAME_EXCLUDE_COLUMNS = ["input", "scan_events"]


async def bundle_view(
    config: ViewConfig,
    output_dir: PathlibPath,
    shard_size: int = DEFAULT_SHARD_SIZE,
    max_details: int | None = None,
    force: bool = False,
) -> None:
    """Materialize a static bundle of the given project view into ``output_dir``.

    The output directory will contain the frontend SPA (copied from the
    resolved dist directory) plus an ``api/`` subdirectory with the
    scout-static-bundle v1 layout: ``manifest.json``, sharded ``.json.zst``
    catalogs, per-transcript item files, and per-scan status/dataframe/detail
    files.

    Args:
        config: View configuration (project + optional CLI dir overrides).
        output_dir: Where to write the bundle. Created if missing.
        shard_size: Rows per catalog shard.
        max_details: Cap on number of per-row detail blobs baked per scanner.
        force: If True, remove ``output_dir`` first if it exists.
    """
    output_dir = PathlibPath(output_dir).resolve()

    if output_dir.exists():
        if not force:
            raise click_usage_error(
                f"Output directory already exists: {output_dir} "
                "(use --force to overwrite)"
            )
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    api_dir = output_dir / "api"
    api_dir.mkdir()

    display().print(f"Bundling scout view to {output_dir}")

    # Resolve target directories from the view config (mirrors view server).
    project = config.project or read_project()
    transcripts_path = config.transcripts_cli or project.transcripts
    scans_path = config.scans_cli or project.scans or DEFAULT_SCANS_DIR

    # 1. Copy the frontend dist and inject the scout_context boot tag.
    dist_dir = _resolve_dist_directory()
    _copy_dist(dist_dir, output_dir)
    _inject_bundle_context(output_dir / "index.html")

    # 2. Bake trivial endpoints.
    _write_json(
        api_dir / "config.json",
        _build_app_config(config, transcripts_path, scans_path),
    )
    _write_json(api_dir / "scanners.json", _build_scanners_response())
    _write_project_config(api_dir / "project-config.json")

    # 3. Bake catalogs + items.
    transcripts_manifest = (
        await _bundle_transcripts(
            transcripts_dir=transcripts_path,
            api_dir=api_dir,
            shard_size=shard_size,
        )
        if transcripts_path is not None
        else None
    )
    scans_manifest = await _bundle_scans(
        scans_dir=scans_path,
        api_dir=api_dir,
        shard_size=shard_size,
        max_details=max_details,
    )

    # 4. Write the bundle manifest (the viewer's entry point).
    manifest: dict[str, Any] = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if transcripts_manifest is not None:
        manifest["transcripts"] = transcripts_manifest
    if scans_manifest is not None:
        manifest["scans"] = scans_manifest
    _write_json(api_dir / "manifest.json", manifest)

    transcript_count = transcripts_manifest["row_count"] if transcripts_manifest else 0
    scan_count = scans_manifest["row_count"] if scans_manifest else 0
    display().print(
        f"Bundle complete: {transcript_count} transcripts, {scan_count} scans"
    )


def click_usage_error(message: str) -> Exception:
    """Build a Click usage error without importing Click at module top."""
    import click

    return click.UsageError(message)


# ---- output helpers --------------------------------------------------------


def _write_json(path: PathlibPath, value: object) -> None:
    """Write a JSON-serializable value to disk using inspect's safe encoder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _write_json_zst(path: PathlibPath, value: object) -> None:
    """Write a zstd-compressed JSON file (`.json.zst`)."""
    _write_bytes_zst(path, _json_bytes(value))


def _write_bytes_zst(path: PathlibPath, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(zstandard.ZstdCompressor().compress(data))


def _json_bytes(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode()
    return to_json_safe(value)


def _jsonable(value: object) -> Any:
    """Round-trip a model/dataclass through inspect's safe JSON encoder."""
    return json.loads(to_json_safe(value))


def _base64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).rstrip(b"=").decode()


# ---- catalog sharding ------------------------------------------------------


def _sort_key(value: object) -> tuple[int, float | str]:
    """Total order matching the viewer's scalarCompare.

    Nulls sort first, numbers numerically, everything else as strings.
    """
    if value is None:
        return (0, "")
    if isinstance(value, bool):
        return (2, str(value))
    if isinstance(value, (int, float)):
        return (1, float(value))
    return (2, str(value))


def _write_catalog(
    rows: list[dict[str, Any]],
    *,
    api_dir: PathlibPath,
    section: str,
    dir_uri: str,
    id_column: str,
    order_column: str,
    order_direction: str,
    shard_size: int,
) -> dict[str, Any]:
    """Shard catalog rows and return the CatalogManifest section.

    Rows are written globally sorted ascending by ``order_column`` (nulls
    first) so the viewer can serve default-order pages from a subset of
    shards using the recorded per-shard min/max.
    """
    rows = sorted(rows, key=lambda r: _sort_key(r.get(order_column)))

    shards: list[dict[str, Any]] = []
    for i in range(0, len(rows), shard_size):
        chunk = rows[i : i + shard_size]
        rel_path = f"{section}/catalog/shard-{i // shard_size:04d}.json.zst"
        _write_json_zst(api_dir / rel_path, chunk)
        shards.append(
            {
                "path": rel_path,
                "row_count": len(chunk),
                "min": chunk[0].get(order_column),
                "max": chunk[-1].get(order_column),
            }
        )

    column_values = _collect_column_values(rows)
    manifest: dict[str, Any] = {
        "dir": dir_uri,
        "id_column": id_column,
        "row_count": len(rows),
        "default_order": {"column": order_column, "direction": order_direction},
        "shards": shards,
    }
    if column_values:
        rel_path = f"{section}/columns.json"
        _write_json(api_dir / rel_path, column_values)
        manifest["column_values"] = rel_path
    return manifest


def _collect_column_values(
    rows: list[dict[str, Any]],
) -> dict[str, list[Any]]:
    """Precompute sorted distinct scalar values per column.

    Used for filter autocomplete; columns whose cardinality exceeds the
    cap are dropped.
    """
    distincts: dict[str, set[Any]] = {}
    dropped: set[str] = set()
    for row in rows:
        for column, value in row.items():
            if column in dropped:
                continue
            if value is not None and not isinstance(value, (str, int, float, bool)):
                dropped.add(column)
                distincts.pop(column, None)
                continue
            values = distincts.setdefault(column, set())
            values.add(value)
            if len(values) > MAX_COLUMN_VALUES:
                dropped.add(column)
                del distincts[column]
    return {
        column: sorted(values, key=_sort_key)
        for column, values in distincts.items()
        if values
    }


# ---- SPA -------------------------------------------------------------------


def _copy_dist(dist_dir: PathlibPath, output_dir: PathlibPath) -> None:
    """Copy dist contents into output_dir (merging at root, not nesting)."""
    for entry in dist_dir.iterdir():
        target = output_dir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target)
        else:
            shutil.copy2(entry, target)


def _inject_bundle_context(index_path: PathlibPath) -> None:
    """Inject a <script id='scout_context'> tag into the bundled index.html.

    The SPA's main.tsx detects this tag at boot and switches to static-bundle
    API mode.
    """
    html = index_path.read_text()
    context = {"bundle": True, "bundleBaseUrl": "./api"}
    # The flag-setting script must run BEFORE the SPA's ESM bundle so that
    # module-init code (e.g. router activities.tsx) sees the static-bundle
    # flag before it computes its filtered list. Both go inside <head>
    # before the </head> placeholder, and so are evaluated before the
    # <script type="module"> in the original template.
    script = (
        '<script id="scout_context" type="application/json">'
        f"{json.dumps(context)}"
        "</script>\n"
        "<script>window.__SCOUT_STATIC_BUNDLE__=true;</script>\n"
    )
    if SCOUT_CONTEXT_PLACEHOLDER not in html:
        raise RuntimeError(
            f"Could not find {SCOUT_CONTEXT_PLACEHOLDER!r} in index.html "
            "(bundled SPA template may have changed)"
        )
    html = html.replace(
        SCOUT_CONTEXT_PLACEHOLDER, script + SCOUT_CONTEXT_PLACEHOLDER, 1
    )
    index_path.write_text(html)


# ---- trivial endpoints -----------------------------------------------------


def _build_app_config(
    view_config: ViewConfig,
    transcripts_path: str | None,
    scans_path: str,
) -> AppConfig:
    """Build the AppConfig payload that the live /app-config endpoint returns."""
    project = view_config.project or read_project()
    return AppConfig(
        **project.model_dump(exclude={"transcripts", "scans", "results"}),
        home_dir=UPath(PathlibPath.home()).resolve().as_uri(),
        project_dir=UPath(PathlibPath.cwd()).resolve().as_uri(),
        transcripts=AppDir(
            dir=UPath(transcripts_path).resolve().as_uri(),
            source="cli" if view_config.transcripts_cli else "project",
        )
        if transcripts_path is not None
        else None,
        scans=AppDir(
            dir=UPath(scans_path).resolve().as_uri(),
            source="cli" if view_config.scans_cli else "project",
        ),
    )


def _build_scanners_response() -> ScannersResponse:
    """Build the scanners listing the live /scanners endpoint returns.

    Uses the same registry-based enumeration as the API handler.
    """
    import inspect
    from typing import Callable, cast

    from inspect_ai._util.registry import registry_find, registry_info
    from inspect_ai.util import json_schema

    from ._api_v2_types import ScannerInfo, ScannerParam

    def param_schema(p: inspect.Parameter) -> dict[str, Any]:
        if p.annotation == inspect.Parameter.empty:
            return {"type": "any"}
        return json_schema(p.annotation).model_dump(exclude_none=True)

    scanner_objs = registry_find(lambda info: info.type == "scanner")
    items = [
        ScannerInfo(
            name=registry_info(s).name,
            version=registry_info(s).metadata.get("scanner_version", 0),
            description=s.__doc__.split("\n")[0] if s.__doc__ else None,
            params=[
                ScannerParam(
                    name=p.name,
                    schema=param_schema(p),
                    required=p.default == inspect.Parameter.empty,
                    default=(
                        p.default if p.default != inspect.Parameter.empty else None
                    ),
                )
                for p in inspect.signature(
                    cast(Callable[..., Any], s)
                ).parameters.values()
            ],
        )
        for s in scanner_objs
    ]
    return ScannersResponse(items=items)


def _write_project_config(path: PathlibPath) -> None:
    """Bake the ProjectConfig; the static viewer supplies a frozen etag."""
    config, _etag = read_project_config_with_etag()
    _write_json(path, config.model_dump())


# ---- transcripts -----------------------------------------------------------


async def _bundle_transcripts(
    transcripts_dir: str,
    api_dir: PathlibPath,
    shard_size: int,
) -> dict[str, Any]:
    """Bake the transcripts catalog + per-transcript item files.

    Returns the CatalogManifest section for the bundle manifest.
    """
    from .._query import Query
    from .._transcript.database.factory import transcripts_view

    def catalog(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return _write_catalog(
            rows,
            api_dir=api_dir,
            section="transcripts",
            dir_uri=transcripts_dir,
            id_column="transcript_id",
            order_column="date",
            order_direction="DESC",
            shard_size=shard_size,
        )

    try:
        async with transcripts_view(transcripts_dir) as view:
            infos = [info async for info in view.select(Query())]
            for info in infos:
                await _write_transcript_item(view, info, api_dir)
            return catalog([_jsonable(info.model_dump()) for info in infos])
    except FileNotFoundError:
        return catalog([])


async def _write_transcript_item(
    view: "TranscriptsView",
    info: "TranscriptInfo",
    api_dir: PathlibPath,
) -> None:
    """Write the combined info + messages-events item for one transcript."""
    # Slashes are valid in transcript_id strings — make a filesystem-safe name.
    safe_id = info.transcript_id.replace("/", "_").replace("\\", "_")
    item_path = api_dir / "transcripts" / "items" / f"{safe_id}.json.zst"
    if item_path.exists():
        raise RuntimeError(
            f"Transcript id collision after sanitization: {info.transcript_id!r}"
        )

    result = await view.read_messages_events(info)
    raw_chunks: list[bytes] = []
    async with result.data as data:
        async for chunk in data:
            raw_chunks.append(chunk)
    raw = b"".join(raw_chunks)

    payload = _decompress_payload(raw, result.compression_method)
    merged = _merge_info_into_payload(to_json_safe(info.model_dump()), payload)
    _write_bytes_zst(item_path, merged)


def _merge_info_into_payload(info_json: bytes, payload: bytes) -> bytes:
    """Splice `"info": {...}` into the messages-events JSON object.

    Avoids parsing the (potentially very large) payload just to add a key.
    """
    body = payload.lstrip()
    if not body.startswith(b"{"):
        raise ValueError("messages-events payload is not a JSON object")
    rest = body[1:].lstrip()
    if rest.startswith(b"}"):
        return b'{"info":' + info_json + b"}"
    return b'{"info":' + info_json + b"," + body[1:]


def _decompress_payload(raw: bytes, compression: object) -> bytes:
    """Decompress raw transcript bytes to plain UTF-8 JSON."""
    from inspect_ai._util.zip_common import ZipCompressionMethod

    if compression is None or compression == ZipCompressionMethod.STORED:
        return raw
    if compression == ZipCompressionMethod.ZSTD:
        # Use streaming API — server-emitted zstd frames omit the content
        # size in the header, so the one-shot .decompress() can't size the
        # output buffer.
        return zstandard.ZstdDecompressor().stream_reader(raw).read()
    if compression == ZipCompressionMethod.DEFLATE:
        import zlib

        # ZIP DEFLATE is raw (RFC 1951), not zlib-wrapped (RFC 1950).
        return zlib.decompress(raw, -zlib.MAX_WBITS)
    raise ValueError(f"Unsupported compression method: {compression}")


# ---- scans -----------------------------------------------------------------


async def _bundle_scans(
    scans_dir: str,
    api_dir: PathlibPath,
    shard_size: int,
    max_details: int | None,
) -> dict[str, Any]:
    """Bake the scans catalog + per-scan status/dataframes/details.

    Returns the CatalogManifest section for the bundle manifest.
    """
    from .._query import Query
    from .._scanjobs import scan_jobs_view

    def catalog(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return _write_catalog(
            rows,
            api_dir=api_dir,
            section="scans",
            dir_uri=scans_dir,
            id_column="scan_id",
            order_column="timestamp",
            order_direction="DESC",
            shard_size=shard_size,
        )

    try:
        async with await scan_jobs_view(scans_dir) as view:
            rows = [row async for row in view.select(Query())]
    except Exception:
        # Scans dir missing or unreadable — emit an empty catalog.
        return catalog([])

    scans_base = UPath(scans_dir)
    for row in rows:
        scan_path_abs = UPath(row.location)
        try:
            scan_rel = str(scan_path_abs.relative_to(scans_base))
        except ValueError:
            scan_rel = scan_path_abs.name
        await _write_scan_item(
            location=row.location,
            item_dir=api_dir / "scans" / "items" / _base64url(scan_rel),
            max_details=max_details,
        )

    return catalog([_jsonable(row.model_dump()) for row in rows])


async def _write_scan_item(
    location: str,
    item_dir: PathlibPath,
    max_details: int | None,
) -> None:
    from .._scanresults import scan_results_arrow_async, scan_results_df_async

    item_dir.mkdir(parents=True, exist_ok=True)

    # status.json — mirror the live GET /scans/{dir}/{scan} JSON shape.
    status = await scan_results_df_async(location, rows="transcripts")
    if status.spec.transcripts:
        status.spec.transcripts = status.spec.transcripts.model_copy(
            update={"data": None}
        )
    _write_json(item_dir / "status.json", status)

    arrow = await scan_results_arrow_async(location)
    for scanner in arrow.scanners:
        _write_scanner_dataframe(
            arrow, scanner, item_dir / "scanners" / f"{scanner}.arrow"
        )
        _write_scanner_details(
            arrow,
            scanner,
            item_dir / "details" / scanner,
            max_details=max_details,
        )


def _write_scanner_dataframe(
    arrow: "ScanResultsArrow",
    scanner: str,
    out_path: PathlibPath,
) -> None:
    """Serialize a scanner's Arrow record batches to an IPC stream file.

    Mirrors the live /scans/{dir}/{scan}/{scanner} endpoint (LZ4 compression),
    excluding the heavy per-row columns the viewer never fetches in grids —
    those are served from details/<uuid>.json.zst instead.
    """
    import io

    import pyarrow.ipc as pa_ipc

    out_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with arrow.reader(scanner, exclude_columns=DATAFRAME_EXCLUDE_COLUMNS) as reader:
        with pa_ipc.new_stream(
            buf,
            reader.schema,
            options=pa_ipc.IpcWriteOptions(compression="lz4"),
        ) as writer:
            for batch in reader:
                writer.write_batch(batch)
    out_path.write_bytes(buf.getvalue())


def _write_scanner_details(
    arrow: "ScanResultsArrow",
    scanner: str,
    out_dir: PathlibPath,
    max_details: int | None,
) -> None:
    """Bake per-row detail blobs containing the columns the UI fetches."""
    from .._transcript.eval_log import JSON_COLUMNS

    detail_columns = ["input", "input_type", "input_data", "scan_events"]
    json_cols = frozenset(JSON_COLUMNS) | {"scan_events", "input_data"}

    with arrow.reader(scanner) as reader:
        written = 0
        for batch in reader:
            uuids = batch.column("uuid").to_pylist()
            for uuid in uuids:
                if max_details is not None and written >= max_details:
                    return
                fields = arrow.get_fields(scanner, "uuid", uuid, detail_columns)
                _write_bytes_zst(
                    out_dir / f"{uuid}.json.zst",
                    _detail_blob(fields, json_cols),
                )
                written += 1


def _detail_blob(fields: dict[str, Any], json_cols: frozenset[str]) -> bytes:
    """Encode a detail blob, preserving pre-serialized JSON columns verbatim.

    Matches the live endpoint's encoding: columns in JSON_COLUMNS are already
    JSON strings in parquet — embedded raw to avoid double-encoding.
    """
    parts: list[str] = []
    for col, value in fields.items():
        if value is None:
            serialized = "null"
        elif col in json_cols and isinstance(value, str) and value:
            serialized = value
        else:
            serialized = json.dumps(value)
        parts.append(json.dumps(col) + ":" + serialized)
    return ("{" + ",".join(parts) + "}").encode()
