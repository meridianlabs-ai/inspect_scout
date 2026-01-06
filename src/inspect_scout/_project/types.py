"""Project configuration types."""

from pydantic import ConfigDict

from inspect_scout._scanjob_config import ScanJobConfig


class ProjectConfig(ScanJobConfig):
    """Scout project configuration from scout.yaml.

    Extends ScanJobConfig to represent project-level defaults. All fields
    from ScanJobConfig are available as project defaults.
    """

    model_config = ConfigDict(extra="forbid", protected_namespaces=())
