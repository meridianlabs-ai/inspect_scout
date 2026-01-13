from dataclasses import dataclass, field

from inspect_scout._project.types import ProjectConfig


@dataclass
class ViewConfig:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    transcripts: str | None = field(default=None)
    scans: str | None = field(default=None)
