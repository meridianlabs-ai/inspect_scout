"""Scout project configuration system.

Provides project-level defaults via scout.yaml files that are merged with
individual scan job configurations. Local overrides can be provided via
scout.local.yaml files (not checked into version control).
"""

from ._project import (
    create_default_project,
    find_git_root,
    find_local_project_file,
    find_project_file,
    init_project,
    load_project_config,
    project,
)
from .merge import merge_configs
from .types import ProjectConfig

__all__ = [
    "ProjectConfig",
    "init_project",
    "project",
    "merge_configs",
    "find_git_root",
    "find_project_file",
    "find_local_project_file",
    "load_project_config",
    "create_default_project",
]
