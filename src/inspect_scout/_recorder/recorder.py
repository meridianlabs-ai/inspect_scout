import abc
from dataclasses import dataclass
from types import TracebackType
from typing import Sequence

import duckdb
import pandas as pd

from .._scanner.result import Error, ResultReport
from .._scanspec import ScanSpec
from .._transcript.types import TranscriptInfo


@dataclass
class ScanStatus:
    complete: bool
    spec: ScanSpec
    location: str
    errors: list[Error]


@dataclass
class ScanResults(ScanStatus):
    data: dict[str, pd.DataFrame]

    def __init__(
        self,
        status: bool,
        spec: ScanSpec,
        location: str,
        errors: list[Error],
        data: dict[str, pd.DataFrame],
    ) -> None:
        super().__init__(status, spec, location, errors)
        self.data = data


@dataclass
class ScanResultsDB(ScanStatus):
    conn: duckdb.DuckDBPyConnection

    def __init__(
        self,
        status: bool,
        spec: ScanSpec,
        location: str,
        errors: list[Error],
        conn: duckdb.DuckDBPyConnection,
    ) -> None:
        super().__init__(status, spec, location, errors)
        self.conn = conn

    def __enter__(self) -> "ScanResultsDB":
        """Enter the async context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.conn.close()

    def to_file(self, file: str, overwrite: bool = False) -> None:
        """Write the database contents to a DuckDB file.

        This materializes all views and tables from the in-memory connection
        into a persistent DuckDB database file.

        Args:
            file:    File where the DuckDB database file should be written.
                     Supports local paths, S3 URIs (s3://bucket/path), and
                     GCS URIs (gs://bucket/path or gcs://bucket/path).
            overwrite: If True, overwrite existing file. If False (default),
                      raise FileExistsError if file already exists.

        Returns:
            The path to the created database file (same as input db_path)

        Raises:
            FileExistsError: If the file exists and overwrite is False

        Note:
            Cloud storage requires the httpfs extension (autoloaded on first use)
            and appropriate credentials:
            - S3: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY environment variables
            - GCS: Uses S3 compatibility API, requires HMAC keys configured as
                   AWS credentials (see DuckDB GCS documentation)
        """
        from upath import UPath

        # Check if file exists
        path = UPath(file)
        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Database file already exists: {file}. "
                f"Use overwrite=True to replace it."
            )

        # If overwriting, delete the existing file
        if path.exists() and overwrite:
            path.unlink()

        # Create a new DuckDB connection to the file
        file_conn = duckdb.connect(file)

        try:
            # Get all tables and views from the in-memory connection
            tables_and_views = self.conn.execute("SHOW TABLES").fetchall()

            # Materialize each table/view into the file database
            for row in tables_and_views:
                table_name = row[0]

                # Read the data from the in-memory connection into a DataFrame
                df = self.conn.execute(f"SELECT * FROM {table_name}").fetchdf()  # noqa: F841

                # Write the DataFrame as a table in the file connection
                file_conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")

        finally:
            # Close the file connection
            file_conn.close()


class ScanRecorder(abc.ABC):
    @abc.abstractmethod
    async def init(self, spec: ScanSpec, scans_location: str) -> None: ...

    @abc.abstractmethod
    async def resume(self, scan_location: str) -> ScanSpec: ...

    @abc.abstractmethod
    async def location(self) -> str: ...

    @abc.abstractmethod
    async def is_recorded(self, transcript: TranscriptInfo, scanner: str) -> bool: ...

    @abc.abstractmethod
    async def record(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None: ...

    @abc.abstractmethod
    async def flush(self) -> None: ...

    @abc.abstractmethod
    async def errors(self) -> list[Error]: ...

    @staticmethod
    @abc.abstractmethod
    async def complete(scan_location: str) -> ScanStatus: ...

    @staticmethod
    @abc.abstractmethod
    async def status(scan_location: str) -> ScanStatus: ...

    @staticmethod
    @abc.abstractmethod
    async def results(
        scan_location: str, *, scanner: str | None = None, include_null: bool = False
    ) -> ScanResults: ...

    @staticmethod
    @abc.abstractmethod
    async def results_db(
        scan_location: str, *, include_null: bool = False
    ) -> ScanResultsDB: ...

    @staticmethod
    @abc.abstractmethod
    async def list(scans_location: str) -> list[ScanStatus]: ...
