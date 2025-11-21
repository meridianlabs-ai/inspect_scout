"""Tests for LazyJSONDict and SelectiveLazyJSONDict."""

from inspect_scout._transcript.util import LazyJSONDict


def test_lazy_json_dict_parses_dict() -> None:
    """Test that LazyJSONDict parses JSON dict on access."""
    data = LazyJSONDict({"config": '{"key": "value", "num": 42}'})
    result = data["config"]
    assert result == {"key": "value", "num": 42}
    assert isinstance(result, dict)


def test_lazy_json_dict_parses_array() -> None:
    """Test that LazyJSONDict parses JSON array on access."""
    data = LazyJSONDict({"tags": '["math", "reasoning"]'})
    result = data["tags"]
    assert result == ["math", "reasoning"]
    assert isinstance(result, list)


def test_lazy_json_dict_keeps_non_json_strings() -> None:
    """Test that LazyJSONDict doesn't parse regular strings."""
    data = LazyJSONDict({"name": "test", "model": "gpt-4"})
    assert data["name"] == "test"
    assert data["model"] == "gpt-4"


def test_lazy_json_dict_handles_invalid_json() -> None:
    """Test that LazyJSONDict handles invalid JSON gracefully."""
    data = LazyJSONDict({"bad": "{not valid json}"})
    result = data["bad"]
    assert result == "{not valid json}"
    assert isinstance(result, str)


def test_lazy_json_dict_caches_parsed_values() -> None:
    """Test that LazyJSONDict caches parsed values."""
    data = LazyJSONDict({"config": '{"key": "value"}'})
    # First access - should parse
    result1 = data["config"]
    # Second access - should return cached
    result2 = data["config"]
    assert result1 == result2
    assert result1 is result2  # Same object


def test_lazy_json_dict_get_method() -> None:
    """Test that get() method works with lazy parsing."""
    data = LazyJSONDict({"config": '{"key": "value"}'})
    result = data.get("config")
    assert result == {"key": "value"}
    # Test with default
    result = data.get("missing", "default")
    assert result == "default"


def test_selective_lazy_json_dict_only_parses_specified_keys() -> None:
    """Test that SelectiveLazyJSONDict only parses specified keys."""
    data = LazyJSONDict(
        {"config": '{"key": "value"}', "data": "[1,2,3]", "name": "test"},
        json_keys=["config", "data"],
    )
    # Should parse config
    assert data["config"] == {"key": "value"}
    assert isinstance(data["config"], dict)
    # Should parse data
    assert data["data"] == [1, 2, 3]
    assert isinstance(data["data"], list)
    # Should NOT parse name (not in json_keys)
    assert data["name"] == "test"
    assert isinstance(data["name"], str)


def test_selective_lazy_json_dict_with_list_of_keys() -> None:
    """Test that SelectiveLazyJSONDict accepts list of keys."""
    data = LazyJSONDict({"config": '{"key": "value"}'}, json_keys=["config"])
    assert data["config"] == {"key": "value"}


def test_lazy_json_dict_with_empty_json_keys() -> None:
    """Test that LazyJSONDict with empty json_keys doesn't parse."""
    data = LazyJSONDict({"config": '{"key": "value"}'}, json_keys=[])
    # Should not parse anything (empty set means no keys to parse)
    assert data["config"] == '{"key": "value"}'
    assert isinstance(data["config"], str)


def test_lazy_json_dict_none_json_keys_uses_auto_detection() -> None:
    """Test that LazyJSONDict with json_keys=None uses auto-detection."""
    data = LazyJSONDict({"config": '{"key": "value"}'}, json_keys=None)
    # Should parse (None means auto-detection mode)
    assert data["config"] == {"key": "value"}
    assert isinstance(data["config"], dict)


# Tests for to_json_string() edge cases


def test_to_json_string_with_special_characters_in_keys() -> None:
    """Test to_json_string handles special characters in keys."""
    import json

    data = LazyJSONDict(
        {
            'key"with"quotes': "value1",
            "key\\with\\backslashes": "value2",
            "key\nwith\nnewlines": "value3",
            "key\twith\ttabs": "value4",
        }
    )
    result = json.loads(data.to_json_string())
    assert result['key"with"quotes'] == "value1"
    assert result["key\\with\\backslashes"] == "value2"
    assert result["key\nwith\nnewlines"] == "value3"
    assert result["key\twith\ttabs"] == "value4"


def test_to_json_string_with_unicode() -> None:
    """Test to_json_string handles unicode in keys and values."""
    import json

    data = LazyJSONDict(
        {
            "emoji": "🚀",
            "chinese": "你好",
            "arabic": "مرحبا",
            "key_🔥": "fire",
            "nested": '{"unicode": "🎉"}',
        }
    )
    result = json.loads(data.to_json_string())
    assert result["emoji"] == "🚀"
    assert result["chinese"] == "你好"
    assert result["arabic"] == "مرحبا"
    assert result["key_🔥"] == "fire"
    assert result["nested"] == {"unicode": "🎉"}


def test_to_json_string_with_nested_json() -> None:
    """Test to_json_string handles deeply nested JSON structures."""
    import json

    data = LazyJSONDict(
        {
            "simple": "value",
            "nested": '{"level1": {"level2": {"level3": {"level4": "deep"}}}}',
            "nested_array": '{"items": [{"id": 1}, {"id": 2, "nested": {"key": "val"}}]}',
        }
    )
    result = json.loads(data.to_json_string())
    assert result["simple"] == "value"
    assert result["nested"]["level1"]["level2"]["level3"]["level4"] == "deep"
    assert result["nested_array"]["items"][1]["nested"]["key"] == "val"


