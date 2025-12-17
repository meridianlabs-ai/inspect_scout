import asyncio
import sys

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
