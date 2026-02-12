"""Conversion helpers for scan job types."""

from .._recorder.active_scans_store import ActiveScanInfo
from .._recorder.recorder import Status as RecorderStatus
from .._view._api_v2_types import ScanRow


def scan_row_from_status(
    status: RecorderStatus,
    active_scan_info: ActiveScanInfo | None = None,
) -> ScanRow:
    """Create a ScanRow from a Status object."""
    spec = status.spec

    # Aggregate summary fields
    total_results = 0
    total_errors = 0
    total_tokens = 0
    for scanner_summary in status.summary.scanners.values():
        total_results += scanner_summary.results
        total_errors += scanner_summary.errors
        total_tokens += scanner_summary.tokens

    return ScanRow(
        # Extracted fields
        scan_id=spec.scan_id,
        scan_name=spec.scan_name,
        scan_file=spec.scan_file,
        timestamp=spec.timestamp,
        packages=spec.packages,
        metadata=spec.metadata,
        scan_args=spec.scan_args,
        location=status.location,
        # Computed fields
        status=(
            "active"
            if active_scan_info
            else "error"
            if status.errors
            else "complete"
            if status.complete
            else "incomplete"
        ),
        scanners=",".join(spec.scanners.keys()) if spec.scanners else "",
        model=(
            getattr(spec.model, "model", None) or str(spec.model)
            if spec.model
            else None
        ),
        tags=",".join(spec.tags) if spec.tags else "",
        revision_version=spec.revision.version if spec.revision else None,
        revision_commit=spec.revision.commit if spec.revision else None,
        revision_origin=spec.revision.origin if spec.revision else None,
        total_results=total_results,
        total_errors=total_errors,
        total_tokens=total_tokens,
        active_completion_pct=(
            None
            if active_scan_info is None
            else 0
            if active_scan_info.total_scans == 0
            else round(
                active_scan_info.metrics.completed_scans
                / active_scan_info.total_scans
                * 100
            )
        ),
        transcript_count=len(spec.transcripts.transcript_ids)
        if spec.transcripts is not None
        else 0,
    )
