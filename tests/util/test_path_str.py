"""Tests for PathStr branded type and conversion functions."""

from pathlib import Path

import pytest
from inspect_scout._util.path_str import as_path, make_path
from inspect_scout._util.uri_str import as_uri
from upath import UPath


class TestMakePathFromPath:
    """Tests for make_path with Path input."""

    @pytest.mark.parametrize(
        ("input_path", "expected"),
        [
            (Path("/tmp/file.txt"), "/tmp/file.txt"),
            (Path("/tmp/foo bar.txt"), "/tmp/foo bar.txt"),
            (Path("/tmp/foo@bar.txt"), "/tmp/foo@bar.txt"),
            (Path("/tmp/a/b/c.txt"), "/tmp/a/b/c.txt"),
            (Path("."), "."),
            (Path("relative/path.txt"), "relative/path.txt"),
            (Path("/"), "/"),
            (
                Path("/tmp/file with spaces and @special.txt"),
                "/tmp/file with spaces and @special.txt",
            ),
        ],
        ids=[
            "simple_absolute",
            "with_space",
            "with_at_symbol",
            "nested_path",
            "current_dir",
            "relative_path",
            "root",
            "complex_name",
        ],
    )
    def test_converts_path_to_pathstr(self, input_path: Path, expected: str) -> None:
        """make_path converts Path to PathStr preserving the path string."""
        result = make_path(input_path)
        assert result == expected
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "input_path",
        [
            Path("/tmp/file.txt"),
            Path("/tmp/foo bar.txt"),
            Path("/tmp/foo@bar.txt"),
        ],
        ids=["simple", "with_space", "with_at"],
    )
    def test_returns_pathstr_type(self, input_path: Path) -> None:
        """make_path returns PathStr (which is a str)."""
        result = make_path(input_path)
        assert type(result) is str


class TestMakePathFromUPath:
    """Tests for make_path with UPath input."""

    @pytest.mark.parametrize(
        ("input_path", "expected"),
        [
            (UPath("/tmp/file.txt"), "/tmp/file.txt"),
            (UPath("/tmp/foo bar.txt"), "/tmp/foo bar.txt"),
            (UPath("/tmp/foo@bar.txt"), "/tmp/foo@bar.txt"),
        ],
        ids=["simple", "with_space", "with_at"],
    )
    def test_accepts_upath(self, input_path: UPath, expected: str) -> None:
        """make_path accepts UPath."""
        result = make_path(input_path)
        assert result == expected
        assert type(result) is str


class TestMakePathFromUriStr:
    """Tests for make_path with UriStr input (decodes percent-encoding)."""

    @pytest.mark.parametrize(
        ("uri", "expected"),
        [
            ("file:///tmp/file.txt", "/tmp/file.txt"),
            ("file:///tmp/foo%20bar.txt", "/tmp/foo bar.txt"),
            ("file:///tmp/foo%40bar.txt", "/tmp/foo@bar.txt"),
            ("file:///tmp/file%23hash.txt", "/tmp/file#hash.txt"),
            ("file:///tmp/file%3Fquery.txt", "/tmp/file?query.txt"),
            ("file:///tmp/100%25done.txt", "/tmp/100%done.txt"),
            ("file:///tmp/a/b/c.txt", "/tmp/a/b/c.txt"),
            (
                "file:///tmp/%E2%9C%93check.txt",
                "/tmp/\u2713check.txt",
            ),  # unicode checkmark
        ],
        ids=[
            "simple",
            "space_decoded",
            "at_decoded",
            "hash_decoded",
            "question_decoded",
            "percent_decoded",
            "nested",
            "unicode_decoded",
        ],
    )
    def test_decodes_uri_to_path(self, uri: str, expected: str) -> None:
        """make_path decodes percent-encoded characters from UriStr."""
        result = make_path(as_uri(uri))
        assert result == expected

    def test_returns_pathstr_type(self) -> None:
        """make_path returns PathStr (which is a str)."""
        result = make_path(as_uri("file:///tmp/file.txt"))
        assert type(result) is str

    def test_double_encoding_not_applied(self) -> None:
        """make_path doesn't double-decode (e.g., %2520 -> %20 -> space)."""
        # A URI where %25 represents a literal % in the path
        # So %2520 means the path contains literal "%20" (not a space)
        uri = as_uri("file:///tmp/file%2520name.txt")
        path = make_path(uri)
        # Should decode %25 -> % once, leaving 20 after it as literal
        assert "%20" in path  # literal %20 in filename


class TestAsPath:
    """Tests for as_path function."""

    @pytest.mark.parametrize(
        "raw_string",
        [
            "/tmp/file.txt",
            "/tmp/foo bar.txt",
            "/tmp/foo@bar.txt",
            "relative/path.txt",
            ".",
            "/",
            "/path/with/many/segments/file.txt",
            "/tmp/unicode_αβγ.txt",
            "/tmp/file%20name.txt",  # percent in path is literal, not encoding
        ],
        ids=[
            "simple_absolute",
            "with_space",
            "with_at_symbol",
            "relative",
            "current_dir",
            "root",
            "deep_nested",
            "unicode",
            "literal_percent",
        ],
    )
    def test_returns_input_unchanged(self, raw_string: str) -> None:
        """as_path returns the input string unchanged (it's an assertion/cast)."""
        result = as_path(raw_string)
        assert result == raw_string

    @pytest.mark.parametrize(
        "raw_string",
        [
            "/tmp/file.txt",
            "",
            "any string at all",
        ],
        ids=["valid_path", "empty", "arbitrary"],
    )
    def test_returns_pathstr_type(self, raw_string: str) -> None:
        """as_path returns PathStr (which is a str)."""
        result = as_path(raw_string)
        assert type(result) is str


class TestPathStrRoundTrip:
    """Tests for PathStr behavior in round-trip scenarios."""

    @pytest.mark.parametrize(
        "path",
        [
            Path("/tmp/file.txt"),
            Path("/tmp/foo bar.txt"),
            Path("/tmp/foo@bar.txt"),
            Path("relative/path.txt"),
        ],
        ids=["simple", "with_space", "with_at", "relative"],
    )
    def test_make_path_then_as_path_idempotent(self, path: Path) -> None:
        """Calling as_path on a PathStr is idempotent."""
        path_str = make_path(path)
        result = as_path(path_str)
        assert result == path_str

    @pytest.mark.parametrize(
        "path",
        [
            Path("/tmp/file.txt"),
            Path("/tmp/foo bar.txt"),
            Path("/tmp/foo@bar.txt"),
        ],
        ids=["simple", "with_space", "with_at"],
    )
    def test_pathstr_can_construct_path(self, path: Path) -> None:
        """PathStr can be used to construct a Path object."""
        path_str = make_path(path)
        reconstructed = Path(path_str)
        assert reconstructed == path
