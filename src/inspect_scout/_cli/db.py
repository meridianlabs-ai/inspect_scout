import asyncio
import json
import sys
from pathlib import Path

import click
import duckdb
from inspect_ai._util.error import PrerequisiteError

from inspect_scout._transcript.database.parquet.encryption import (
    ENCRYPTION_KEY_ENV,
    decrypt_database,
    encrypt_database,
    get_encryption_key_from_env,
    validate_encryption_key,
)
from inspect_scout._transcript.database.parquet.index import create_index
from inspect_scout._transcript.database.parquet.types import IndexStorage
from inspect_scout._transcript.database.schema import (
    transcripts_db_schema,
    validate_transcript_schema,
)


def _resolve_key(key: str | None) -> str:
    """Resolve encryption key from CLI option, stdin, or environment.

    Args:
        key: Key value from --key option (may be "-" for stdin, None if not provided)

    Returns:
        The resolved encryption key.

    Raises:
        PrerequisiteError: If no key is available or key is invalid.
    """
    resolved_key: str
    if key == "-":
        # Read from stdin
        resolved_key = sys.stdin.read().strip()
    elif key is not None:
        resolved_key = key
    else:
        # Try environment variable
        env_key = get_encryption_key_from_env()
        if env_key:
            resolved_key = env_key
        else:
            raise PrerequisiteError(
                f"No encryption key provided. Use --key or set {ENCRYPTION_KEY_ENV}"
            )

    # Validate the key
    try:
        validate_encryption_key(resolved_key)
    except ValueError as e:
        raise PrerequisiteError(str(e)) from e

    return resolved_key


@click.group("db")
def db_command() -> None:
    """Scout transcript database management."""
    return None


@db_command.command("encrypt")
@click.argument("database-location", type=str, required=True)
@click.option(
    "--output-dir",
    required=True,
    help="Directory to write encrypted database files to.",
)
@click.option(
    "--key",
    type=str,
    default=None,
    envvar="SCOUT_DB_ENCRYPTION_KEY",
    help="Encryption key (use '-' for stdin, or set SCOUT_DB_ENCRYPTION_KEY).",
)
@click.option(
    "--overwrite",
    type=bool,
    is_flag=True,
    default=False,
    help="Overwrite files in the output directory.",
)
def encrypt(
    database_location: str, output_dir: str, key: str | None, overwrite: bool
) -> None:
    """Encrypt a transcript database."""
    resolved_key = _resolve_key(key)
    encrypt_database(database_location, output_dir, resolved_key, overwrite)


@db_command.command("decrypt")
@click.argument("database-location", type=str, required=True)
@click.option(
    "--output-dir",
    required=True,
    help="Directory to write decrypted database files to.",
)
@click.option(
    "--key",
    type=str,
    default=None,
    envvar="SCOUT_DB_ENCRYPTION_KEY",
    help="Encryption key (use '-' for stdin, or set SCOUT_DB_ENCRYPTION_KEY).",
)
@click.option(
    "--overwrite",
    type=bool,
    is_flag=True,
    default=False,
    help="Overwrite files in the output directory.",
)
def decrypt(
    database_location: str, output_dir: str, key: str | None, overwrite: bool
) -> None:
    """Decrypt a transcript database."""
    resolved_key = _resolve_key(key)
    decrypt_database(database_location, output_dir, resolved_key, overwrite)


@db_command.command("index")
@click.argument("database-location", type=str, required=True)
@click.option(
    "--key",
    type=str,
    default=None,
    help="Encryption key for encrypted databases (use '-' for stdin, or set SCOUT_DB_ENCRYPTION_KEY).",
)
def index(database_location: str, key: str | None) -> None:
    """Create or rebuild the index for a transcript database.

    This scans all parquet data files and creates a manifest index
    containing metadata for fast queries. Any existing index files
    are replaced.

    For encrypted databases, provide --key or set SCOUT_DB_ENCRYPTION_KEY.
    """
    # Resolve key if provided (handles stdin), but don't require it
    # IndexStorage.create() will error if encrypted files detected without key
    try:
        resolved_key = _resolve_key(key) if key is not None else None
    except PrerequisiteError:
        resolved_key = None

    async def _run() -> None:
        storage = await IndexStorage.create(
            location=database_location, key=resolved_key
        )
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
@click.option(
    "--key",
    type=str,
    default=None,
    help="Encryption key for encrypted databases (use '-' for stdin, or set SCOUT_DB_ENCRYPTION_KEY).",
)
def validate(database_location: str, key: str | None) -> None:
    """Validate a transcript database schema.

    Checks that the database has the required fields and correct types.

    Examples:
        scout db validate ./my_transcript_db

        scout db validate ./encrypted_db --key $KEY
    """
    import tempfile

    path = Path(database_location)

    if not path.exists():
        click.echo(f"Error: Path does not exist: {database_location}", err=True)
        raise SystemExit(1)

    # Check if database appears to be encrypted (has .enc files)
    enc_files = list(path.glob("*.parquet.enc"))
    parquet_files = list(path.glob("*.parquet"))

    if enc_files and not parquet_files:
        # Database is encrypted - need key to validate
        resolved_key = _resolve_key(key)

        # Decrypt to temp directory for validation
        with tempfile.TemporaryDirectory() as temp_dir:
            click.echo("Decrypting database for validation...")
            decrypt_database(database_location, temp_dir, resolved_key, overwrite=False)
            errors = validate_transcript_schema(Path(temp_dir))
    else:
        # Database is not encrypted
        errors = validate_transcript_schema(path)

    if errors:
        click.echo("Schema validation failed:", err=True)
        for error in errors:
            click.echo(f"  - {error.field}: {error.message}", err=True)
        raise SystemExit(1)
    else:
        click.echo("Schema validation passed.")
