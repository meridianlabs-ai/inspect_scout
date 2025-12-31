"""Tests for NullableIsOptionalJsonSchema.

Verifies that field requiredness is determined by nullability, not defaults:
- `str` -> required
- `str` with default -> required
- `str | None` -> optional
- `str | None` with default -> optional
"""

import pytest
from inspect_scout._view._server_common import NullableIsOptionalJsonSchema
from pydantic import BaseModel, Field


# Test models
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


def get_required_fields(model: type[BaseModel]) -> list[str]:
    """Get required field names using NullableIsOptionalJsonSchema."""
    schema = model.model_json_schema(schema_generator=NullableIsOptionalJsonSchema)
    return schema.get("required", [])  # type:ignore


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
    required = get_required_fields(model)
    if expected_required:
        assert field_name in required
    else:
        assert field_name not in required


def test_default_pydantic_treats_defaulted_fields_as_optional() -> None:
    """Document difference: default Pydantic makes fields with defaults optional."""
    schema = NonNullableWithDefault.model_json_schema()
    assert "field" not in schema.get("required", [])

    # Our custom generator keeps non-nullable fields required
    custom_schema = NonNullableWithDefault.model_json_schema(
        schema_generator=NullableIsOptionalJsonSchema
    )
    assert "field" in custom_schema.get("required", [])
