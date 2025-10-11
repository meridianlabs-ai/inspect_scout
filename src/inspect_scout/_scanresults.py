import pandas as pd
from inspect_ai._util._async import run_coroutine

from ._recorder.factory import scan_recorder_type_for_location
from ._recorder.recorder import ScanResults, ScanResultsFilter, ScanStatus


def scan_status(scan_location: str) -> ScanStatus:
    return run_coroutine(scan_status_async(scan_location))


async def scan_status_async(scan_location: str) -> ScanStatus:
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.status(scan_location)


def has_value(df: pd.DataFrame) -> pd.Series:
    return df["value"].notnull()


def scan_results(
    scan_location: str,
    *,
    scanner: str | None = None,
    filter: ScanResultsFilter | None = has_value,
) -> ScanResults:
    return run_coroutine(
        scan_results_async(scan_location, scanner=scanner, filter=filter)
    )


async def scan_results_async(
    scan_location: str,
    *,
    scanner: str | None = None,
    filter: ScanResultsFilter | None = has_value,
) -> ScanResults:
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results(scan_location, scanner=scanner, filter=filter)
