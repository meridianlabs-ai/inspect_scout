"""Static bundle generator: materializes a scout project view as a directory."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
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
    from .._recorder.recorder import ScanResultsArrow
    from .._transcript.database.database import TranscriptsView
    from .._transcript.types import TranscriptInfo

BUNDLE_VERSION = 1
SCOUT_CONTEXT_PLACEHOLDER = "</head>"


async def bundle_view(
    config: ViewConfig,
    output_dir: PathlibPath,
    max_details: int | None = None,
    force: bool = False,
) -> None:
    """Materialize a static bundle of the given project view into ``output_dir``.

    The output directory will contain:
    - The frontend SPA (copied from the resolved dist directory)
    - An ``api/`` subdirectory with pre-baked JSON / Arrow / zstd payloads
    - A ``scout-bundle.json`` manifest

    Args:
        config: View configuration (project + optional CLI dir overrides).
        output_dir: Where to write the bundle. Created if missing.
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
        )
    else:
        counts["transcripts"] = 0

    # 5. Bake scans.
    counts["scans"] = await _bundle_scans(
        scans_dir=scans_path,
        api_dir=api_dir,
        max_details=max_details,
    )

    # 6. Bake validations.
    counts["validations"] = await _bundle_validations(api_dir=api_dir)

    # 7. Write bundle manifest.
    manifest = {
        "version": BUNDLE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "transcripts_dir": transcripts_path,
        "scans_dir": scans_path,
        "counts": counts,
    }
    await _write_json(output_dir / "scout-bundle.json", manifest)

    display().print(
        f"Bundle complete: {counts['transcripts']} transcripts, "
        f"{counts['scans']} scans, {counts['validations']} validation sets"
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
    script = (
        '<script id="scout_context" type="application/json">'
        f"{json.dumps(context)}"
        "</script>\n"
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


# ---- placeholders for follow-up commits -----------------------------------


async def _bundle_transcripts(
    transcripts_dir: str,
    api_dir: PathlibPath,
) -> int:
    """Pre-bake transcripts (listing + per-id info + messages-events).

    Listing matches TranscriptsResponse shape; per-id payloads sit under
    ``transcripts/<id>/`` mirroring the live endpoint paths. messages-events
    bytes are decompressed at bundle time so the static client only needs
    a plain ``fetch().json()`` to read them.

    Returns the number of transcripts written.
    """
    from .._query import Query
    from .._transcript.database.factory import transcripts_view

    target = api_dir / "transcripts"
    target.mkdir(parents=True, exist_ok=True)

    try:
        async with transcripts_view(transcripts_dir) as view:
            infos = [info async for info in view.select(Query())]
            total = await view.count(Query())

            # Listing matches the TranscriptsResponse shape returned by the
            # live POST /transcripts/{dir} endpoint.
            await _write_json(
                target / "listing.json",
                {
                    "items": [info.model_dump() for info in infos],
                    "total_count": total,
                    "next_cursor": None,
                },
            )

            for info in infos:
                await _write_transcript_payload(view, info, target)
    except FileNotFoundError:
        await _write_json(
            target / "listing.json",
            {"items": [], "total_count": 0, "next_cursor": None},
        )
        return 0

    return len(infos)


async def _write_transcript_payload(
    view: "TranscriptsView",
    info: "TranscriptInfo",
    target: PathlibPath,
) -> None:
    """Write info.json + decoded messages-events.json for a single transcript."""
    # Slashes are valid in transcript_id strings — make a filesystem-safe dir.
    safe_id = info.transcript_id.replace("/", "_").replace("\\", "_")
    transcript_dir = target / safe_id
    transcript_dir.mkdir(parents=True, exist_ok=True)

    await _write_json(transcript_dir / "info.json", info.model_dump())

    result = await view.read_messages_events(info)
    raw_chunks: list[bytes] = []
    async with result.data as data:
        async for chunk in data:
            raw_chunks.append(chunk)
    raw = b"".join(raw_chunks)

    decoded = _decompress_payload(raw, result.compression_method)
    (transcript_dir / "messages-events.json").write_bytes(decoded)


def _decompress_payload(
    raw: bytes,
    compression: object,
) -> bytes:
    """Decompress raw transcript bytes to plain UTF-8 JSON."""
    from inspect_ai._util.zip_common import ZipCompressionMethod

    if compression is None or compression == ZipCompressionMethod.STORED:
        return raw
    if compression == ZipCompressionMethod.ZSTD:
        import zstandard

        # Use streaming API — server-emitted zstd frames omit the content
        # size in the header, so the one-shot .decompress() can't size the
        # output buffer.
        return zstandard.ZstdDecompressor().stream_reader(raw).read()
    if compression == ZipCompressionMethod.DEFLATE:
        import zlib

        # ZIP DEFLATE is raw (RFC 1951), not zlib-wrapped (RFC 1950).
        return zlib.decompress(raw, -zlib.MAX_WBITS)
    raise ValueError(f"Unsupported compression method: {compression}")


async def _bundle_scans(
    scans_dir: str,
    api_dir: PathlibPath,
    max_details: int | None,
) -> int:
    """Pre-bake scans (listing + per-scan status, dataframes, details, archive).

    Returns the number of scans written.
    """
    from upath import UPath

    from .._query import Query
    from .._scanjobs.duckdb import scan_jobs_view
    from .._scanresults import scan_results_arrow_async, scan_results_df_async

    target = api_dir / "scans"
    target.mkdir(parents=True, exist_ok=True)

    try:
        async with await scan_jobs_view(scans_dir) as view:
            rows = [row async for row in view.select(Query())]
            total = await view.count(Query())
    except Exception:
        # Scans dir missing or unreadable — emit empty listing and bail.
        await _write_json(
            target / "listing.json",
            {"items": [], "total_count": 0, "next_cursor": None},
        )
        return 0

    await _write_json(
        target / "listing.json",
        {
            "items": [row.model_dump() for row in rows],
            "total_count": total,
            "next_cursor": None,
        },
    )

    scans_base = UPath(scans_dir)
    for row in rows:
        scan_path_abs = UPath(row.location)
        try:
            scan_rel = str(scan_path_abs.relative_to(scans_base))
        except ValueError:
            scan_rel = scan_path_abs.name
        scan_target = target / scan_rel
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
        details_dir = scan_target / "details"

        for scanner in arrow.scanners:
            _write_scanner_dataframe(arrow, scanner, scanners_dir / f"{scanner}.arrow")
            _write_scanner_details(
                arrow,
                scanner,
                details_dir / scanner,
                max_details=max_details,
            )

        _build_scan_archive_zip(scan_path_abs, scan_target / "archive.zip")

    return len(rows)


def _write_scanner_dataframe(
    arrow: "ScanResultsArrow",
    scanner: str,
    out_path: PathlibPath,
) -> None:
    """Serialize a scanner's Arrow record batches to an IPC stream file.

    Mirrors the live /scans/{dir}/{scan}/{scanner} endpoint (LZ4 compression).
    """
    import io

    import pyarrow.ipc as pa_ipc

    buf = io.BytesIO()
    with arrow.reader(scanner) as reader:
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
    """Bake per-row detail JSON blobs containing the columns the UI fetches."""
    from .._transcript.eval_log import JSON_COLUMNS

    out_dir.mkdir(parents=True, exist_ok=True)
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
                _write_detail_blob(out_dir / f"{uuid}.json", fields, json_cols)
                written += 1


def _write_detail_blob(
    path: PathlibPath,
    fields: dict[str, object],
    json_cols: frozenset[str],
) -> None:
    """Write a detail blob, preserving pre-serialized JSON columns verbatim.

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

    path.write_text("{" + ",".join(parts) + "}")


def _build_scan_archive_zip(scan_path: object, out_path: PathlibPath) -> None:
    """Zip all files in the scan directory into a single archive.

    Mirrors the live GET /scans/{dir}/{scan} Accept: application/zip handler.
    """
    import io
    import zipfile

    from inspect_ai._util.file import file as fs_open

    # scan_path is a UPath but we only use the universal interface here.
    if not scan_path.exists():  # type: ignore[attr-defined]
        return

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for child in scan_path.iterdir():  # type: ignore[attr-defined]
            if child.is_file():
                with fs_open(child.as_posix(), "rb") as f:
                    zf.writestr(child.name, f.read())
    out_path.write_bytes(buf.getvalue())


async def _bundle_validations(api_dir: PathlibPath) -> int:
    """Pre-bake validation sets (sets list + per-set cases).

    Discovers .csv/.yaml/.json/.jsonl validation files in the current
    project directory and emits them under api/validations/. The static
    client base64-url-encodes the URI to look up per-set cases.

    Returns the number of validation sets written.
    """
    import base64

    from .._validation.file_scanner import scan_validation_files
    from .._validation.writer import ValidationFileWriter, _unflatten_columns

    target = api_dir / "validations"
    target.mkdir(parents=True, exist_ok=True)

    uris: list[str] = []
    project_dir = PathlibPath.cwd().resolve()
    for file_path in scan_validation_files(project_dir):
        try:
            uri = UPath(file_path).resolve().as_uri()
        except Exception:
            continue
        uris.append(uri)

        try:
            writer = ValidationFileWriter(file_path)
            cases = _unflatten_columns(writer.read_cases())
        except FileNotFoundError:
            continue

        encoded = (
            base64.urlsafe_b64encode(uri.encode()).rstrip(b"=").decode()
        )
        await _write_json(target / encoded / "cases.json", cases)

    await _write_json(target / "sets.json", uris)
    return len(uris)
