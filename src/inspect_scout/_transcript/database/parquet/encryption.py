import os
import shutil
import tempfile
from pathlib import Path

import duckdb
from upath import UPath

from inspect_scout._display import display
from inspect_scout._transcript.database.parquet.types import (
    ENCRYPTED_INDEX_EXTENSION,
    IndexStorage,
)
from inspect_scout._util.filesystem import ensure_filesystem_dependencies

# Environment variable for encryption key
ENCRYPTION_KEY_ENV = "SCOUT_DB_ENCRYPTION_KEY"

# Internal DuckDB key name (used in PRAGMA add_parquet_key)
ENCRYPTION_KEY_NAME = "scout_key"

# Valid AES key lengths in bytes (128, 192, 256 bits)
VALID_KEY_LENGTHS = (16, 24, 32)


def validate_encryption_key(key: str) -> None:
    """Validate that an encryption key has a valid AES length.

    Args:
        key: The encryption key to validate.

    Raises:
        ValueError: If the key length is not valid for AES encryption.
    """
    key_bytes = len(key.encode("utf-8"))
    if key_bytes not in VALID_KEY_LENGTHS:
        raise ValueError(
            f"Invalid encryption key length: {key_bytes} bytes. "
            f"AES keys must be 16, 24, or 32 bytes (128, 192, or 256 bits)."
        )


def get_encryption_key_from_env() -> str | None:
    """Get encryption key from environment variable.

    Returns:
        The encryption key if set, None otherwise.
    """
    return os.environ.get(ENCRYPTION_KEY_ENV)


def _is_remote(location: str) -> bool:
    """Check if location is a remote filesystem (S3 or HuggingFace)."""
    return location.startswith("s3://") or location.startswith("hf://")


def _list_files_recursive(location: str) -> list[str]:
    """List all files recursively in the given location.

    Args:
        location: Local path or S3/HF URI.

    Returns:
        List of file paths/URIs (directories excluded).
    """
    location_path = UPath(location)
    if not location_path.exists():
        return []
    # Get all files recursively, excluding directories
    # UPath works for both local and remote (S3/HF) via fsspec
    return [str(p) for p in location_path.rglob("*") if p.is_file()]


def _validate_output_dir(output_dir: str, overwrite: bool) -> None:
    """Validate and prepare the output directory.

    Args:
        output_dir: Path to output directory.
        overwrite: If True, remove existing directory.

    Raises:
        FileExistsError: If directory exists and overwrite is False.
    """
    output_path = UPath(output_dir)

    if output_path.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output directory already exists: {output_dir}. "
                "Use --overwrite to replace it."
            )
        # Remove existing directory
        if _is_remote(output_dir):
            # For remote, delete files recursively
            for f in output_path.rglob("*"):
                if f.is_file():
                    f.unlink()
        else:
            shutil.rmtree(str(output_path))

    output_path.mkdir(parents=True, exist_ok=True)


def _setup_duckdb(key: str) -> duckdb.DuckDBPyConnection:
    """Create and configure a DuckDB connection with encryption key.

    Args:
        key: The encryption key to register.

    Returns:
        Configured DuckDB connection.
    """
    conn = duckdb.connect(":memory:")
    conn.execute("INSTALL httpfs")
    conn.execute("LOAD httpfs")
    conn.execute(f"PRAGMA add_parquet_key('{ENCRYPTION_KEY_NAME}', '{key}')")
    return conn


def _get_relative_path(file_path: str, base_location: str) -> str:
    """Get the relative path of a file from the base location.

    Args:
        file_path: Full path to the file.
        base_location: Base directory path.

    Returns:
        Relative path from base to file.
    """
    if _is_remote(base_location):
        # For S3/HF, strip the base location prefix
        base = base_location.rstrip("/") + "/"
        if file_path.startswith(base):
            return file_path[len(base) :]
        return file_path
    else:
        return str(Path(file_path).relative_to(base_location))


