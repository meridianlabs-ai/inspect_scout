"""Typed metadata interface for Inspect log transcripts.

This module provides a typed subclass of Metadata that offers IDE support
and documentation for standard Inspect log fields.
"""

from logging import getLogger

from inspect_ai._util.logger import warn_once

from .columns import Column, Columns

logger = getLogger(__name__)


class LogColumns(Columns):
    """Typed column interface for Inspect log transcripts.

    Provides typed properties for standard Inspect log columns while
    preserving the ability to access custom fields through the base
    Metadata class methods.

    Usage:
        from inspect_scout import log_columns as c

        # Typed access to standard fields
        filter = c.model == "gpt-4"
        filter = (c.task_set == "math") & (c.epochs > 1)

        # Dynamic access to custom fields
        filter = c["custom_field"] > 100
    """

    # ===== ID columns =====

    @property
    def sample_id(self) -> Column:
        """Unique id for sample."""
        return Column("sample_id")

    @property
    def eval_id(self) -> Column:
        """Globally unique id for eval."""
        return Column("eval_id")

    @property
    def eval_status(self) -> Column:
        """Status of eval."""
        return Column("eval_status")

    @property
    def log(self) -> Column:
        """Location that the log file was read from."""
        return Column("log")

    # ===== Eval Info columns =====

    @property
    def eval_tags(self) -> Column:
        """Tags associated with evaluation run."""
        return Column("eval_tags")

    @property
    def eval_metadata(self) -> Column:
        """Additional eval metadata."""
        return Column("eval_metadata")

    # ===== Eval Task columns =====

    @property
    def task_args(self) -> Column:
        """Task arguments."""
        return Column("task_args")

    # ===== Eval Model columns =====

    @property
    def generate_config(self) -> Column:
        """Generate config specified for model instance."""
        return Column("generate_config")

    @property
    def model_roles(self) -> Column:
        """Model roles."""
        return Column("model_roles")

    # ===== Sample columns =====

    @property
    def id(self) -> Column:
        """Unique id for sample."""
        return Column("id")

    @property
    def epoch(self) -> Column:
        """Epoch number for sample."""
        return Column("epoch")

    @property
    def input(self) -> Column:
        """Sample input."""
        return Column("input")

    @property
    def target(self) -> Column:
        """Sample target."""
        return Column("target")

    @property
    def sample_metadata(self) -> Column:
        """Sample metadata."""
        return Column("sample_metadata")

    @property
    def working_time(self) -> Column:
        """Time spent working (model generation, sandbox calls, etc.)."""
        return Column("working_time")

    # ===== Deprecated columns =====

    @property
    def eval_created(self) -> Column:
        """Time eval was created (deprecated, use 'date' instead)."""
        warn_once(logger, "'eval_created' is deprecated, use 'date' instead")
        return self.date

    @property
    def task_name(self) -> Column:
        """Task name (deprecated, use 'task' instead)."""
        warn_once(logger, "'task_name' is deprecated, use 'task_set' instead")
        return self.task_set

    @property
    def solver(self) -> Column:
        """Solver name (deprecated, use 'agent' instead)."""
        warn_once(logger, "'solver' is deprecated, use 'agent' instead")
        return self.agent

    @property
    def solver_args(self) -> Column:
        """Arguments used for invoking the solver (deprecated, use 'agent_args' instead)."""
        warn_once(logger, "'solver_args' is deprecated, use 'agent_args' instead")
        return self.agent_args


log_columns = LogColumns()
"""Log columns selector for where expressions.

Typically aliased to a more compact expression (e.g. `c`)
for use in queries). For example:

```python
from inspect_scout import log_columns as c

# typed access to standard fields
filter = c.model == "gpt-4"
filter = (c.task_set == "math") & (c.epochs > 1)

# dynamic access to custom fields
filter = c["custom_field"] > 100
```
"""
