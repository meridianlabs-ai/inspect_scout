"""Column definitions for transcript filtering.

This module re-exports the query DSL from _query and provides
transcript-specific column definitions.

Usage:
    from inspect_scout import columns as c

    # Simple conditions
    filter = c.model == "gpt-4"
    filter = c["custom_field"] > 100

    # Combined conditions
    filter = (c.model == "gpt-4") & (c.score > 0.8)
    filter = (c.status == "error") | (c.retries > 3)

    # Generate SQL
    sql, params = filter.to_sql("sqlite")  # or "duckdb" or "postgres"
"""

from inspect_scout._query import (
    Column,
    LogicalOperator,
    Operator,
    ScalarValue,
    SQLDialect,
)
from inspect_scout._query.condition import Condition

# Re-export for backwards compatibility
__all__ = [
    "Column",
    "Columns",
    "Condition",
    "LogicalOperator",
    "Operator",
    "ScalarValue",
    "SQLDialect",
    "columns",
]


class Columns:
    """Entry point for building filter expressions.

    Supports both dot notation and bracket notation for accessing columns:

    ```python
    from inspect_scout import columns as c

    c.column_name
    c["column_name"]
    c["nested.json.path"]
    ```
    """

    @property
    def transcript_id(self) -> Column:
        """Globally unique identifier for transcript."""
        return Column("transcript_id")

    @property
    def source_type(self) -> Column:
        """Type of transcript source (e.g. "eval_log", "weave", etc.)."""
        return Column("source_type")

    @property
    def source_id(self) -> Column:
        """Globally unique identifier of transcript source (e.g. 'eval_id' in Inspect logs)."""
        return Column("source_id")

    @property
    def source_uri(self) -> Column:
        """URI for source data (e.g. full path to the Inspect log file or weave op)."""
        return Column("source_uri")

    @property
    def date(self) -> Column:
        """Date transcript was created."""
        return Column("date")

    @property
    def task_set(self) -> Column:
        """Set from which transcript task was drawn (e.g. benchmark name)."""
        return Column("task_set")

    @property
    def task_id(self) -> Column:
        """Identifier for task (e.g. dataset sample id)."""
        return Column("task_id")

    @property
    def task_repeat(self) -> Column:
        """Repeat for a given task id within a task set (e.g. epoch)."""
        return Column("task_repeat")

    @property
    def agent(self) -> Column:
        """Agent name."""
        return Column("agent")

    @property
    def agent_args(self) -> Column:
        """Agent args."""
        return Column("agent_args")

    @property
    def model(self) -> Column:
        """Model used for eval."""
        return Column("model")

    @property
    def model_options(self) -> Column:
        """Generation options for model."""
        return Column("model_options")

    @property
    def score(self) -> Column:
        """Headline score value."""
        return Column("score")

    @property
    def success(self) -> Column:
        """Reduction of 'score' to True/False sucess."""
        return Column("success")

    @property
    def total_time(self) -> Column:
        """Total execution time."""
        return Column("total_time")

    @property
    def error(self) -> Column:
        """Error that halted exeuction."""
        return Column("error")

    @property
    def limit(self) -> Column:
        """Limit that halted execution."""
        return Column("limit")

    def __getattr__(self, name: str) -> Column:
        """Access columns using dot notation."""
        if name.startswith("_"):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )
        return Column(name)

    def __getitem__(self, name: str) -> Column:
        """Access columns using bracket notation."""
        return Column(name)


columns = Columns()
"""Column selector for where expressions.

Typically aliased to a more compact expression (e.g. `c`)
for use in queries). For example:

```python
from inspect_scout import columns as c
filter = c.model == "gpt-4"
filter = (c.task_set == "math") & (c.epochs > 1)
```
"""
