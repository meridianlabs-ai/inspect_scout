"""Tests demonstrating pre-existing bugs in pagination and scan helpers."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from inspect_scout._query.order_by import OrderBy
from inspect_scout._view._pagination_helpers import cursor_to_condition


class TestCursorToConditionNullHandling:
    """Tests for cursor_to_condition handling of None/null cursor values.

    Bug: cursor.get(column) or "" converts None to empty string, causing
    type mismatches when comparing datetime/numeric columns to "".
    """

    def test_null_cursor_value_should_not_become_empty_string(self) -> None:
        """Cursor with None value should not be converted to empty string.

        When paginating with a cursor that has a null timestamp (e.g., the last
        row had timestamp=NULL), the cursor will contain {"timestamp": None}.
        The current code converts this to "" which causes invalid SQL comparisons.
        """
        cursor: dict[str, Any] = {"timestamp": None, "scan_id": "scan-001"}
        order_columns = [
            OrderBy("timestamp", "ASC"),
            OrderBy("scan_id", "ASC"),
        ]

        condition = cursor_to_condition(cursor, order_columns, "forward")

        # The condition should handle NULL properly, not convert to ""
        # This test will fail because the current implementation uses `or ""`
        condition_str = str(condition)
        assert "right=''" not in condition_str, (
            f"Cursor None value was converted to empty string: {condition_str}"
        )

    def test_falsy_cursor_value_zero_should_not_become_empty_string(self) -> None:
        """Cursor with falsy value 0 should remain 0, not become empty string.

        The `or ""` pattern also incorrectly converts 0 to "" because 0 is falsy.
        """
        cursor: dict[str, Any] = {"count": 0, "scan_id": "scan-001"}
        order_columns = [
            OrderBy("count", "ASC"),
            OrderBy("scan_id", "ASC"),
        ]

        condition = cursor_to_condition(cursor, order_columns, "forward")

        # The condition should contain 0, not ""
        # This test will fail because the current implementation uses `or ""`
        condition_str = str(condition)
        assert "right=0" in condition_str, (
            f"Cursor value 0 was incorrectly converted to empty string: {condition_str}"
        )


class TestSpawnScanSubprocessTempFileCleanup:
    """Tests for _spawn_scan_subprocess temp file cleanup on error."""

    def test_temp_file_cleaned_up_on_write_error(self) -> None:
        """Temp file should be deleted if write fails."""
        from inspect_scout._scanjob_config import ScanJobConfig

        unlink_calls: list[str] = []

        # Mock file that raises on write
        class FailingFile:
            name = "/tmp/test_config.json"

            def write(self, data: str) -> None:
                raise IOError("Simulated write failure")

            def __enter__(self) -> "FailingFile":
                return self

            def __exit__(self, *args: object) -> None:
                pass

        def tracking_unlink(path: str) -> None:
            unlink_calls.append(path)

        with (
            patch(
                "inspect_scout._view._api_v2_scans.tempfile.NamedTemporaryFile",
                return_value=FailingFile(),
            ),
            patch("inspect_scout._view._api_v2_scans.os.unlink", tracking_unlink),
        ):
            from inspect_scout._view._api_v2_scans import _spawn_scan_subprocess

            config = MagicMock(spec=ScanJobConfig)
            config.model_dump_json.return_value = "{}"

            with pytest.raises(IOError, match="Simulated write failure"):
                _spawn_scan_subprocess(config)

        # Temp file should be cleaned up on error
        assert "/tmp/test_config.json" in unlink_calls, (
            f"Temp file was not cleaned up. unlink calls: {unlink_calls}"
        )

    def test_temp_file_cleaned_up_on_popen_error(self) -> None:
        """Temp file should be deleted if subprocess spawn fails."""
        from inspect_scout._scanjob_config import ScanJobConfig

        unlink_calls: list[str] = []

        class MockFile:
            name = "/tmp/test_config.json"

            def write(self, data: str) -> None:
                pass  # Success

            def __enter__(self) -> "MockFile":
                return self

            def __exit__(self, *args: object) -> None:
                pass

        def tracking_unlink(path: str) -> None:
            unlink_calls.append(path)

        def failing_popen(*args: object, **kwargs: object) -> None:
            raise OSError("Simulated Popen failure")

        with (
            patch(
                "inspect_scout._view._api_v2_scans.tempfile.NamedTemporaryFile",
                return_value=MockFile(),
            ),
            patch("inspect_scout._view._api_v2_scans.subprocess.Popen", failing_popen),
            patch("inspect_scout._view._api_v2_scans.os.unlink", tracking_unlink),
        ):
            from inspect_scout._view._api_v2_scans import _spawn_scan_subprocess

            config = MagicMock(spec=ScanJobConfig)
            config.model_dump_json.return_value = "{}"

            with pytest.raises(OSError, match="Simulated Popen failure"):
                _spawn_scan_subprocess(config)

        # Temp file should be cleaned up on error
        assert "/tmp/test_config.json" in unlink_calls, (
            f"Temp file was not cleaned up. unlink calls: {unlink_calls}"
        )
