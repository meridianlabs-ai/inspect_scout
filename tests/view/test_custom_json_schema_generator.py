"""Tests for CustomJsonSchemaGenerator.

Verifies:
1. Field requiredness is determined by nullability, not defaults
2. JsonValue generates a proper oneOf schema instead of empty {}
"""

from typing import Any

import pytest
from inspect_scout._view._server_common import CustomJsonSchemaGenerator
from pydantic import BaseModel, Field, JsonValue


# Test models for requiredness
class NonNullableNoDefault(BaseModel):
    field: str


class NonNullableWithDefault(BaseModel):
    field: str = Field(default="value")


class NullableNoDefault(BaseModel):
    field: str | None


class NullableWithDefault(BaseModel):
    field: str | None = Field(default=None)


class NullableWithNonNoneDefault(BaseModel):
    field: str | None = Field(default="value")


class NestedNonNullable(BaseModel):
    nested: NonNullableNoDefault


class NestedNullable(BaseModel):
    nested: NonNullableNoDefault | None = Field(default=None)


# Test models for JsonValue
class WithJsonValue(BaseModel):
    value: JsonValue


class WithNullableJsonValue(BaseModel):
    value: JsonValue | None = Field(default=None)


def get_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Get JSON schema using CustomJsonSchemaGenerator."""
    return model.model_json_schema(schema_generator=CustomJsonSchemaGenerator)


@pytest.mark.parametrize(
    ("model", "field_name", "expected_required"),
    [
        # Non-nullable fields are always required
        (NonNullableNoDefault, "field", True),
        (NonNullableWithDefault, "field", True),
        # Nullable fields are never required
        (NullableNoDefault, "field", False),
        (NullableWithDefault, "field", False),
        (NullableWithNonNoneDefault, "field", False),
        # Nested models follow same rules
        (NestedNonNullable, "nested", True),
        (NestedNullable, "nested", False),
    ],
    ids=[
        "str_no_default",
        "str_with_default",
        "str|None_no_default",
        "str|None_default_None",
        "str|None_default_value",
        "nested_non_nullable",
        "nested_nullable",
    ],
)
def test_field_requiredness(
    model: type[BaseModel], field_name: str, expected_required: bool
) -> None:
    schema = get_schema(model)
    required = schema.get("required", [])
    if expected_required:
        assert field_name in required
    else:
        assert field_name not in required


def test_default_pydantic_treats_defaulted_fields_as_optional() -> None:
    """Document difference: default Pydantic makes fields with defaults optional."""
    schema = NonNullableWithDefault.model_json_schema()
    assert "field" not in schema.get("required", [])

    # Our custom generator keeps non-nullable fields required
    custom_schema = get_schema(NonNullableWithDefault)
    assert "field" in custom_schema.get("required", [])


def test_json_value_generates_proper_schema() -> None:
    """JsonValue should generate a proper oneOf schema, not empty {}."""
    schema = get_schema(WithJsonValue)
    defs = schema.get("$defs", {})

    assert "JsonValue" in defs
    json_value_schema = defs["JsonValue"]

    # Should not be empty
    assert json_value_schema != {}

    # Should be a oneOf with all JSON primitive types
    assert "oneOf" in json_value_schema
    one_of = json_value_schema["oneOf"]

    types = {item.get("type") for item in one_of if "type" in item}
    assert types == {
        "null",
        "boolean",
        "integer",
        "number",
        "string",
        "array",
        "object",
    }


def test_json_value_is_not_recursive() -> None:
    """JsonValue uses non-recursive schema (openapi-typescript can't handle recursive)."""
    schema = get_schema(WithJsonValue)
    json_value_schema = schema["$defs"]["JsonValue"]

    # Array items should be {} (any), not a $ref to JsonValue
    array_schema = next(
        s for s in json_value_schema["oneOf"] if s.get("type") == "array"
    )
    assert array_schema["items"] == {}

    # Object additionalProperties should be {} (any), not a $ref to JsonValue
    object_schema = next(
        s for s in json_value_schema["oneOf"] if s.get("type") == "object"
    )
    assert object_schema["additionalProperties"] == {}


def test_default_pydantic_json_value_is_empty() -> None:
    """Document difference: default Pydantic generates empty {} for JsonValue."""
    schema = WithJsonValue.model_json_schema()
    assert schema["$defs"]["JsonValue"] == {}

    # Our custom generator provides proper typing
    custom_schema = get_schema(WithJsonValue)
    assert custom_schema["$defs"]["JsonValue"] != {}