def _encrypt_parquet_file(
    conn: duckdb.DuckDBPyConnection,
    source_path: str,
    dest_path: str,
    output_is_remote: bool,
) -> None:
    """Encrypt a parquet file using DuckDB footer_key encryption.

    Args:
        conn: DuckDB connection with encryption key registered.
        source_path: Path to source parquet file.
        dest_path: Path for encrypted output file.
        output_is_remote: Whether the output is on a remote filesystem.
    """
    if output_is_remote:
        # Write to temp file, then upload using UPath
        with tempfile.NamedTemporaryFile(suffix=".enc.parquet", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            conn.execute(
                f"COPY (SELECT * FROM read_parquet('{source_path}')) "
                f"TO '{tmp_path}' (ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
            )
            # Upload to remote using UPath
            UPath(dest_path).write_bytes(Path(tmp_path).read_bytes())
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        # Write directly to local path
        conn.execute(
            f"COPY (SELECT * FROM read_parquet('{source_path}')) "
            f"TO '{dest_path}' (ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
        )


def _decrypt_parquet_file(
    conn: duckdb.DuckDBPyConnection,
    source_path: str,
    dest_path: str,
    output_is_remote: bool,
) -> None:
    """Decrypt a parquet file using DuckDB footer_key decryption.

    Args:
        conn: DuckDB connection with encryption key registered.
        source_path: Path to encrypted parquet file.
        dest_path: Path for decrypted output file.
        output_is_remote: Whether the output is on a remote filesystem.
    """
    if output_is_remote:
        # Write to temp file, then upload using UPath
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            conn.execute(
                f"COPY (SELECT * FROM read_parquet('{source_path}', "
                f"encryption_config={{footer_key: '{ENCRYPTION_KEY_NAME}'}})) "
                f"TO '{tmp_path}'"
            )
            # Upload to remote using UPath
            UPath(dest_path).write_bytes(Path(tmp_path).read_bytes())
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        # Write directly to local path
        conn.execute(
            f"COPY (SELECT * FROM read_parquet('{source_path}', "
            f"encryption_config={{footer_key: '{ENCRYPTION_KEY_NAME}'}})) "
            f"TO '{dest_path}'"
        )


def _copy_file(source_path: str, dest_path: str, output_is_remote: bool) -> None:
    """Copy a non-parquet file from source to destination.

    Uses UPath for cross-filesystem compatibility.

    Args:
        source_path: Path to source file.
        dest_path: Path for destination file.
        output_is_remote: Whether the output is on a remote filesystem.
    """
    # Read content from source (UPath handles both local and remote)
    content = UPath(source_path).read_bytes()

    # Write to destination
    dest = UPath(dest_path)
    if not output_is_remote:
        # For local, ensure parent directory exists
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)


def encrypt_database(location: str, output_dir: str, key: str, overwrite: bool) -> None:
    """Encrypt a transcript database using DuckDB parquet encryption.

    Takes parquet files from location (recursively) and creates encrypted
    versions in output_dir with .enc.parquet extension. Non-parquet files
    are copied unchanged. Directory structure is preserved.

    Args:
        location: Source database location (local path or S3/HF URI).
        output_dir: Output directory for encrypted files.
        key: The encryption key to use.
        overwrite: If True, overwrite existing output directory.

    Raises:
        FileExistsError: If output_dir exists and overwrite is False.
    """
    # Ensure filesystem dependencies are available
    ensure_filesystem_dependencies(location)
    ensure_filesystem_dependencies(output_dir)

    # Validate and prepare output directory
    _validate_output_dir(output_dir, overwrite)

    # List all files in source
    files = _list_files_recursive(location)
    if not files:
        return

    # Setup DuckDB connection
    conn = _setup_duckdb(key)

    output_is_remote = _is_remote(output_dir)

    with display().text_progress("Encrypting", len(files)) as progress:
        for file_path in files:
            file_name = UPath(file_path).name
            progress.update(text=file_name)

            # Compute relative path and destination
            rel_path = _get_relative_path(file_path, location)

            if file_path.endswith(".parquet") and not file_path.endswith(
                ".enc.parquet"
            ):
                # Encrypt parquet file
                dest_rel_path = rel_path.replace(".parquet", ".enc.parquet")
                if output_is_remote:
                    dest_path = f"{output_dir.rstrip('/')}/{dest_rel_path}"
                else:
                    dest_path = str(UPath(output_dir) / dest_rel_path)
                    # Ensure parent directory exists for local
                    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)

                _encrypt_parquet_file(conn, file_path, dest_path, output_is_remote)
            else:
                # Copy non-parquet file unchanged
                if output_is_remote:
                    dest_path = f"{output_dir.rstrip('/')}/{rel_path}"
                else:
                    dest_path = str(UPath(output_dir) / rel_path)

                _copy_file(file_path, dest_path, output_is_remote)

    conn.close()


