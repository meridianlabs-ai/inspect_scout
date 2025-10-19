from inspect_ai._util._async import run_coroutine

from ._recorder.factory import scan_recorder_type_for_location
from ._recorder.recorder import (
    ScanResults,
    ScanResultsDB,
    ScanStatus,
)


def scan_status(scan_location: str) -> ScanStatus:
    """Status of scan.

    Args:
        scan_location: Location to get status for (e.g. directory or s3 bucket)

    Returns:
        ScanStatus: Status of scan (spec, summary, errors, etc.)
    """
    return run_coroutine(scan_status_async(scan_location))


async def scan_status_async(scan_location: str) -> ScanStatus:
    """Status of scan.

    Args:
        scan_location: Location to get status for (e.g. directory or s3 bucket)

    Returns:
        ScanStatus: Status of scan (spec, summary, errors, etc.)
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.status(scan_location)


def scan_results(
    scan_location: str, *, scanner: str | None = None, include_null: bool = False
) -> ScanResults:
    """Scan results as Pandas data frames.

    Args:
         scan_location: Location of scan (e.g. directory or s3 bucket).
         scanner: Scanner name (defaults to all scanners).
         include_null: Should `None` results be included in the data frame (defaults to `False`)

    Returns:
         ScanResults: Results as pandas data frames.
    """
    return run_coroutine(
        scan_results_async(scan_location, scanner=scanner, include_null=include_null)
    )


async def scan_results_async(
    scan_location: str, *, scanner: str | None = None, include_null: bool = False
) -> ScanResults:
    """Scan results as Pandas data frames.

    Args:
         scan_location: Location of scan (e.g. directory or s3 bucket).
         scanner: Scanner name (defaults to all scanners).
         include_null: Should `None` results be included in the data frame (defaults to `False`)

    Returns:
         ScanResults: Results as Pandas data frames.
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results(
        scan_location, scanner=scanner, include_null=include_null
    )


def scan_results_db(scan_location: str, include_null: bool = False) -> ScanResultsDB:
    """Scan results as DuckDB database.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).
        include_null: Should `None` results be included in the data frame (defaults to `False`)

    Returns:
        ScanResultsDB: Results as DuckDB database.
    """
    return run_coroutine(scan_results_db_async(scan_location, include_null))


async def scan_results_db_async(
    scan_location: str, include_null: bool = False
) -> ScanResultsDB:
    """Scan results as DuckDB database.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).
        include_null: Should `None` results be included in the data frame (defaults to `False`)

    Returns:
        ScanResultsDB: Results as DuckDB database.
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results_db(scan_location, include_null=include_null)
