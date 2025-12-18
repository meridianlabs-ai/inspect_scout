"""Tests for database encryption functionality."""

import tempfile
from pathlib import Path

import duckdb
import pytest
from inspect_scout._transcript.database.parquet.encryption import (
    ENCRYPTION_KEY_ENV,
    ENCRYPTION_KEY_NAME,
    _get_relative_path,
    _is_remote,
    _list_files_recursive,
    _setup_duckdb,
    _validate_output_dir,
    decrypt_database,
    encrypt_database,
    validate_encryption_key,
)

# Test encryption key - 32 characters (256-bit AES key)
TEST_ENCRYPTION_KEY = "0123456789abcdef0123456789abcdef"


class TestValidateEncryptionKey:
    """Tests for validate_encryption_key function."""

    def test_valid_16_byte_key(self) -> None:
        """Test that 16-byte key (128-bit) is valid."""
        key = "0123456789abcdef"  # 16 chars
        validate_encryption_key(key)  # Should not raise

    def test_valid_24_byte_key(self) -> None:
        """Test that 24-byte key (192-bit) is valid."""
        key = "0123456789abcdef01234567"  # 24 chars
        validate_encryption_key(key)  # Should not raise

    def test_valid_32_byte_key(self) -> None:
        """Test that 32-byte key (256-bit) is valid."""
        key = "0123456789abcdef0123456789abcdef"  # 32 chars
        validate_encryption_key(key)  # Should not raise

    def test_invalid_short_key(self) -> None:
        """Test that short key raises error."""
        key = "tooshort"  # 8 chars
        with pytest.raises(ValueError) as exc_info:
            validate_encryption_key(key)
        assert "8 bytes" in str(exc_info.value)
        assert "16, 24, or 32" in str(exc_info.value)

    def test_invalid_long_key(self) -> None:
        """Test that long key raises error."""
        key = "0123456789abcdef0123456789abcdef0"  # 33 chars
        with pytest.raises(ValueError) as exc_info:
            validate_encryption_key(key)
        assert "33 bytes" in str(exc_info.value)

    def test_invalid_17_byte_key(self) -> None:
        """Test that 17-byte key (invalid) raises error."""
        key = "0123456789abcdefX"  # 17 chars
        with pytest.raises(ValueError) as exc_info:
            validate_encryption_key(key)
        assert "17 bytes" in str(exc_info.value)


class TestIsRemote:
    """Tests for _is_remote helper."""

    def test_s3_path_is_remote(self) -> None:
        assert _is_remote("s3://bucket/path") is True

    def test_hf_path_is_remote(self) -> None:
        assert _is_remote("hf://dataset/path") is True

    def test_local_path_is_not_remote(self) -> None:
        assert _is_remote("/local/path") is False
        assert _is_remote("./relative/path") is False
        assert _is_remote("relative/path") is False


