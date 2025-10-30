from inspect_ai._util._async import run_coroutine
from upath import UPath

from ._recorder.factory import scan_recorder_type_for_location
from ._recorder.recorder import (
    Results,
    ResultsDB,
    Status,
)


def scan_status(scan_location: str) -> Status:
    """Status of scan.

    Args:
        scan_location: Location to get status for (e.g. directory or s3 bucket)

    Returns:
        ScanStatus: Status of scan (spec, summary, errors, etc.)
    """
    return run_coroutine(scan_status_async(scan_location))


async def scan_status_async(scan_location: str) -> Status:
    """Status of scan.

    Args:
        scan_location: Location to get status for (e.g. directory or s3 bucket)

    Returns:
        ScanStatus: Status of scan (spec, summary, errors, etc.)
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.status(scan_location)


def scan_results(scan_location: str, *, scanner: str | None = None) -> Results:
    """Scan results as Pandas data frames.

    Args:
         scan_location: Location of scan (e.g. directory or s3 bucket).
         scanner: Scanner name (defaults to all scanners).

    Returns:
         ScanResults: Results as pandas data frames.
    """
    return run_coroutine(scan_results_async(scan_location, scanner=scanner))


async def scan_results_async(
    scan_location: str, *, scanner: str | None = None
) -> Results:
    """Scan results as Pandas data frames.

    Args:
         scan_location: Location of scan (e.g. directory or s3 bucket).
         scanner: Scanner name (defaults to all scanners).

    Returns:
         ScanResults: Results as Pandas data frames.
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results(scan_location, scanner=scanner)


def scan_results_db(scan_location: str) -> ResultsDB:
    """Scan results as DuckDB database.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).

    Returns:
        ScanResultsDB: Results as DuckDB database.
    """
    return run_coroutine(scan_results_db_async(scan_location))


async def scan_results_db_async(scan_location: str) -> ResultsDB:
    """Scan results as DuckDB database.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).

    Returns:
        ScanResultsDB: Results as DuckDB database.
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results_db(scan_location)


def remove_scan_results(scan_location: str) -> None:
    scan_path = UPath(scan_location)
    if scan_path.exists():
        scan_path.rmdir(recursive=True)
