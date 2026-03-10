import asyncio
import json
from pathlib import Path

import click
import duckdb

from inspect_scout._transcript.database.parquet.index import create_index
from inspect_scout._transcript.database.parquet.types import IndexStorage
from inspect_scout._transcript.database.schema import (
    transcripts_db_schema,
    validate_transcript_schema,
)


@click.group("db")
def db_command() -> None:
    """Scout transcript database management."""
    return None


@db_command.command("index")
@click.argument("database-location", type=str, required=True)
def index(database_location: str) -> None:
    """Create or rebuild the index for a transcript database.

    This scans all parquet data files and creates a manifest index
    containing metadata for fast queries. Any existing index files
    are replaced.
    """

    async def _run() -> None:
        storage = IndexStorage.create(location=database_location)
        conn = duckdb.connect(":memory:")
        try:
            result = await create_index(conn, storage)
            if result:
                click.echo(f"Index created: {result}")
            else:
                click.echo("No data files found to index.")
        finally:
            conn.close()

    asyncio.run(_run())


@db_command.command("schema")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["avro", "pyarrow", "json", "pandas"]),
    default="avro",
    help="Output format (default: avro).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write to file instead of stdout.",
)
def schema(fmt: str, output: str | None) -> None:
    """Print the transcript database schema.

    Outputs the schema in various formats for use when creating
    transcript databases outside of the Python API.

    Examples:
        scout db schema                     # Avro schema to stdout

        scout db schema --format pyarrow    # PyArrow schema

        scout db schema -o transcript.avsc  # Save to file
    """
    output_str: str
    if fmt == "pyarrow":
        # PyArrow schema has a nice string representation
        output_str = str(transcripts_db_schema(format="pyarrow"))
    elif fmt == "pandas":
        # Show DataFrame info
        df = transcripts_db_schema(format="pandas")
        output_str = df.dtypes.to_string()
    elif fmt == "avro":
        output_str = json.dumps(transcripts_db_schema(format="avro"), indent=2)
    else:  # json
        output_str = json.dumps(transcripts_db_schema(format="json"), indent=2)

    if output:
        Path(output).write_text(output_str)
        click.echo(f"Schema written to {output}")
    else:
        click.echo(output_str)


@db_command.command("validate")
@click.argument("database-location", type=str, required=True)
def validate(database_location: str) -> None:
    """Validate a transcript database schema.

    Checks that the database has the required fields and correct types.

    Examples:
        scout db validate ./my_transcript_db
    """
    path = Path(database_location)

    if not path.exists():
        click.echo(f"Error: Path does not exist: {database_location}", err=True)
        raise SystemExit(1)

    errors = validate_transcript_schema(path)

    if errors:
        click.echo("Schema validation failed:", err=True)
        for error in errors:
            click.echo(f"  - {error.field}: {error.message}", err=True)
        raise SystemExit(1)
    else:
        click.echo("Schema validation passed.")
