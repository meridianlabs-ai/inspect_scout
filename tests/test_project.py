"""Tests for the project configuration system."""

from pathlib import Path

import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_scout._project import (
    ProjectConfig,
    create_default_project,
    find_local_project_file,
    load_project_config,
    merge_configs,
)
from inspect_scout._scanspec import ScannerSpec, Worklist
from inspect_scout._util.constants import DEFAULT_SCANS_DIR, DEFAULT_TRANSCRIPTS_DIR


class TestLoadProjectConfig:
    """Tests for load_project_config function."""

    def test_loads_with_tags_and_metadata(self, tmp_path: Path) -> None:
        """Should load tags and metadata."""
        project_file = tmp_path / "scout.yaml"
        project_file.write_text(
            """
name: test
tags:
  - production
  - safety
metadata:
  team: research
  version: 1
"""
        )

        config = load_project_config(project_file)
        assert config.tags == ["production", "safety"]
        assert config.metadata == {"team": "research", "version": 1}


class TestCreateDefaultProject:
    """Tests for create_default_project function."""

    def test_uses_transcripts_dir_if_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should use ./transcripts if it exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "transcripts").mkdir()

        config = create_default_project()
        assert config.transcripts == DEFAULT_TRANSCRIPTS_DIR
        assert config.scans == DEFAULT_SCANS_DIR

    def test_uses_logs_dir_if_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should use ./logs if transcripts doesn't exist but logs does."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "logs").mkdir()

        config = create_default_project()
        assert config.transcripts == "./logs"

    def test_prefers_transcripts_over_logs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should prefer ./transcripts over ./logs when both exist."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "transcripts").mkdir()
        (tmp_path / "logs").mkdir()

        config = create_default_project()
        assert config.transcripts == DEFAULT_TRANSCRIPTS_DIR

    def test_none_transcripts_when_neither_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should set transcripts to None when neither dir exists."""
        monkeypatch.chdir(tmp_path)

        config = create_default_project()
        assert config.transcripts is None


class TestProjectConfig:
    """Tests for ProjectConfig class."""

    def test_extends_scanjob_config(self) -> None:
        """ProjectConfig should extend ScanJobConfig."""
        from inspect_scout._scanjob_config import ScanJobConfig

        assert issubclass(ProjectConfig, ScanJobConfig)

    def test_has_all_scanjob_fields(self) -> None:
        """ProjectConfig should have all ScanJobConfig fields."""
        config = ProjectConfig(
            name="test",
            transcripts="./logs",
            scans=DEFAULT_SCANS_DIR,
            model="openai/gpt-4o",
            max_transcripts=25,
            tags=["tag1"],
            metadata={"key": "value"},
        )
        assert config.name == "test"
        assert config.transcripts == "./logs"
        assert config.scans == DEFAULT_SCANS_DIR
        assert config.model == "openai/gpt-4o"
        assert config.max_transcripts == 25
        assert config.tags == ["tag1"]
        assert config.metadata == {"key": "value"}


class TestMergeConfigs:
    """Tests for merge_configs function."""

    def test_simple_field_override(self) -> None:
        """Override should win for simple fields when present."""
        base = ProjectConfig(name="base", transcripts="./logs", log_level="info")
        override = ProjectConfig(log_level="debug")

        result = merge_configs(base, override)
        assert result.name == "base"  # Not overridden
        assert result.transcripts == "./logs"  # Not overridden
        assert result.log_level == "debug"  # Overridden

    def test_simple_field_fallback(self) -> None:
        """Base value should be used when override doesn't specify field."""
        base = ProjectConfig(
            name="base",
            transcripts="./logs",
            max_transcripts=50,
            max_processes=8,
        )
        override = ProjectConfig(name="override")

        result = merge_configs(base, override)
        assert result.name == "override"
        assert result.transcripts == "./logs"
        assert result.max_transcripts == 50
        assert result.max_processes == 8

    def test_union_tags_merged_and_deduplicated(self) -> None:
        """Tags should be merged with deduplication."""
        base = ProjectConfig(tags=["a", "b"])
        override = ProjectConfig(tags=["b", "c"])

        result = merge_configs(base, override)
        assert result.tags == ["a", "b", "c"]

    def test_union_metadata_override_wins(self) -> None:
        """Metadata should be merged with override winning on conflicts."""
        base = ProjectConfig(metadata={"key1": "base", "key2": "base"})
        override = ProjectConfig(metadata={"key2": "override", "key3": "override"})

        result = merge_configs(base, override)
        assert result.metadata == {
            "key1": "base",
            "key2": "override",
            "key3": "override",
        }

    def test_union_scanners_merged(self) -> None:
        """Scanners should be merged with override winning on conflicts."""
        base = ProjectConfig(
            scanners={"s1": ScannerSpec(name="scanner1", file="s1.py")}
        )
        override = ProjectConfig(
            scanners={"s2": ScannerSpec(name="scanner2", file="s2.py")}
        )

        result = merge_configs(base, override)
        assert result.scanners is not None
        assert "s1" in result.scanners
        assert "s2" in result.scanners

    def test_union_scanners_override_wins_conflict(self) -> None:
        """Override scanner should win when keys conflict."""
        base = ProjectConfig(
            scanners={"scanner": ScannerSpec(name="base_scanner", file="base.py")}
        )
        override = ProjectConfig(
            scanners={
                "scanner": ScannerSpec(name="override_scanner", file="override.py")
            }
        )

        result = merge_configs(base, override)
        assert result.scanners is not None
        assert isinstance(result.scanners, dict)
        assert result.scanners["scanner"].name == "override_scanner"

    def test_model_fields_atomic(self) -> None:
        """Model fields should be treated as atomic unit."""
        base = ProjectConfig(model="gpt-4", model_base_url="http://base")
        override = ProjectConfig(model="gpt-3.5")  # Only model, no base_url

        result = merge_configs(base, override)
        assert result.model == "gpt-3.5"
        assert result.model_base_url is None  # Should not inherit base_url

    def test_model_fields_base_used_when_no_override(self) -> None:
        """All model fields from base should be used when override has no model."""
        from inspect_ai.model import GenerateConfig

        base = ProjectConfig(
            model="gpt-4",
            model_base_url="http://base",
            generate_config=GenerateConfig(temperature=0.5),
        )
        override = ProjectConfig(name="override")

        result = merge_configs(base, override)
        assert result.model == "gpt-4"
        assert result.model_base_url == "http://base"
        assert result.generate_config is not None
        assert result.generate_config.temperature == 0.5

    def test_worklist_concatenated(self) -> None:
        """Worklists should be concatenated."""
        base = ProjectConfig(worklist=[Worklist(scanner="s1", transcripts=["t1"])])
        override = ProjectConfig(worklist=[Worklist(scanner="s2", transcripts=["t2"])])

        result = merge_configs(base, override)
        assert result.worklist is not None
        assert len(result.worklist) == 2
        assert result.worklist[0].scanner == "s1"
        assert result.worklist[1].scanner == "s2"

    def test_returns_same_type_as_base(self) -> None:
        """Result should be same type as base (ProjectConfig)."""
        base = ProjectConfig(name="base")
        override = ProjectConfig(name="override")

        result = merge_configs(base, override)
        assert type(result) is ProjectConfig


