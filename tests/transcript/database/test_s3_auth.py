from pathlib import Path
from typing import cast

import duckdb
import pytest
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB


class RecordingConnection:
    def __init__(self, outcomes: list[duckdb.Error | None]) -> None:
        self._outcomes = outcomes
        self.statements: list[str] = []

    def execute(self, statement: str) -> None:
        self.statements.append(statement)
        outcome = self._outcomes.pop(0)
        if outcome is not None:
            raise outcome


def _s3_database(connection: RecordingConnection) -> ParquetTranscriptsDB:
    database = ParquetTranscriptsDB("s3://example-bucket/transcripts")
    database._conn = cast(duckdb.DuckDBPyConnection, connection)
    return database


def _write_config(tmp_path: Path, contents: str) -> Path:
    config_file = tmp_path / "config"
    config_file.write_text(contents, encoding="utf-8")
    return config_file


def test_s3_auth_falls_back_when_config_has_only_named_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _write_config(tmp_path, "[profile named-only]\nregion = us-east-1\n")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config_file))
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    connection = RecordingConnection(
        [
            duckdb.Error(
                "Secret Validation Failure: no profile 'default' found in config file"
            ),
            None,
        ]
    )

    _s3_database(connection)._init_s3_auth()

    assert connection.statements == [
        "CREATE SECRET (TYPE S3, PROVIDER credential_chain, "
        "CHAIN 'env;config;sso;instance;process', PROFILE 'default')",
        "CREATE SECRET (TYPE S3, PROVIDER credential_chain)",
    ]


def test_s3_auth_falls_back_when_profile_exists_only_in_credentials_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _write_config(
        tmp_path, "[profile another-profile]\nregion = us-east-1\n"
    )
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("AWS_PROFILE", "credentials-only")
    connection = RecordingConnection(
        [
            duckdb.Error(
                "Secret Validation Failure: no profile 'credentials-only' found in config file"
            ),
            None,
        ]
    )

    _s3_database(connection)._init_s3_auth()

    assert connection.statements == [
        "CREATE SECRET (TYPE S3, PROVIDER credential_chain, "
        "CHAIN 'env;config;sso;instance;process', PROFILE 'credentials-only')",
        "CREATE SECRET (TYPE S3, PROVIDER credential_chain)",
    ]


def test_s3_auth_uses_bound_profile_chain_for_sso_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _write_config(
        tmp_path,
        "[profile sso-user]\nsso_start_url = https://example.awsapps.com/start\n",
    )
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("AWS_PROFILE", "sso-user")
    connection = RecordingConnection([None])

    _s3_database(connection)._init_s3_auth()

    assert connection.statements == [
        "CREATE SECRET (TYPE S3, PROVIDER credential_chain, "
        "CHAIN 'env;config;sso;instance;process', PROFILE 'sso-user')"
    ]


def test_s3_auth_uses_default_chain_without_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "missing-config"))
    connection = RecordingConnection([None])

    _s3_database(connection)._init_s3_auth()

    assert connection.statements == [
        "CREATE SECRET (TYPE S3, PROVIDER credential_chain)"
    ]


def test_s3_auth_reraises_non_profile_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _write_config(tmp_path, "[default]\nregion = us-east-1\n")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config_file))
    connection = RecordingConnection([duckdb.Error("Credential provider failed")])

    with pytest.raises(duckdb.Error, match="Credential provider failed"):
        _s3_database(connection)._init_s3_auth()

    assert len(connection.statements) == 1
