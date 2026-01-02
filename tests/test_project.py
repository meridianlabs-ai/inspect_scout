"""Tests for the project configuration system."""

from pathlib import Path

import pytest
from inspect_scout._project import (
    ProjectConfig,
    create_default_project,
    find_git_root,
    find_project_file,
    load_project_config,
)


class TestFindGitRoot:
    """Tests for find_git_root function."""

    def test_finds_git_root_in_repo(self, tmp_path: Path) -> None:
        """Should find .git directory when present."""
        # Create a fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        subdir = tmp_path / "sub" / "nested"
        subdir.mkdir(parents=True)

        result = find_git_root(subdir)
        assert result == tmp_path

    def test_returns_none_when_no_git(self, tmp_path: Path) -> None:
        """Should return None when no .git directory exists."""
        subdir = tmp_path / "sub" / "nested"
        subdir.mkdir(parents=True)

        result = find_git_root(subdir)
        assert result is None


class TestFindProjectFile:
    """Tests for find_project_file function."""

    def test_finds_project_in_current_dir(self, tmp_path: Path) -> None:
        """Should find scout.yaml in the starting directory."""
        project_file = tmp_path / "scout.yaml"
        project_file.write_text("name: test")

        result = find_project_file(tmp_path)
        assert result == project_file

    def test_finds_project_in_parent_dir(self, tmp_path: Path) -> None:
        """Should find scout.yaml in parent directory."""
        project_file = tmp_path / "scout.yaml"
        project_file.write_text("name: test")
        subdir = tmp_path / "sub" / "nested"
        subdir.mkdir(parents=True)

        result = find_project_file(subdir)
        assert result == project_file

    def test_stops_at_git_root(self, tmp_path: Path) -> None:
        """Should not search above git root."""
        # Create project file above git root
        project_file = tmp_path / "scout.yaml"
        project_file.write_text("name: test")

        # Create git repo in subdir
        git_repo = tmp_path / "repo"
        git_repo.mkdir()
        (git_repo / ".git").mkdir()

        # Search from inside the repo
        search_dir = git_repo / "sub"
        search_dir.mkdir()

        result = find_project_file(search_dir)
        assert result is None

    def test_returns_none_when_no_project(self, tmp_path: Path) -> None:
        """Should return None when no scout.yaml exists."""
        subdir = tmp_path / "sub"
        subdir.mkdir()

        result = find_project_file(subdir)
        assert result is None


class TestLoadProjectConfig:
    """Tests for load_project_config function."""

    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        """Should load a valid scout.yaml file."""
        project_file = tmp_path / "scout.yaml"
        project_file.write_text(
            """
name: my-project
transcripts: ./logs
results: ./scans
model: openai/gpt-4o
log_level: warning
"""
        )

        config = load_project_config(project_file)
        assert config.name == "my-project"
        assert config.transcripts == "./logs"
        assert config.results == "./scans"
        assert config.model == "openai/gpt-4o"
        assert config.log_level == "warning"

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
        assert config.transcripts == "./transcripts"
        assert config.results == "./scans"

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
        assert config.transcripts == "./transcripts"

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
        from inspect_scout._scanjob import ScanJobConfig

        assert issubclass(ProjectConfig, ScanJobConfig)

    def test_has_all_scanjob_fields(self) -> None:
        """ProjectConfig should have all ScanJobConfig fields."""
        config = ProjectConfig(
            name="test",
            transcripts="./logs",
            results="./scans",
            model="openai/gpt-4o",
            max_transcripts=25,
            tags=["tag1"],
            metadata={"key": "value"},
        )
        assert config.name == "test"
        assert config.transcripts == "./logs"
        assert config.results == "./scans"
        assert config.model == "openai/gpt-4o"
        assert config.max_transcripts == 25
        assert config.tags == ["tag1"]
        assert config.metadata == {"key": "value"}
