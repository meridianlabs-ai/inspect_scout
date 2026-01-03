"""Column definitions for scan job filtering DSL."""

from inspect_scout._query import Column


class ScanJobColumns:
    """Column selector for scan job filter expressions.

    Provides named properties for IDE autocomplete when building filter conditions.

    Example:
        from inspect_scout._scanjobs.columns import scan_job_columns as c

        filter = c.scan_name == "my_scan"
        filter = (c.complete == True) & (c.model.like("%gpt%"))
    """

    @property
    def scan_id(self) -> Column:
        """Unique identifier for the scan job."""
        return Column("scan_id")

    @property
    def scan_name(self) -> Column:
        """Name of the scan job."""
        return Column("scan_name")

    @property
    def scanners(self) -> Column:
        """Comma-separated list of scanner names."""
        return Column("scanners")

    @property
    def model(self) -> Column:
        """Model used for the scan."""
        return Column("model")

    @property
    def location(self) -> Column:
        """Path to the scan directory."""
        return Column("location")

    @property
    def timestamp(self) -> Column:
        """Timestamp when scan was created."""
        return Column("timestamp")

    @property
    def complete(self) -> Column:
        """Whether the scan is complete."""
        return Column("complete")

    def __getattr__(self, name: str) -> Column:
        """Access columns using dot notation."""
        if name.startswith("_"):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )
        return Column(name)

    def __getitem__(self, name: str) -> Column:
        """Access columns using bracket notation."""
        return Column(name)


scan_job_columns = ScanJobColumns()
"""Column selector for scan job filter expressions.

Typically aliased to a more compact expression (e.g. `c`) for use in queries.

Example:
    from inspect_scout._scanjobs.columns import scan_job_columns as c

    filter = c.complete == True
    filter = (c.scan_name == "job") & (c.model.like("%gpt%"))
"""
