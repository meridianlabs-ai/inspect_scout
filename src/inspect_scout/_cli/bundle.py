"""scout view bundle: produce a static directory bundle of a project's view."""

from logging import getLogger
from pathlib import Path
from typing import Any

import anyio
import click
from typing_extensions import Unpack

from inspect_scout._cli.common import (
    CommonOptions,
    common_options,
    process_common_options,
)

from .._scan import top_level_async_init
from .._view._bundle import DEFAULT_SHARD_SIZE, bundle_view
from .._view.types import ViewConfig

logger = getLogger(__name__)


@click.command("bundle")
@click.argument("project_dir", required=False, default=None)
@click.option(
    "-T",
    "--transcripts",
    type=str,
    default=None,
    help="Location of transcripts to bundle.",
)
@click.option(
    "--scans",
    type=str,
    default=None,
    help="Location of scan results to bundle.",
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="Output directory for the static bundle.",
)
@click.option(
    "--shard-size",
    type=int,
    default=DEFAULT_SHARD_SIZE,
    help="Rows per catalog shard.",
)
@click.option(
    "--max-details",
    type=int,
    default=None,
    help=(
        "Maximum number of scanner detail rows to pre-bake per scanner. "
        "Detail blobs can dominate bundle size for large scans; omit to bake all."
    ),
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite the output directory if it already exists.",
)
@common_options
@click.pass_context
def bundle_command(
    ctx: click.Context,
    project_dir: str | None,
    transcripts: str | None,
    scans: str | None,
    output_dir: Path,
    shard_size: int,
    max_details: int | None,
    force: bool,
    **common: Unpack[CommonOptions],
) -> None:
    """Bundle a project view as a static directory that can be hosted anywhere.

    The bundle contains the frontend SPA plus pre-baked JSON/Arrow files
    representing the project's transcripts and scans. It can be deployed to
    any static host (S3, GitHub Pages, nginx) without the scout backend.
    """
    from inspect_ai._util.path import chdir

    # resolve the output dir before chdir so a relative -o is relative to
    # the invocation directory, not the project dir
    output_dir = output_dir.resolve()

    with chdir(project_dir or "."):
        process_common_options(ctx, common, init_logging=False)

        from inspect_scout._project._project import read_project

        project = read_project()
        top_level_async_init(common["log_level"])

        config = ViewConfig(
            project=project,
            transcripts_cli=transcripts,
            scans_cli=scans,
        )

        anyio.run(_run_bundle, config, output_dir, shard_size, max_details, force)


async def _run_bundle(
    config: ViewConfig,
    output_dir: Path,
    shard_size: int,
    max_details: int | None,
    force: bool,
) -> Any:
    await bundle_view(
        config=config,
        output_dir=output_dir,
        shard_size=shard_size,
        max_details=max_details,
        force=force,
    )