def test_to_json_string_with_all_json_types() -> None:
    """Test to_json_string handles all JSON value types."""
    import json

    data = LazyJSONDict(
        {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "bool_true": True,
            "bool_false": False,
            "null": None,
            "array": "[1, 2, 3]",
            "object": '{"key": "value"}',
            "empty_string": "",
            "empty_array": "[]",
            "empty_object": "{}",
        }
    )
    result = json.loads(data.to_json_string())
    assert result["string"] == "text"
    assert result["number"] == 42
    assert result["float"] == 3.14
    assert result["bool_true"] is True
    assert result["bool_false"] is False
    assert result["null"] is None
    assert result["array"] == [1, 2, 3]
    assert result["object"] == {"key": "value"}
    assert result["empty_string"] == ""
    assert result["empty_array"] == []
    assert result["empty_object"] == {}


def test_to_json_string_with_mixed_parsed_and_unparsed() -> None:
    """Test to_json_string with some fields parsed and some unparsed."""
    import json

    data = LazyJSONDict(
        {
            "unparsed_dict": '{"key": "value"}',
            "unparsed_array": "[1, 2, 3]",
            "plain_string": "text",
            "number": 42,
        }
    )
    # Parse only the dict
    _ = data["unparsed_dict"]

    result = json.loads(data.to_json_string())
    assert result["unparsed_dict"] == {"key": "value"}
    assert result["unparsed_array"] == [1, 2, 3]
    assert result["plain_string"] == "text"
    assert result["number"] == 42


def test_to_json_string_with_strings_that_look_like_json_but_arent() -> None:
    """Test to_json_string handles strings that start with { or [ but aren't valid JSON."""
    import json

    data = LazyJSONDict(
        {
            "invalid_object": "{not valid json}",
            "invalid_array": "[also not valid",
            "looks_like_json": '{"valid": "json"}',
        }
    )
    # Access to trigger parsing attempt (will fail for invalid ones)
    _ = data["invalid_object"]
    _ = data["invalid_array"]

    result = json.loads(data.to_json_string())
    assert result["invalid_object"] == "{not valid json}"
    assert result["invalid_array"] == "[also not valid"
    assert result["looks_like_json"] == {"valid": "json"}


def test_to_json_string_with_empty_dict() -> None:
    """Test to_json_string handles empty dictionary."""
    import json

    data = LazyJSONDict({})
    result = data.to_json_string()
    assert result == "{}"
    assert json.loads(result) == {}


def test_to_json_string_with_special_json_characters_in_values() -> None:
    """Test to_json_string handles special JSON characters in string values."""
    import json

    data = LazyJSONDict(
        {
            "quotes": 'He said "hello"',
            "backslash": "path\\to\\file",
            "newlines": "line1\nline2",
            "tabs": "col1\tcol2",
            "mixed": 'Special: "\\\n\t',
        }
    )
    result = json.loads(data.to_json_string())
    assert result["quotes"] == 'He said "hello"'
    assert result["backslash"] == "path\\to\\file"
    assert result["newlines"] == "line1\nline2"
    assert result["tabs"] == "col1\tcol2"
    assert result["mixed"] == 'Special: "\\\n\t'


def test_to_json_string_with_json_containing_escaped_characters() -> None:
    """Test to_json_string preserves escaped characters in JSON strings."""
    import json

    # JSON string with already-escaped content
    data = LazyJSONDict(
        {
            "escaped": '{"path": "C:\\\\Users\\\\test", "quote": "He said \\"hi\\""}',
            "plain": "simple",
        }
    )
    result = json.loads(data.to_json_string())
    assert result["escaped"]["path"] == "C:\\Users\\test"
    assert result["escaped"]["quote"] == 'He said "hi"'
    assert result["plain"] == "simple"


def test_to_json_string_with_very_large_nested_structure() -> None:
    """Test to_json_string handles large nested structures."""
    import json
    from typing import Any

    # Create a deeply nested structure
    nested: dict[str, Any] = {"level": 0}
    current: dict[str, Any] = nested
    for i in range(1, 50):
        current["next"] = {"level": i}
        current = current["next"]

    data = LazyJSONDict(
        {
            "simple": "value",
            "large_nested": json.dumps(nested, separators=(",", ":")),
        }
    )
    result = json.loads(data.to_json_string())
    assert result["simple"] == "value"
    # Verify deep nesting preserved
    current_result: Any = result["large_nested"]
    for i in range(50):
        assert current_result["level"] == i
        if i < 49:
            current_result = current_result["next"]


def test_to_json_string_with_array_of_complex_objects() -> None:
    """Test to_json_string handles arrays with complex objects."""
    import json

    data = LazyJSONDict(
        {
            "users": '[{"id": 1, "name": "Alice", "tags": ["admin", "user"]}, '
            '{"id": 2, "name": "Bob", "settings": {"theme": "dark"}}]',
            "count": 2,
        }
    )
    result = json.loads(data.to_json_string())
    assert result["count"] == 2
    assert len(result["users"]) == 2
    assert result["users"][0]["name"] == "Alice"
    assert result["users"][0]["tags"] == ["admin", "user"]
    assert result["users"][1]["settings"]["theme"] == "dark"


def test_to_json_string_preserves_json_number_formats() -> None:
    """Test to_json_string preserves different number formats in JSON."""
    import json

    data = LazyJSONDict(
        {
            "numbers": '{"int": 42, "float": 3.14, "sci": 1e10, "negative": -100}',
            "plain_int": 100,
            "plain_float": 2.5,
        }
    )
    result = json.loads(data.to_json_string())
    assert result["numbers"]["int"] == 42
    assert result["numbers"]["float"] == 3.14
    assert result["numbers"]["sci"] == 1e10
    assert result["numbers"]["negative"] == -100
    assert result["plain_int"] == 100
    assert result["plain_float"] == 2.5
