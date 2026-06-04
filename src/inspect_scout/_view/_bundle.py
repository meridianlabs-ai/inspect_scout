"""Static bundle generator: materializes a scout project view as a directory."""

from __future__ import annotations

import json
import shutil
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path as PathlibPath
from typing import TYPE_CHECKING

from inspect_ai._util.json import to_json_safe
from upath import UPath

from .._display._display import display
from .._project._project import read_project, read_project_config_with_etag
from .._util.constants import DEFAULT_SCANS_DIR
from ._api_v2_types import AppConfig, AppDir, ScannersResponse
from .server import _resolve_dist_directory
from .types import ViewConfig

if TYPE_CHECKING:
    from .._query.condition import Condition
    from .._transcript.database.database import TranscriptsView
    from .._transcript.types import TranscriptInfo
    from .._view._api_v2_types import ScanRow

BUNDLE_VERSION = 1
SCOUT_CONTEXT_PLACEHOLDER = "</head>"
TRANSCRIPT_CATALOG_COLUMNS = [
    "bundle_id",
    "transcript_id",
    "source_type",
    "source_id",
    "source_uri",
    "date",
    "task_set",
    "task_id",
    "task_repeat",
    "agent",
    "agent_args",
    "model",
    "model_options",
    "score",
    "success",
    "message_count",
    "total_time",
    "total_tokens",
    "error",
    "limit",
    "metadata",
    "content_path",
    "row_json",
]
SCAN_CATALOG_COLUMNS = [
    "bundle_id",
    "scan_id",
    "scan_name",
    "scan_file",
    "timestamp",
    "packages",
    "metadata",
    "scan_args",
    "location",
    "status",
    "scanners",
    "model",
    "tags",
    "revision_version",
    "revision_commit",
    "revision_origin",
    "total_results",
    "total_errors",
    "total_tokens",
    "active_completion_pct",
    "transcript_count",
    "static_path",
    "status_path",
    "scanner_paths_json",
    "row_json",
]


async def bundle_view(
    config: ViewConfig,
    output_dir: PathlibPath,
    force: bool = False,
) -> None:
    """Materialize a static bundle of the given project view into ``output_dir``.

    The output directory will contain:
    - The frontend SPA (copied from the resolved dist directory)
    - An ``api/`` subdirectory with Parquet catalogs and static payloads
    - A ``scout-bundle.json`` manifest

    Args:
        config: View configuration (project + optional CLI dir overrides).
        output_dir: Where to write the bundle. Created if missing.
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

    # 1. Copy the frontend dist.
    dist_dir = _resolve_dist_directory()
    _copy_dist(dist_dir, output_dir)

    # 2. Inject the scout_context script into index.html.
    _inject_bundle_context(
        output_dir / "index.html",
        transcripts_path=transcripts_path,
        scans_path=scans_path,
    )

    # 3. Bake trivial endpoints.
    await _write_json(
        api_dir / "config.json",
        _build_app_config(config, transcripts_path, scans_path),
    )
    await _write_json(api_dir / "scanners.json", _build_scanners_response())
    await _write_project_config(api_dir / "project-config.json")
    await _write_json(api_dir / "topics.json", _build_topic_versions())

    counts: dict[str, int] = {}

    # 4. Bake transcripts.
    if transcripts_path is not None:
        counts["transcripts"] = await _bundle_transcripts(
            transcripts_dir=transcripts_path,
            api_dir=api_dir,
            project_filter=project.filter,
        )
    else:
        counts["transcripts"] = 0

    # 5. Bake scans.
    counts["scans"] = await _bundle_scans(
        scans_dir=scans_path,
        api_dir=api_dir,
    )

    # 6. Write bundle manifest.
    manifest = {
        "version": BUNDLE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "transcripts_dir": transcripts_path,
        "scans_dir": scans_path,
        "catalogs": {
            "transcripts": "api/transcripts/catalog.parquet",
            "scans": "api/scans/catalog.parquet",
        },
        "counts": counts,
    }
    await _write_json(output_dir / "scout-bundle.json", manifest)

    display().print(
        f"Bundle complete: {counts['transcripts']} transcripts, {counts['scans']} scans"
    )


def click_usage_error(message: str) -> Exception:
    """Build a Click usage error without importing Click at module top."""
    import click

    return click.UsageError(message)


# ---- helpers --------------------------------------------------------------


def _copy_dist(dist_dir: PathlibPath, output_dir: PathlibPath) -> None:
    """Copy dist contents into output_dir (merging at root, not nesting)."""
    for entry in dist_dir.iterdir():
        target = output_dir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target)
        else:
            shutil.copy2(entry, target)


def _inject_bundle_context(
    index_path: PathlibPath,
    transcripts_path: str | None,
    scans_path: str,
) -> None:
    """Inject a <script id='scout_context'> tag into the bundled index.html.

    The SPA's main.tsx detects this tag at boot and switches to static-bundle
    API mode.
    """
    html = index_path.read_text()
    context: dict[str, object] = {
        "bundle": True,
        "bundleBaseUrl": "./api",
        "transcriptsDir": transcripts_path,
        "scansDir": scans_path,
    }
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
    from typing import Any, Callable, cast

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


async def _write_project_config(path: PathlibPath) -> None:
    """Bake project config + frozen ETag in the shape the live endpoint returns.

    The live endpoint returns the ProjectConfig as the body and ETag in a
    header; the static endpoint returns `{config, etag}` since headers aren't
    available without a backend.
    """
    config, etag = read_project_config_with_etag()
    await _write_json(
        path,
        {"config": config.model_dump(), "etag": etag},
    )


def _build_topic_versions() -> dict[str, str]:
    """Bake a frozen snapshot of topic versions for the static bundle."""
    timestamp = datetime.now(timezone.utc).isoformat()
    # Match keys used by the live /topics endpoint.
    return {"project-config": timestamp, "scans": timestamp}


async def _write_json(path: PathlibPath, value: object) -> None:
    """Write a JSON-serializable value to disk using inspect's safe encoder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        to_json_safe(value)
        if not isinstance(value, (str, bytes))
        else (value.encode() if isinstance(value, str) else value)
    )
    path.write_bytes(payload)


