"""scout bundle: produce a static directory bundle of a project's view."""

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
from .._view._bundle import bundle_view
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
    "--max-details",
    type=int,
    default=None,
    help=(
        "Deprecated; ignored by static bundle v2 because scanner details "
        "are read from Parquet on demand."
    ),
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite the output directory if it already exists.",
)
@common_options
def bundle_command(
    project_dir: str | None,
    transcripts: str | None,
    scans: str | None,
    output_dir: Path,
    max_details: int | None,
    force: bool,
    **common: Unpack[CommonOptions],
) -> None:
    """Bundle a project view as a static directory that can be hosted anywhere.

    The bundle contains the frontend SPA plus Parquet catalogs and static data
    files representing the project's transcripts and scans. It
    can be deployed to any static host with HTTP range request support.
    """
    process_common_options(common)
    from inspect_ai._util.path import chdir

    with chdir(project_dir or "."):
        from inspect_scout._project._project import read_project

        project = read_project()
        top_level_async_init(common["log_level"])

        config = ViewConfig(
            project=project,
            transcripts_cli=transcripts,
            scans_cli=scans,
        )

        anyio.run(
            _run_bundle, config, output_dir, max_details, force
        )


async def _run_bundle(
    config: ViewConfig,
    output_dir: Path,
    max_details: int | None,
    force: bool,
) -> Any:
    await bundle_view(
        config=config,
        output_dir=output_dir,
        max_details=max_details,
        force=force,
    )