class TestListFilesRecursive:
    """Tests for _list_files_recursive helper."""

    def test_lists_files_in_directory(self, tmp_path: Path) -> None:
        # Create test files
        (tmp_path / "file1.parquet").write_text("test")
        (tmp_path / "file2.txt").write_text("test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.parquet").write_text("test")

        files = _list_files_recursive(str(tmp_path))

        assert len(files) == 3
        filenames = [Path(f).name for f in files]
        assert "file1.parquet" in filenames
        assert "file2.txt" in filenames
        assert "file3.parquet" in filenames

    def test_returns_empty_for_nonexistent_directory(self) -> None:
        files = _list_files_recursive("/nonexistent/path/12345")
        assert files == []

    def test_excludes_directories(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("test")
        (tmp_path / "subdir").mkdir()

        files = _list_files_recursive(str(tmp_path))

        assert len(files) == 1
        assert "subdir" not in files[0]


class TestValidateOutputDir:
    """Tests for _validate_output_dir helper."""

    def test_creates_new_directory(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "new_output"
        assert not output_dir.exists()

        _validate_output_dir(str(output_dir), overwrite=False)

        assert output_dir.exists()

    def test_raises_error_if_exists_without_overwrite(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "existing"
        output_dir.mkdir()
        (output_dir / "file.txt").write_text("test")

        with pytest.raises(FileExistsError) as exc_info:
            _validate_output_dir(str(output_dir), overwrite=False)

        assert "already exists" in str(exc_info.value)
        assert "--overwrite" in str(exc_info.value)

    def test_removes_existing_with_overwrite(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "existing"
        output_dir.mkdir()
        old_file = output_dir / "old_file.txt"
        old_file.write_text("old content")

        _validate_output_dir(str(output_dir), overwrite=True)

        assert output_dir.exists()
        assert not old_file.exists()


class TestGetRelativePath:
    """Tests for _get_relative_path helper."""

    def test_local_path_relative(self) -> None:
        result = _get_relative_path("/base/dir/subdir/file.txt", "/base/dir")
        assert result == "subdir/file.txt"

    def test_remote_path_relative(self) -> None:
        result = _get_relative_path(
            "s3://bucket/base/subdir/file.txt", "s3://bucket/base"
        )
        assert result == "subdir/file.txt"

    def test_remote_path_with_trailing_slash(self) -> None:
        result = _get_relative_path(
            "s3://bucket/base/subdir/file.txt", "s3://bucket/base/"
        )
        assert result == "subdir/file.txt"


class TestSetupDuckdb:
    """Tests for _setup_duckdb helper."""

    def test_creates_connection(self) -> None:
        conn = _setup_duckdb(TEST_ENCRYPTION_KEY)
        try:
            assert isinstance(conn, duckdb.DuckDBPyConnection)
        finally:
            conn.close()

    def test_has_encryption_key_registered(self) -> None:
        conn = _setup_duckdb(TEST_ENCRYPTION_KEY)
        try:
            # Write and read encrypted parquet to verify key is registered
            conn.execute("CREATE TABLE test AS SELECT 1 as id")
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
                tmp_path = f.name

            conn.execute(
                f"COPY test TO '{tmp_path}' "
                f"(ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
            )

            # Should be able to read with the registered key
            result = conn.execute(
                f"SELECT * FROM read_parquet('{tmp_path}', "
                f"encryption_config={{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
            ).fetchall()
            assert result == [(1,)]

            Path(tmp_path).unlink()
        finally:
            conn.close()


class TestEncryptDatabase:
    """Tests for encrypt_database function."""

    @pytest.fixture
    def source_db(self, tmp_path: Path) -> Path:
        """Create a source database with test parquet files."""
        src_dir = tmp_path / "source"
        src_dir.mkdir()

        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE test AS SELECT 1 as id, 'hello' as msg")
        conn.execute(f"COPY test TO '{src_dir / 'transcripts_test1.parquet'}'")
        conn.execute("CREATE TABLE test2 AS SELECT 2 as id, 'world' as msg")
        conn.execute(f"COPY test2 TO '{src_dir / 'transcripts_test2.parquet'}'")
        conn.close()

        return src_dir

    def test_encrypts_parquet_files(self, source_db: Path, tmp_path: Path) -> None:
        output_dir = tmp_path / "encrypted"

        encrypt_database(
            str(source_db), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Check encrypted files were created
        enc_files = list(output_dir.glob("*.enc.parquet"))
        assert len(enc_files) == 2

        # Verify files are encrypted (can't read without key)
        conn = duckdb.connect(":memory:")
        for enc_file in enc_files:
            with pytest.raises(duckdb.InvalidInputException):
                conn.execute(f"SELECT * FROM read_parquet('{enc_file}')").fetchall()
        conn.close()

    def test_encrypted_files_readable_with_key(
        self, source_db: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "encrypted"

        encrypt_database(
            str(source_db), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Should be readable with the correct key
        conn = duckdb.connect(":memory:")
        conn.execute(
            f"PRAGMA add_parquet_key('{ENCRYPTION_KEY_NAME}', '{TEST_ENCRYPTION_KEY}')"
        )

        enc_file = list(output_dir.glob("*.enc.parquet"))[0]
        result = conn.execute(
            f"SELECT * FROM read_parquet('{enc_file}', "
            f"encryption_config={{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
        ).fetchall()

        assert len(result) > 0
        conn.close()

    def test_raises_error_if_output_exists(
        self, source_db: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "encrypted"
        output_dir.mkdir()
        (output_dir / "existing.txt").write_text("test")

        with pytest.raises(FileExistsError) as exc_info:
            encrypt_database(
                str(source_db), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
            )

        assert "--overwrite" in str(exc_info.value)

    def test_overwrite_removes_existing(self, source_db: Path, tmp_path: Path) -> None:
        output_dir = tmp_path / "encrypted"
        output_dir.mkdir()
        old_file = output_dir / "old.txt"
        old_file.write_text("old")

        encrypt_database(
            str(source_db), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=True
        )

        assert not old_file.exists()
        assert len(list(output_dir.glob("*.enc.parquet"))) == 2

    def test_copies_non_parquet_files(self, tmp_path: Path) -> None:
        # Create source with mixed files
        src_dir = tmp_path / "source"
        src_dir.mkdir()

        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE test AS SELECT 1 as id")
        conn.execute(f"COPY test TO '{src_dir / 'transcripts_test.parquet'}'")
        conn.close()

        (src_dir / "readme.txt").write_text("readme content")
        (src_dir / "config.json").write_text('{"key": "value"}')

        output_dir = tmp_path / "encrypted"
        encrypt_database(
            str(src_dir), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Check all files exist
        assert (output_dir / "transcripts_test.enc.parquet").exists()
        assert (output_dir / "readme.txt").exists()
        assert (output_dir / "config.json").exists()

        # Check non-parquet content preserved
        assert (output_dir / "readme.txt").read_text() == "readme content"

    def test_preserves_directory_structure(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        (src_dir / "subdir").mkdir()

        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE test AS SELECT 1 as id")
        conn.execute(f"COPY test TO '{src_dir / 'transcripts_test1.parquet'}'")
        conn.execute(
            f"COPY test TO '{src_dir / 'subdir' / 'transcripts_test2.parquet'}'"
        )
        conn.close()

        output_dir = tmp_path / "encrypted"
        encrypt_database(
            str(src_dir), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        assert (output_dir / "transcripts_test1.enc.parquet").exists()
        assert (output_dir / "subdir" / "transcripts_test2.enc.parquet").exists()


class TestDecryptDatabase:
    """Tests for decrypt_database function."""

    @pytest.fixture
    def encrypted_db(self, tmp_path: Path) -> Path:
        """Create an encrypted database for testing."""
        enc_dir = tmp_path / "encrypted"
        enc_dir.mkdir()

        conn = duckdb.connect(":memory:")
        conn.execute(
            f"PRAGMA add_parquet_key('{ENCRYPTION_KEY_NAME}', '{TEST_ENCRYPTION_KEY}')"
        )
        conn.execute("CREATE TABLE test AS SELECT 42 as value, 'encrypted' as msg")
        conn.execute(
            f"COPY test TO '{enc_dir / 'transcripts_test.enc.parquet'}' "
            f"(ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
        )
        conn.close()

        return enc_dir

    def test_decrypts_encrypted_files(self, encrypted_db: Path, tmp_path: Path) -> None:
        output_dir = tmp_path / "decrypted"

        decrypt_database(
            str(encrypted_db), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Check decrypted file exists with correct extension
        dec_files = list(output_dir.glob("*.parquet"))
        assert len(dec_files) == 1
        assert not dec_files[0].name.endswith(".enc.parquet")

    def test_decrypted_files_readable_without_key(
        self, encrypted_db: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "decrypted"

        decrypt_database(
            str(encrypted_db), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Should be readable without any encryption key
        conn = duckdb.connect(":memory:")
        dec_file = list(output_dir.glob("*.parquet"))[0]
        result = conn.execute(f"SELECT * FROM read_parquet('{dec_file}')").fetchall()

        assert result == [(42, "encrypted")]
        conn.close()

    def test_raises_error_if_output_exists(
        self, encrypted_db: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "decrypted"
        output_dir.mkdir()
        (output_dir / "existing.txt").write_text("test")

        with pytest.raises(FileExistsError):
            decrypt_database(
                str(encrypted_db), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
            )

    def test_preserves_data_integrity(self, tmp_path: Path) -> None:
        """Test that encrypt -> decrypt roundtrip preserves data."""
        # Create source with specific data
        src_dir = tmp_path / "source"
        src_dir.mkdir()

        conn = duckdb.connect(":memory:")
        conn.execute(
            "CREATE TABLE test AS SELECT "
            "123 as id, "
            "'test message' as msg, "
            "3.14159 as value"
        )
        conn.execute(f"COPY test TO '{src_dir / 'transcripts_test.parquet'}'")
        conn.close()

        # Encrypt
        enc_dir = tmp_path / "encrypted"
        encrypt_database(
            str(src_dir), str(enc_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Decrypt
        dec_dir = tmp_path / "decrypted"
        decrypt_database(
            str(enc_dir), str(dec_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Verify data integrity
        conn = duckdb.connect(":memory:")
        original = conn.execute(
            f"SELECT * FROM read_parquet('{src_dir / 'transcripts_test.parquet'}')"
        ).fetchall()
        decrypted = conn.execute(
            f"SELECT * FROM read_parquet('{dec_dir / 'transcripts_test.parquet'}')"
        ).fetchall()
        conn.close()

        assert original == decrypted

    def test_copies_non_encrypted_files(self, tmp_path: Path) -> None:
        """Test that non-encrypted files are copied unchanged."""
        enc_dir = tmp_path / "encrypted"
        enc_dir.mkdir()

        # Create encrypted parquet
        conn = duckdb.connect(":memory:")
        conn.execute(
            f"PRAGMA add_parquet_key('{ENCRYPTION_KEY_NAME}', '{TEST_ENCRYPTION_KEY}')"
        )
        conn.execute("CREATE TABLE test AS SELECT 1 as id")
        conn.execute(
            f"COPY test TO '{enc_dir / 'transcripts_test.enc.parquet'}' "
            f"(ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
        )
        conn.close()

        # Create non-encrypted files
        (enc_dir / "readme.txt").write_text("readme content")

        output_dir = tmp_path / "decrypted"
        decrypt_database(
            str(enc_dir), str(output_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        assert (output_dir / "transcripts_test.parquet").exists()
        assert (output_dir / "readme.txt").exists()
        assert (output_dir / "readme.txt").read_text() == "readme content"


class TestEncryptDecryptRoundtrip:
    """End-to-end tests for encrypt/decrypt roundtrip."""

    def test_full_roundtrip(self, tmp_path: Path) -> None:
        """Test complete encrypt -> decrypt cycle."""
        # Create source database
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        (src_dir / "subdir").mkdir()

        conn = duckdb.connect(":memory:")
        # Create multiple files with different data
        for i in range(3):
            conn.execute(f"CREATE TABLE test{i} AS SELECT {i} as id, 'data{i}' as val")
            if i < 2:
                conn.execute(
                    f"COPY test{i} TO '{src_dir / f'transcripts_file{i}.parquet'}'"
                )
            else:
                conn.execute(
                    f"COPY test{i} TO '{src_dir / 'subdir' / f'transcripts_file{i}.parquet'}'"
                )
        conn.close()

        # Add a non-parquet file
        (src_dir / "metadata.json").write_text('{"version": 1}')

        # Encrypt
        enc_dir = tmp_path / "encrypted"
        encrypt_database(
            str(src_dir), str(enc_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Verify encrypted state
        assert len(list(enc_dir.glob("**/*.enc.parquet"))) == 3
        assert (enc_dir / "metadata.json").exists()

        # Decrypt
        dec_dir = tmp_path / "decrypted"
        decrypt_database(
            str(enc_dir), str(dec_dir), TEST_ENCRYPTION_KEY, overwrite=False
        )

        # Verify decrypted state
        assert len(list(dec_dir.glob("**/*.parquet"))) == 3
        assert not any(f.name.endswith(".enc.parquet") for f in dec_dir.glob("**/*"))
        assert (dec_dir / "metadata.json").read_text() == '{"version": 1}'

        # Verify data integrity for all files
        conn = duckdb.connect(":memory:")
        for i in range(3):
            if i < 2:
                src_file = src_dir / f"transcripts_file{i}.parquet"
                dec_file = dec_dir / f"transcripts_file{i}.parquet"
            else:
                src_file = src_dir / "subdir" / f"transcripts_file{i}.parquet"
                dec_file = dec_dir / "subdir" / f"transcripts_file{i}.parquet"

            original = conn.execute(
                f"SELECT * FROM read_parquet('{src_file}')"
            ).fetchall()
            decrypted = conn.execute(
                f"SELECT * FROM read_parquet('{dec_file}')"
            ).fetchall()

            assert original == decrypted, f"Data mismatch for file {i}"
        conn.close()


class TestParquetDBEncryptionDetection:
    """Tests for ParquetTranscriptsDB encryption detection."""

    def test_check_encryption_status_all_encrypted(self) -> None:
        """Test detection of all encrypted files."""
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        db = ParquetTranscriptsDB("/tmp/test")
        files = [
            "/path/to/transcripts_1.enc.parquet",
            "/path/to/transcripts_2.enc.parquet",
        ]

        result = db._check_encryption_status(files)
        assert result is True

    def test_check_encryption_status_all_unencrypted(self) -> None:
        """Test detection of all unencrypted files."""
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        db = ParquetTranscriptsDB("/tmp/test")
        files = [
            "/path/to/transcripts_1.parquet",
            "/path/to/transcripts_2.parquet",
        ]

        result = db._check_encryption_status(files)
        assert result is False

    def test_check_encryption_status_mixed_raises_error(self) -> None:
        """Test that mixed files raise an error."""
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        db = ParquetTranscriptsDB("/tmp/test")
        files = [
            "/path/to/transcripts_1.parquet",
            "/path/to/transcripts_2.enc.parquet",
        ]

        with pytest.raises(ValueError) as exc_info:
            db._check_encryption_status(files)

        assert "mixed encrypted" in str(exc_info.value)
        assert "1" in str(exc_info.value)  # encrypted count
        assert "unencrypted" in str(exc_info.value)

    def test_read_parquet_encryption_config_encrypted(self) -> None:
        """Test encryption config string when encrypted."""
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        db = ParquetTranscriptsDB("/tmp/test")
        db._is_encrypted = True

        config = db._read_parquet_encryption_config()
        assert "encryption_config" in config
        assert "footer_key" in config
        assert ENCRYPTION_KEY_NAME in config

    def test_read_parquet_encryption_config_not_encrypted(self) -> None:
        """Test encryption config string when not encrypted."""
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        db = ParquetTranscriptsDB("/tmp/test")
        db._is_encrypted = False

        config = db._read_parquet_encryption_config()
        assert config == ""


@pytest.mark.asyncio
class TestParquetDBEncryptedAccess:
    """Integration tests for accessing encrypted databases."""

    @pytest.fixture
    def encrypted_db_dir(self, tmp_path: Path) -> Path:
        """Create an encrypted database directory with test data."""
        db_dir = tmp_path / "encrypted_db"
        db_dir.mkdir()

        # Create encrypted parquet files
        conn = duckdb.connect(":memory:")
        conn.execute(
            f"PRAGMA add_parquet_key('{ENCRYPTION_KEY_NAME}', '{TEST_ENCRYPTION_KEY}')"
        )

        # Create test data matching transcript schema
        conn.execute("""
            CREATE TABLE transcripts AS SELECT
                'test-001' as transcript_id,
                'test' as source_type,
                'source-001' as source_id,
                'test://uri' as source_uri,
                '[]' as messages,
                '[]' as events
        """)
        conn.execute(
            f"COPY transcripts TO '{db_dir / 'transcripts_test1.enc.parquet'}' "
            f"(ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
        )

        conn.execute("""
            CREATE OR REPLACE TABLE transcripts AS SELECT
                'test-002' as transcript_id,
                'test' as source_type,
                'source-002' as source_id,
                'test://uri2' as source_uri,
                '[]' as messages,
                '[]' as events
        """)
        conn.execute(
            f"COPY transcripts TO '{db_dir / 'transcripts_test2.enc.parquet'}' "
            f"(ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
        )
        conn.close()

        return db_dir

    @pytest.fixture(autouse=True)
    def set_encryption_key_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set the encryption key environment variable for all tests."""
        monkeypatch.setenv(ENCRYPTION_KEY_ENV, TEST_ENCRYPTION_KEY)

    async def test_connect_to_encrypted_database(self, encrypted_db_dir: Path) -> None:
        """Test that ParquetTranscriptsDB can connect to encrypted database."""
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        db = ParquetTranscriptsDB(str(encrypted_db_dir))
        await db.connect()

        try:
            assert db._is_encrypted is True
            assert db._conn is not None
        finally:
            await db.disconnect()

    async def test_count_encrypted_database(self, encrypted_db_dir: Path) -> None:
        """Test counting transcripts in encrypted database."""
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        db = ParquetTranscriptsDB(str(encrypted_db_dir))
        await db.connect()

        try:
            ids = await db.transcript_ids()
            assert len(ids) == 2
        finally:
            await db.disconnect()

    async def test_select_from_encrypted_database(self, encrypted_db_dir: Path) -> None:
        """Test selecting transcripts from encrypted database."""
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        db = ParquetTranscriptsDB(str(encrypted_db_dir))
        await db.connect()

        try:
            # Collect results from async iterator
            results = [t async for t in db.select()]
            assert len(results) == 2
            transcript_ids = {t.transcript_id for t in results}
            assert "test-001" in transcript_ids
            assert "test-002" in transcript_ids
        finally:
            await db.disconnect()

    async def test_missing_key_raises_error(
        self, encrypted_db_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing encryption key raises PrerequisiteError."""
        from inspect_ai._util.error import PrerequisiteError
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        # Remove the environment variable
        monkeypatch.delenv(ENCRYPTION_KEY_ENV, raising=False)

        db = ParquetTranscriptsDB(str(encrypted_db_dir))

        with pytest.raises(PrerequisiteError) as exc_info:
            await db.connect()

        assert "encryption key" in str(exc_info.value).lower()
        assert ENCRYPTION_KEY_ENV in str(exc_info.value)

    async def test_invalid_key_length_raises_error(
        self, encrypted_db_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid key length raises PrerequisiteError."""
        from inspect_ai._util.error import PrerequisiteError
        from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

        # Set an invalid key (wrong length)
        monkeypatch.setenv(ENCRYPTION_KEY_ENV, "tooshort")

        db = ParquetTranscriptsDB(str(encrypted_db_dir))

        with pytest.raises(PrerequisiteError) as exc_info:
            await db.connect()

        assert "8 bytes" in str(exc_info.value)
        assert "16, 24, or 32" in str(exc_info.value)
