"""Project configuration types."""

from pydantic import ConfigDict, Field

from inspect_scout._scanjob_config import ScanJobConfig


class ProjectConfig(ScanJobConfig):
    """Scout project configuration from scout.yaml.

    Extends ScanJobConfig to represent project-level defaults. All fields
    from ScanJobConfig are available as project defaults.
    """

    trust_content: bool | None = Field(default=None)
    """Whether `scout view` may render model output richly (markdown, syntax highlighting, ANSI colors, media, links).

    `False` shows all model output as plain text, whatever each transcript's own setting. `None` (the default) and `True` defer to each transcript. Configures the viewer only; scans ignore it.
    """

    model_config = ConfigDict(extra="forbid", protected_namespaces=())