def _write_parquet_catalog(
    path: PathlibPath,
    rows: list[dict[str, object]],
    *,
    empty_columns: list[str],
) -> None:
    """Write a Parquet metadata catalog for static DuckDB-WASM queries."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        table = pa.Table.from_pylist(rows)
    else:
        schema = pa.schema([(column, pa.string()) for column in empty_columns])
        table = pa.Table.from_pylist([], schema=schema)
    pq.write_table(table, path, compression="zstd")


def _bundle_id(value: str) -> str:
    """Return a stable filesystem-safe id for a bundle payload."""
    return (
        urlsafe_b64encode(sha256(value.encode("utf-8")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )


def _project_filter_conditions(project_filter: object) -> list["Condition"]:
    """Convert configured project filters to query conditions."""
    from .._query.condition_sql import condition_from_sql

    filters = project_filter if isinstance(project_filter, list) else [project_filter]
    return [condition_from_sql(f) for f in filters if isinstance(f, str) and f]


def _transcript_catalog_row(
    info: "TranscriptInfo",
    bundle_id: str,
    content_path: str,
) -> dict[str, object]:
    """Build one transcript catalog row with scalar query columns."""
    values = info.model_dump()
    row = _catalog_row(values, TRANSCRIPT_CATALOG_COLUMNS)
    for column in ("agent_args", "model_options", "score", "metadata"):
        row[column] = _json_cell(values.get(column))
    row["bundle_id"] = bundle_id
    row["content_path"] = content_path
    row["row_json"] = _json_text(values)
    return row


def _scan_catalog_row(
    scan: "ScanRow",
    bundle_id: str,
    *,
    static_path: str,
    status_path: str,
    scanner_paths: dict[str, str],
) -> dict[str, object]:
    """Build one scan catalog row with scalar query columns."""
    values = scan.model_dump()
    row = _catalog_row(values, SCAN_CATALOG_COLUMNS)
    for column in ("packages", "metadata", "scan_args"):
        row[column] = _json_cell(values.get(column))
    row["bundle_id"] = bundle_id
    row["static_path"] = static_path
    row["status_path"] = status_path
    row["scanner_paths_json"] = _json_text(scanner_paths)
    row["row_json"] = _json_text(values)
    return row


def _catalog_row(
    values: dict[str, object],
    columns: list[str],
) -> dict[str, object]:
    """Return catalog columns where complex values are compact JSON strings."""
    return {
        column: _catalog_cell(values.get(column)) if column in values else None
        for column in columns
    }


def _catalog_cell(value: object) -> object:
    """Convert values to Parquet cells that DuckDB can filter and sort."""
    if value is None or isinstance(value, str | int | float | bool):
        return value

    decoded = json.loads(to_json_safe(value))
    if decoded is None or isinstance(decoded, str | int | float | bool):
        return decoded
    return json.dumps(decoded, separators=(",", ":"), sort_keys=True)


def _json_cell(value: object) -> str | None:
    """Return compact JSON text for catalog columns that may mix JSON types."""
    if value is None:
        return None
    return json.dumps(json.loads(to_json_safe(value)), separators=(",", ":"))


def _json_text(value: object) -> str:
    """Serialize with Inspect's JSON encoder and return UTF-8 text."""
    return to_json_safe(value).decode("utf-8")


