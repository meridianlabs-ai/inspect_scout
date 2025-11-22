from unittest.mock import MagicMock, patch

from inspect_scout._scanspec import GIT_VERSION_UNKNOWN
from inspect_scout._util.revision import (
    bump_version,
    git_version_to_semver,
    parse_git_describe_to_semver,
)


class TestParseGitDescribeToSemver:
    """Tests for parse_git_describe_to_semver function."""

    def test_exact_tag_clean(self) -> None:
        """Test parsing exact tag without uncommitted changes."""
        result = parse_git_describe_to_semver("v0.2.2-0-g4ef4bfd")
        assert result == "0.2.2"

    def test_exact_tag_dirty(self) -> None:
        """Test parsing exact tag with uncommitted changes."""
        result = parse_git_describe_to_semver("v0.2.2-0-g4ef4bfd-dirty")
        assert result == "0.2.2+dirty"

    def test_post_release_clean(self) -> None:
        """Test parsing post-release version without uncommitted changes."""
        result = parse_git_describe_to_semver("v0.2.2-539-g4ef4bfd")
        assert result == "0.2.3-dev.539+g4ef4bfd"

    def test_post_release_dirty(self) -> None:
        """Test parsing post-release version with uncommitted changes."""
        result = parse_git_describe_to_semver("v0.2.2-539-g4ef4bfd-dirty")
        assert result == "0.2.3-dev.539+g4ef4bfd.dirty"

    def test_version_without_v_prefix(self) -> None:
        """Test parsing version without 'v' prefix."""
        result = parse_git_describe_to_semver("0.2.2-539-g4ef4bfd")
        assert result == "0.2.3-dev.539+g4ef4bfd"

    def test_single_commit_post_release(self) -> None:
        """Test parsing version with single commit after tag."""
        result = parse_git_describe_to_semver("v1.0.0-1-gabc1234")
        assert result == "1.0.1-dev.1+gabc1234"

    def test_major_minor_version(self) -> None:
        """Test parsing version with major.minor format."""
        result = parse_git_describe_to_semver("v1.2-10-gdef5678")
        assert result == "1.2.1-dev.10+gdef5678"

    def test_invalid_format_returns_unknown(self) -> None:
        """Test that invalid format returns GIT_VERSION_UNKNOWN."""
        result = parse_git_describe_to_semver("invalid-format")
        assert result == GIT_VERSION_UNKNOWN

    def test_no_tags_returns_unknown(self) -> None:
        """Test that output without tags returns GIT_VERSION_UNKNOWN."""
        result = parse_git_describe_to_semver("g4ef4bfd")
        assert result == GIT_VERSION_UNKNOWN


class TestBumpVersion:
    """Tests for bump_version function."""

    def test_bump_standard_semver(self) -> None:
        """Test bumping standard semantic version (major.minor.patch)."""
        assert bump_version("0.2.2") == "0.2.3"
        assert bump_version("1.0.0") == "1.0.1"
        assert bump_version("2.5.9") == "2.5.10"

    def test_bump_major_minor(self) -> None:
        """Test bumping major.minor version adds patch version."""
        assert bump_version("0.2") == "0.2.1"
        assert bump_version("1.0") == "1.0.1"

    def test_bump_major_only(self) -> None:
        """Test bumping major-only version adds minor and patch."""
        assert bump_version("0") == "0.0.1"
        assert bump_version("1") == "1.0.1"

    def test_bump_with_extra_parts(self) -> None:
        """Test bumping version with more than 3 parts (only patch is bumped)."""
        assert bump_version("1.2.3.4") == "1.2.4.4"


class TestGitVersionToSemver:
    """Tests for git_version_to_semver function with mocked git calls."""

    @patch("inspect_scout._util.revision.get_git_describe")
    def test_with_valid_git_output(self, mock_get_git_describe: MagicMock) -> None:
        """Test git_version_to_semver with valid git describe output."""
        mock_get_git_describe.return_value = "v0.2.2-539-g4ef4bfd"
        result = git_version_to_semver()
        assert result == "0.2.3-dev.539+g4ef4bfd"

    @patch("inspect_scout._util.revision.get_git_describe")
    def test_with_git_error(self, mock_get_git_describe: MagicMock) -> None:
        """Test git_version_to_semver when git command fails."""
        mock_get_git_describe.return_value = None
        result = git_version_to_semver()
        assert result == GIT_VERSION_UNKNOWN

    @patch("inspect_scout._util.revision.get_git_describe")
    def test_with_exact_tag(self, mock_get_git_describe: MagicMock) -> None:
        """Test git_version_to_semver when on exact tag."""
        mock_get_git_describe.return_value = "v1.0.0-0-gabc1234"
        result = git_version_to_semver()
        assert result == "1.0.0"

    @patch("inspect_scout._util.revision.get_git_describe")
    def test_with_dirty_working_tree(self, mock_get_git_describe: MagicMock) -> None:
        """Test git_version_to_semver with dirty working tree."""
        mock_get_git_describe.return_value = "v0.2.2-0-g4ef4bfd-dirty"
        result = git_version_to_semver()
        assert result == "0.2.2+dirty"
