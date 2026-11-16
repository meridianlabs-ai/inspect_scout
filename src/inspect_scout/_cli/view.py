from logging import getLogger
from typing import Literal

import click
from inspect_ai._util.path import chdir
from typing_extensions import Unpack

from inspect_scout._cli.common import (
    CommonOptions,
    common_options,
    process_common_options,
    resolve_view_authorization,
    view_options,
)

from .._view.view import view

logger = getLogger(__name__)


@click.command("view")
@click.argument("project_dir", required=False, default=None)
@click.option(
    "-T",
    "--transcripts",
    type=str,
    default=None,
    help="Location of transcripts to view.",
)
@click.option(
    "--scans",
    type=str,
    default=None,
    help="Location of scan results to view.",
)
@click.option(
    "--trust-content/--no-trust-content",
    default=None,
    envvar="SCOUT_VIEW_TRUST_CONTENT",
    help="Whether model output may be rendered richly (markdown, syntax highlighting, "
    "ANSI colors, media, links). --no-trust-content shows all model output as plain "
    "text, whatever the project or each transcript's own setting. --trust-content, "
    "like leaving the option unset, defers to them; it never shows untrusted content "
    "richly.",
)
@click.option(
    "--mode",
    type=click.Choice(("default", "scans")),
    default="default",
    help="View display mode.",
)
@view_options
@common_options
@click.pass_context
def view_command(
    ctx: click.Context,
    project_dir: str | None,
    transcripts: str | None,
    scans: str | None,
    trust_content: bool | None,
    mode: Literal["default", "scans"],
    host: str,
    port: int,
    browser: bool | None,
    root_path: str,
    **common: Unpack[CommonOptions],
) -> None:
    """View scan results."""
    # chdir to correctly resolve log level based on the relevant project_dir
    with chdir(project_dir or "."):
        process_common_options(ctx, common, init_logging=False)

    view(
        project_dir=project_dir,
        transcripts=transcripts,
        scans=scans,
        trust_content=trust_content,
        host=host,
        port=port,
        browser=browser is True,
        mode=mode,
        authorization=resolve_view_authorization(),
        log_level=common["log_level"],
        root_path=root_path,
    )
