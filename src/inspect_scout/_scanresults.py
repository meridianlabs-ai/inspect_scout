from inspect_ai._util._async import run_coroutine

from ._recorder.factory import scan_recorder_type_for_location
from ._recorder.recorder import (
    ScanResults,
    ScanResultsDB,
    ScanStatus,
)


def scan_status(scan_location: str) -> ScanStatus:
    return run_coroutine(scan_status_async(scan_location))


async def scan_status_async(scan_location: str) -> ScanStatus:
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.status(scan_location)


def scan_results(
    scan_location: str, *, scanner: str | None = None, include_null: bool = False
) -> ScanResults:
    return run_coroutine(
        scan_results_async(scan_location, scanner=scanner, include_null=include_null)
    )


async def scan_results_async(
    scan_location: str, *, scanner: str | None = None, include_null: bool = False
) -> ScanResults:
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results(
        scan_location, scanner=scanner, include_null=include_null
    )


def scan_results_db(scan_location: str, include_null: bool = False) -> ScanResultsDB:
    return run_coroutine(scan_results_db_async(scan_location))


async def scan_results_db_async(
    scan_location: str, include_null: bool = False
) -> ScanResultsDB:
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results_db(scan_location, include_null=include_null)
