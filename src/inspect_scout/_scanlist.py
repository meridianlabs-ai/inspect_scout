from inspect_ai._util._async import run_coroutine

from inspect_scout._recorder.factory import scan_recorder_type_for_location
from inspect_scout._recorder.recorder import Status


def scan_list(scans_location: str) -> list[Status]:
    """List completed and pending scans.

    Args:
        scans_location: Location of scans to list.

    Returns:
        List of `ScanStatus`.
    """
    return run_coroutine(scan_list_async(scans_location))


async def scan_list_async(scans_location: str) -> list[Status]:
    """List completed and pending scans.

    Args:
        scans_location: Location of scans to list.

    Returns:
        List of `ScanStatus`.

    """
    recorder = scan_recorder_type_for_location(scans_location)
    return await recorder.list(scans_location)
