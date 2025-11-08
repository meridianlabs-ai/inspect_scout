from typing import Type, TypeVar

from inspect_ai.util import JSONSchema
from pydantic import BaseModel

ST = TypeVar("ST", bound=BaseModel)


def structured_schema(type: Type[ST]) -> JSONSchema:
    # default schema extracted from BaseModel
    schema = type.model_json_schema(by_alias=False)

    # now see if we can find doc comments as descriptions

    return JSONSchema.model_validate(schema)
