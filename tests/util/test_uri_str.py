"""Tests for UriStr branded type and conversion functions."""

from pathlib import Path

import pytest
from inspect_scout._util.path_str import PathStr, as_path, make_path
from inspect_scout._util.uri_str import as_uri, make_uri
from upath import UPath


class TestMakeUri:
    """Tests for make_uri function."""

    @pytest.mark.parametrize(
        ("input_path", "expected_suffix"),
        [
            (Path("/tmp/file.txt"), "/tmp/file.txt"),
            (Path("/tmp/foo bar.txt"), "/tmp/foo%20bar.txt"),
            (Path("/tmp/foo@bar.txt"), "/tmp/foo%40bar.txt"),
            (Path("/tmp/a/b/c.txt"), "/tmp/a/b/c.txt"),
            (Path("/tmp/file#hash.txt"), "/tmp/file%23hash.txt"),
            (Path("/tmp/file?query.txt"), "/tmp/file%3Fquery.txt"),
            (Path("/tmp/100%done.txt"), "/tmp/100%25done.txt"),
            (Path("/tmp/file&name.txt"), "/tmp/file%26name.txt"),
            (Path("/tmp/file=name.txt"), "/tmp/file%3Dname.txt"),
        ],
        ids=[
            "simple",
            "space_encoded",
            "at_encoded",
            "nested",
            "hash_encoded",
            "question_encoded",
            "percent_encoded",
            "ampersand_encoded",
            "equals_encoded",
        ],
    )
    def test_encodes_path_to_uri(self, input_path: Path, expected_suffix: str) -> None:
        """make_uri percent-encodes special characters per RFC 3986."""
        result = make_uri(input_path)
        # URI may have platform-specific prefix (e.g., /private on macOS)
        assert result.startswith("file://")
        assert result.endswith(expected_suffix) or expected_suffix in result

    @pytest.mark.parametrize(
        "input_path",
        [
            Path("/tmp/file.txt"),
            UPath("/tmp/file.txt"),
            as_path("/tmp/file.txt"),
        ],
        ids=["Path", "UPath", "PathStr"],
    )
    def test_accepts_multiple_path_types(
        self, input_path: Path | UPath | PathStr
    ) -> None:
        """make_uri accepts Path, UPath, and PathStr."""
        result = make_uri(input_path)
        assert result.startswith("file://")
        assert "file.txt" in result

    def test_resolves_relative_paths(self) -> None:
        """make_uri resolves relative paths to absolute."""
        result = make_uri(Path("relative/path.txt"))
        assert result.startswith("file://")
        # Should be absolute (not contain ./relative)
        assert "/relative/path.txt" in result

    def test_resolves_dot_segments(self) -> None:
        """make_uri resolves . and .. segments."""
        result = make_uri(Path("/tmp/foo/../bar/./baz.txt"))
        assert "/tmp/bar/baz.txt" in result
        assert ".." not in result
        assert "/." not in result

    def test_returns_uristr_type(self) -> None:
        """make_uri returns UriStr (which is a str)."""
        result = make_uri(Path("/tmp/file.txt"))
        assert type(result) is str


class TestAsUri:
    """Tests for as_uri function."""

    @pytest.mark.parametrize(
        "raw_uri",
        [
            "file:///tmp/file.txt",
            "file:///tmp/foo%20bar.txt",
            "file:///tmp/foo%40bar.txt",
            "https://example.com/path",
            "s3://bucket/key",
        ],
        ids=[
            "file_simple",
            "file_encoded_space",
            "file_encoded_at",
            "https",
            "s3",
        ],
    )
    def test_returns_input_unchanged(self, raw_uri: str) -> None:
        """as_uri returns the input string unchanged (it's an assertion/cast)."""
        result = as_uri(raw_uri)
        assert result == raw_uri

    def test_returns_uristr_type(self) -> None:
        """as_uri returns UriStr (which is a str)."""
        result = as_uri("file:///tmp/file.txt")
        assert type(result) is str


class TestRoundTrip:
    """Tests for round-trip conversion between Path and URI."""

    @pytest.mark.parametrize(
        "original_path",
        [
            "/tmp/file.txt",
            "/tmp/foo bar.txt",
            "/tmp/foo@bar.txt",
            "/tmp/file#hash.txt",
            "/tmp/file?query.txt",
            "/tmp/100%done.txt",
            "/tmp/a/b/c/deep/nested/file.txt",
            "/tmp/unicode_\u03b1\u03b2\u03b3.txt",  # Greek letters
        ],
        ids=[
            "simple",
            "with_space",
            "with_at",
            "with_hash",
            "with_question",
            "with_percent",
            "deeply_nested",
            "unicode",
        ],
    )
    def test_path_to_uri_to_path(self, original_path: str) -> None:
        """Converting path -> URI -> path preserves the original path."""
        path = Path(original_path)
        uri = make_uri(path)
        result = make_path(uri)
        # Note: result may have platform prefix like /private on macOS
        assert result.endswith(original_path) or original_path in result

    @pytest.mark.parametrize(
        ("uri", "expected_path_suffix"),
        [
            ("file:///tmp/file.txt", "/tmp/file.txt"),
            ("file:///tmp/foo%20bar.txt", "/tmp/foo bar.txt"),
            ("file:///tmp/foo%40bar.txt", "/tmp/foo@bar.txt"),
        ],
        ids=["simple", "encoded_space", "encoded_at"],
    )
    def test_uri_to_path_to_uri(self, uri: str, expected_path_suffix: str) -> None:
        """Converting URI -> path -> URI preserves encoding semantics."""
        typed_uri = as_uri(uri)
        path = make_path(typed_uri)
        assert path.endswith(expected_path_suffix)
        # Round-trip back to URI
        new_uri = make_uri(Path(path))
        # The new URI should encode the same way
        assert expected_path_suffix.replace(" ", "%20").replace("@", "%40") in new_uri


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_filename(self) -> None:
        """Handles paths with empty-ish filenames."""
        uri = make_uri(Path("/tmp/"))
        path = make_path(uri)
        assert "/tmp" in path

    def test_multiple_encoded_chars(self) -> None:
        """Handles paths with multiple special characters."""
        original = Path("/tmp/a@b c#d?e%f.txt")
        uri = make_uri(original)
        path = make_path(uri)
        assert "@" in path
        assert " " in path
        assert "#" in path
        assert "?" in path
        assert "%" in path

    def test_already_decoded_path_encodes_correctly(self) -> None:
        """Paths with literal percent signs encode correctly."""
        # Path contains literal "100%"
        path = Path("/tmp/100%complete.txt")
        uri = make_uri(path)
        # The % should be encoded as %25
        assert "%25" in uri
        # Round-trip should preserve
        result = make_path(uri)
        assert "100%" in result