class TestFindLocalProjectFile:
    """Tests for find_local_project_file function."""

    def test_finds_local_file_when_exists(self, tmp_path: Path) -> None:
        """Should find scout.local.yaml when it exists."""
        project_file = tmp_path / "scout.yaml"
        local_file = tmp_path / "scout.local.yaml"
        project_file.write_text("name: test")
        local_file.write_text("log_level: debug")

        result = find_local_project_file(project_file)
        assert result == local_file

    def test_returns_none_when_no_local_file(self, tmp_path: Path) -> None:
        """Should return None when scout.local.yaml doesn't exist."""
        project_file = tmp_path / "scout.yaml"
        project_file.write_text("name: test")

        result = find_local_project_file(project_file)
        assert result is None


class TestLoadProjectConfigWithLocal:
    """Tests for loading project config with local overrides."""

    def test_merges_local_into_base(self, tmp_path: Path) -> None:
        """Should merge scout.local.yaml into scout.yaml."""
        project_file = tmp_path / "scout.yaml"
        local_file = tmp_path / "scout.local.yaml"

        project_file.write_text("""
name: my-project
transcripts: ./logs
log_level: warning
tags:
  - production
""")
        local_file.write_text("""
log_level: debug
tags:
  - dev
metadata:
  developer: me
""")

        config = load_project_config(project_file)

        assert config.name == "my-project"
        assert config.transcripts == "./logs"
        assert config.log_level == "debug"
        assert config.tags == ["production", "dev"]
        assert config.metadata == {"developer": "me"}

    def test_local_model_overrides_completely(self, tmp_path: Path) -> None:
        """Local model config should completely replace base model config."""
        project_file = tmp_path / "scout.yaml"
        local_file = tmp_path / "scout.local.yaml"

        project_file.write_text("""
name: my-project
model: openai/gpt-4
model_base_url: http://production
""")
        local_file.write_text("""
model: openai/gpt-3.5-turbo
""")

        config = load_project_config(project_file)

        assert config.model == "openai/gpt-3.5-turbo"
        assert config.model_base_url is None  # Not inherited from base

    def test_local_validation_errors_reported(self, tmp_path: Path) -> None:
        """Should report validation errors from scout.local.yaml."""
        project_file = tmp_path / "scout.yaml"
        local_file = tmp_path / "scout.local.yaml"

        project_file.write_text("name: test")
        local_file.write_text("invalid_field: value")

        with pytest.raises(PrerequisiteError) as exc_info:
            load_project_config(project_file)

        assert "scout.local.yaml" in str(exc_info.value)

    def test_loads_without_local_file(self, tmp_path: Path) -> None:
        """Should load normally when no scout.local.yaml exists."""
        project_file = tmp_path / "scout.yaml"
        project_file.write_text("""
name: my-project
transcripts: ./logs
""")

        config = load_project_config(project_file)

        assert config.name == "my-project"
        assert config.transcripts == "./logs"

    def test_default_name_applied_after_merge(self, tmp_path: Path) -> None:
        """Default name should use directory name after merging."""
        project_dir = tmp_path / "my-cool-project"
        project_dir.mkdir()
        project_file = project_dir / "scout.yaml"
        local_file = project_dir / "scout.local.yaml"

        project_file.write_text("transcripts: ./logs")
        local_file.write_text("log_level: debug")

        config = load_project_config(project_file)

        assert config.name == "my-cool-project"