async def _bundle_transcripts(
    transcripts_dir: str,
    api_dir: PathlibPath,
    project_filter: object,
) -> int:
    """Pre-bake transcript catalog and compressed content payloads.

    The catalog is queryable by DuckDB-WASM in the browser. Large transcript
    message/event payloads stay out of the catalog and are written as zstd
    files that the static client fetches only when a transcript is opened.

    Returns the number of transcripts written.
    """
    from .._query import Query
    from .._transcript.database.factory import transcripts_view

    target = api_dir / "transcripts"
    content_dir = target / "content"
    target.mkdir(parents=True, exist_ok=True)
    content_dir.mkdir(parents=True, exist_ok=True)
    filters = _project_filter_conditions(project_filter)

    try:
        async with transcripts_view(transcripts_dir) as view:
            infos = [info async for info in view.select(Query(where=filters))]
            rows: list[dict[str, object]] = []
            for info in infos:
                bundle_id = _bundle_id(info.transcript_id)
                content_path = f"transcripts/content/{bundle_id}.json.zst"
                rows.append(_transcript_catalog_row(info, bundle_id, content_path))
                await _write_transcript_content_zstd(
                    view,
                    info,
                    target / "content" / f"{bundle_id}.json.zst",
                )
            _write_parquet_catalog(
                target / "catalog.parquet",
                rows,
                empty_columns=TRANSCRIPT_CATALOG_COLUMNS,
            )
    except FileNotFoundError:
        _write_parquet_catalog(
            target / "catalog.parquet",
            [],
            empty_columns=TRANSCRIPT_CATALOG_COLUMNS,
        )
        return 0

    return len(infos)


async def _write_transcript_content_zstd(
    view: "TranscriptsView",
    info: "TranscriptInfo",
    path: PathlibPath,
) -> None:
    """Write a transcript's messages/events stream as a zstd JSON payload."""
    import zlib

    import zstandard
    from inspect_ai._util.zip_common import ZipCompressionMethod

    result = await view.read_messages_events(info)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as out:
        if result.compression_method == ZipCompressionMethod.ZSTD:
            async with result.data as data:
                async for chunk in data:
                    out.write(chunk)
            return

        compressor = zstandard.ZstdCompressor()
        with compressor.stream_writer(out, closefd=False) as writer:
            if (
                result.compression_method is None
                or result.compression_method == ZipCompressionMethod.STORED
            ):
                async with result.data as data:
                    async for chunk in data:
                        writer.write(chunk)
                return

            if result.compression_method == ZipCompressionMethod.DEFLATE:
                decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
                async with result.data as data:
                    async for chunk in data:
                        decoded = decompressor.decompress(chunk)
                        if decoded:
                            writer.write(decoded)
                tail = decompressor.flush()
                if tail:
                    writer.write(tail)
                return

    raise ValueError(f"Unsupported compression method: {result.compression_method}")


async def _bundle_scans(
    scans_dir: str,
    api_dir: PathlibPath,
) -> int:
    """Pre-bake scan catalog, status snapshots, and scanner Parquet files.

    Returns the number of scans written.
    """
    from upath import UPath

    from .._query import Query
    from .._scanjobs.duckdb import scan_jobs_view
    from .._scanresults import scan_results_arrow_async, scan_results_df_async

    target = api_dir / "scans"
    target.mkdir(parents=True, exist_ok=True)
    data_dir = target / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with await scan_jobs_view(scans_dir) as view:
            rows = [row async for row in view.select(Query())]
    except Exception:
        # Scans dir missing or unreadable — emit an empty catalog and bail.
        _write_parquet_catalog(
            target / "catalog.parquet",
            [],
            empty_columns=SCAN_CATALOG_COLUMNS,
        )
        return 0

    catalog_rows: list[dict[str, object]] = []
    scans_base = UPath(scans_dir)
    for row in rows:
        scan_path_abs = UPath(row.location)
        try:
            scan_rel = str(scan_path_abs.relative_to(scans_base))
        except ValueError:
            scan_rel = scan_path_abs.name
        bundle_id = _bundle_id(row.location)
        scan_target = data_dir / bundle_id
        scan_target.mkdir(parents=True, exist_ok=True)

        # status.json — mirror the live GET /scans/{dir}/{scan} JSON shape.
        status = await scan_results_df_async(row.location, rows="transcripts")
        if status.spec.transcripts:
            status.spec.transcripts = status.spec.transcripts.model_copy(
                update={"data": None}
            )
        await _write_json(scan_target / "status.json", status)

        arrow = await scan_results_arrow_async(row.location)
        scanners_dir = scan_target / "scanners"
        scanners_dir.mkdir(exist_ok=True)
        scanner_paths: dict[str, str] = {}

        for scanner in arrow.scanners:
            rel_path = f"scans/data/{bundle_id}/scanners/{scanner}.parquet"
            _copy_scanner_parquet(
                UPath(row.location) / f"{scanner}.parquet",
                scanners_dir / f"{scanner}.parquet",
            )
            scanner_paths[scanner] = rel_path

        catalog_rows.append(
            _scan_catalog_row(
                row,
                bundle_id,
                static_path=scan_rel,
                status_path=f"scans/data/{bundle_id}/status.json",
                scanner_paths=scanner_paths,
            )
        )

    _write_parquet_catalog(
        target / "catalog.parquet",
        catalog_rows,
        empty_columns=SCAN_CATALOG_COLUMNS,
    )

    return len(rows)


def _copy_scanner_parquet(source: UPath, target: PathlibPath) -> None:
    """Copy a scanner parquet file without materializing it as Arrow/JSON."""
    from inspect_ai._util.file import file as fs_open

    target.parent.mkdir(parents=True, exist_ok=True)
    with fs_open(source.as_posix(), "rb") as src, target.open("wb") as dst:
        shutil.copyfileobj(src, dst)
