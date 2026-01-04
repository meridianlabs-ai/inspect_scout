"""Factory functions for creating ScanJobsView instances."""

from .._recorder.file import FileRecorder
from .duckdb import DuckDBScanJobsView
from .view import ScanJobsView


async def scan_jobs_view(scans_location: str) -> ScanJobsView:
    """Create a ScanJobsView for the given scans location.

    Args:
        scans_location: Path to directory containing scan jobs.

    Returns:
        ScanJobsView instance for querying scan jobs.
    """
    # Load all Status objects from the scans location
    statuses = await FileRecorder.list(scans_location)

    # Create and return the DuckDB view
    return DuckDBScanJobsView(statuses)