def decrypt_database(location: str, output_dir: str, key: str, overwrite: bool) -> None:
    """Decrypt a transcript database using DuckDB parquet decryption.

    Takes encrypted parquet files (.enc.parquet) from location (recursively)
    and creates decrypted versions in output_dir with .parquet extension.
    Non-encrypted files are copied unchanged. Directory structure is preserved.

    Args:
        location: Source database location (local path or S3/HF URI).
        output_dir: Output directory for decrypted files.
        key: The encryption key to use.
        overwrite: If True, overwrite existing output directory.

    Raises:
        FileExistsError: If output_dir exists and overwrite is False.
    """
    # Ensure filesystem dependencies are available
    ensure_filesystem_dependencies(location)
    ensure_filesystem_dependencies(output_dir)

    # Validate and prepare output directory
    _validate_output_dir(output_dir, overwrite)

    # List all files in source
    files = _list_files_recursive(location)
    if not files:
        return

    # Setup DuckDB connection
    conn = _setup_duckdb(key)

    output_is_remote = _is_remote(output_dir)

    with display().text_progress("Decrypting", len(files)) as progress:
        for file_path in files:
            file_name = UPath(file_path).name
            progress.update(text=file_name)

            # Compute relative path and destination
            rel_path = _get_relative_path(file_path, location)

            if file_path.endswith(".enc.parquet"):
                # Decrypt encrypted parquet file
                dest_rel_path = rel_path.replace(".enc.parquet", ".parquet")
                if output_is_remote:
                    dest_path = f"{output_dir.rstrip('/')}/{dest_rel_path}"
                else:
                    dest_path = str(UPath(output_dir) / dest_rel_path)
                    # Ensure parent directory exists for local
                    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)

                _decrypt_parquet_file(conn, file_path, dest_path, output_is_remote)
            else:
                # Copy non-encrypted file unchanged
                if output_is_remote:
                    dest_path = f"{output_dir.rstrip('/')}/{rel_path}"
                else:
                    dest_path = str(UPath(output_dir) / rel_path)

                _copy_file(file_path, dest_path, output_is_remote)

    conn.close()


def _is_encrypted_index_file(filename: str) -> bool:
    """Check if an index file is encrypted based on its extension."""
    return filename.endswith(ENCRYPTED_INDEX_EXTENSION)


def _check_index_encryption_status(index_files: list[str]) -> bool | None:
    """Check encryption status of index files and validate consistency.

    Args:
        index_files: List of index file paths.

    Returns:
        True if all encrypted, False if all unencrypted, None if empty list.

    Raises:
        ValueError: If index contains mixed encrypted and unencrypted files.
    """
    if not index_files:
        return None

    encrypted_count = sum(1 for f in index_files if _is_encrypted_index_file(f))
    unencrypted_count = len(index_files) - encrypted_count

    if encrypted_count > 0 and unencrypted_count > 0:
        raise ValueError(
            f"Index contains mixed encrypted ({encrypted_count}) and "
            f"unencrypted ({unencrypted_count}) index files. "
            "All index files must be either encrypted or unencrypted."
        )

    return encrypted_count > 0


def _check_data_encryption_status(data_files: list[str]) -> bool | None:
    """Check encryption status of data files and validate consistency.

    Args:
        data_files: List of data file paths.

    Returns:
        True if all encrypted, False if all unencrypted, None if empty list.

    Raises:
        ValueError: If database contains mixed encrypted and unencrypted files.
    """
    if not data_files:
        return None

    encrypted_count = sum(1 for f in data_files if f.endswith(".enc.parquet"))
    unencrypted_count = len(data_files) - encrypted_count

    if encrypted_count > 0 and unencrypted_count > 0:
        raise ValueError(
            f"Database contains mixed encrypted ({encrypted_count}) and "
            f"unencrypted ({unencrypted_count}) parquet files. "
            "All files must be either encrypted or unencrypted."
        )

    return encrypted_count > 0


def setup_encryption(
    conn: duckdb.DuckDBPyConnection,
    storage: IndexStorage,
) -> str:
    """Setup encryption key and return config string for read_parquet.

    Args:
        conn: DuckDB connection to register the key with.
        storage: Storage configuration with is_encrypted flag.

    Returns:
        Encryption config string for read_parquet (empty if not encrypted).
    """
    if not storage.is_encrypted:
        return ""

    conn.execute(
        f"PRAGMA add_parquet_key('{ENCRYPTION_KEY_NAME}', '{storage.encryption_key}')"
    )
    return f", encryption_config={{footer_key: '{ENCRYPTION_KEY_NAME}'}}"
