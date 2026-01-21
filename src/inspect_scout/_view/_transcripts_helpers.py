from .._project._project import (
    read_project,
)
from .._query import Condition
from .._query.condition_sql import condition_from_sql


def get_project_filters() -> list[Condition]:
    project = read_project()
    return [
        condition_from_sql(f)
        for f in (
            project.filter if isinstance(project.filter, list) else [project.filter]
        )
        if f
    ]
