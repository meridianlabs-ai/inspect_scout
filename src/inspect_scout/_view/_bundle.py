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
    """Pre-bake scans (listing, distinct, per-scan payloads).

    Returns the number of scans written. Implemented in a follow-up commit.
    """
    target = api_dir / "scans"
    target.mkdir(parents=True, exist_ok=True)
    await _write_json(
        target / "listing.json",
        {"items": [], "total_count": 0, "next_cursor": None},
    )
    return 0


async def _bundle_validations(api_dir: PathlibPath) -> int:
    """Pre-bake validation sets (sets list + per-set cases).

    Returns the number of validation sets written. Implemented in a follow-up
    commit; for the scaffold we emit an empty sets file.
    """
    target = api_dir / "validations"
    target.mkdir(parents=True, exist_ok=True)
    await _write_json(target / "sets.json", [])
    return 0
