from rich.progress import (
    ProgressColumn,
    Task,
)
from rich.text import Text

from ._concurrency.common import ScanMetrics


class UtilizationColumn(ProgressColumn):
    """Progress column showing worker utilization (active/max)."""

    def render(self, task: Task) -> Text:
        metrics: ScanMetrics | None = task.fields.get("metrics")
        if metrics is None:
            return Text("0/0/0/0 (0)", style="cyan")
        return Text(
            f"{metrics.process_count}/{metrics.tasks_parsing}/{metrics.tasks_scanning}/{metrics.tasks_waiting} ({metrics.buffered_scanner_jobs})",
            style="cyan",
        )
