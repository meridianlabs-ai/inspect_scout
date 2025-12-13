import inspect
import json
from typing import (
    Any,
    Callable,
    NoReturn,
    Type,
    TypeVar,
    get_args,
    get_origin,
)

from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.json import to_json_str_safe
from inspect_ai.model import (
    ChatMessage,
    ChatMessageTool,
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
    execute_tools,
    get_model,
)
from inspect_ai.tool import ToolDef, ToolFunction, ToolParams
from inspect_ai.util import JSONSchema
from pydantic import BaseModel, Field, create_model

from inspect_scout._llm_scanner.types import AnswerStructured
from inspect_scout._scanner.result import Reference, Result, as_resultset
from inspect_scout._util.refusal import generate_retry_refusals


async def structured_generate(
    input: str | list[ChatMessage],
    schema: JSONSchema,
    answer_tool: str | None = "answer",
    model: str | Model | None = None,
    max_attempts: int = 3,
    retry_refusals: int = 3,
) -> tuple[dict[str, Any] | None, list[ChatMessage], ModelOutput]:
    # resolve input
    input = [ChatMessageUser(content=input)] if isinstance(input, str) else input

    # resolve model
    model = get_model(model)

    # create a dynamic tool definition for the answer tool
    # use module-level function to ensure picklability
    answer_tooldef = ToolDef(
        tool=_answer_tool_impl,
        name=answer_tool,
        description="Use this tool to submit your final answer.",
        parameters=ToolParams(
            type="object",
            properties=schema.properties or {},
            required=schema.required or [],
        ),
    )

    # setup initial values for messages and output (we will return these)
    value: dict[str, Any] | None = None
    messages = input.copy()
    output: ModelOutput

    # setup a generate loop that will run until a successful call to the
    # anwser tool is made
    attempts = 0
    while attempts < max_attempts:
        output = await generate_retry_refusals(
            model,
            input=messages,
            tools=[answer_tooldef],
            tool_choice=ToolFunction(answer_tooldef.name),
            config=GenerateConfig(parallel_tool_calls=False),
            retry_refusals=retry_refusals,
        )
        messages.append(output.message)

        # if there we no tool calls then we need to insert a user message to
        # tell the model to keep going
        if len(output.message.tool_calls or []) == 0:
            messages.append(
                ChatMessageUser(
                    content=f"Please use the {answer_tool}() tool to report your answer."
                )
            )

        # check for a call to the 'answer' tool
        answer_tool_call = next(
            (
                tool_call
                for tool_call in (output.message.tool_calls or [])
                if tool_call.function == answer_tool
            ),
            None,
        )
        if answer_tool_call:
            # execute the tool calls (this will take care of validating the
            # answer tool parameters and providing feedback for invalid cases)
            execute_messages, execute_output = await execute_tools(
                messages=messages, tools=[answer_tooldef]
            )
            messages.extend(execute_messages)
            if execute_output is not None:
                output = execute_output

            # exit if there was a successful call of the answer tool
            if isinstance(messages[-1], ChatMessageTool):
                tool_message = messages[-1]
                if tool_message.error is None:
                    # set the value to the object return by the model and break
                    value = answer_tool_call.arguments
                    output.completion = to_json_str_safe(answer_tool_call.arguments)
                    break

        # keep going
        attempts += 1

    # return resultd
    return value, messages, output


ST = TypeVar("ST", bound=BaseModel)


def structured_schema(answer: AnswerStructured) -> JSONSchema:
    # Augment the type with an explanation field if it doesn't have one
    answer_type, result_set = structured_answer_type(answer)
    augmented_type = augment_type_with_explanation(answer_type)

    # validate descriptions on all fields including nested BaseModel types
    # we use validate_nested_models to handle nested BaseModel types properly
    # (Pydantic uses $ref for nested models which complicates JSON schema validation)
    missing_descriptions = validate_nested_models(augmented_type)
    if missing_descriptions:
        raise_missing_descriptions(missing_descriptions)

    # For result sets, synthesize a wrapper schema with a single list field
    if result_set is not False:
        # Determine the field name for the results list
        field_name = "results" if result_set is True else result_set

        # Get the schema for the item type
        item_schema = augmented_type.model_json_schema(by_alias=False)

        # Create a wrapper schema with a single list field containing items of this type
        wrapper_schema = {
            "type": "object",
            "properties": {
                field_name: {
                    "type": "array",
                    "items": item_schema,
                    "description": f"List of {augmented_type.__name__} items",
                }
            },
            "required": [field_name],
        }

        # If the item schema has $defs, include them in the wrapper
        if "$defs" in item_schema:
            wrapper_schema["$defs"] = item_schema["$defs"]

        return JSONSchema.model_validate(wrapper_schema)
    else:
        # For single results, return the schema as-is
        return JSONSchema.model_validate(
            augmented_type.model_json_schema(by_alias=False)
        )


def structured_answer_type(answer: AnswerStructured) -> tuple[type[BaseModel], bool]:
    if get_origin(answer.type) is list:
        args = get_args(answer.type)
        if not args or not issubclass(args[0], BaseModel):
            raise ValueError("List must be parameterized with BaseModel subclass")
        answer_type = args[0]
        result_set = True
    else:
        answer_type = answer.type
        result_set = False
    return answer_type, result_set


def structured_result(
    answer: AnswerStructured,
    output: ModelOutput,
    extract_references: Callable[[str], list[Reference]],
) -> Result:
    """Convert structured model output to Result(s).

    Args:
        answer: The AnswerStructured configuration.
        output: The ModelOutput containing the validated JSON.
        extract_references: Function to extract references from text.

    Returns:
        A Result object
    """
    # parse out type info
    answer_type, result_set = structured_answer_type(answer)

    # Augment the type with an explanation field if it doesn't have one
    augmented_type = augment_type_with_explanation(answer_type)

    # For single results, parse directly into the type
    # For result sets, we need to extract the list from the synthesized wrapper
    if result_set is False:
        parsed = augmented_type.model_validate_json(output.completion, by_name=True)
    else:
        # Parse as a generic dict first to extract the list
        wrapper_data = json.loads(output.completion)

        # Determine the field name
        field_name = "results" if result_set is True else result_set

        # Extract the list from the wrapper
        if field_name not in wrapper_data:
            raise ValueError(f"Expected field '{field_name}' in result set wrapper")

        list_data = wrapper_data[field_name]
        if not isinstance(list_data, list):
            raise ValueError(f"Field '{field_name}' must be a list")

        # We'll handle this list below, so set parsed to None for now
        parsed = None

    # Helper: Find field value by name or alias
    def get_field_by_name_or_alias(
        obj: BaseModel, target_name: str
    ) -> tuple[str | None, Any]:
        """Get field value by field name or alias.

        Returns:
            Tuple of (actual_field_name, field_value) or (None, None) if not found.
        """
        model_fields = type(obj).model_fields

        # Check direct field name first
        if target_name in model_fields:
            return target_name, getattr(obj, target_name)

        # Check for alias
        for field_name, field_info in model_fields.items():
            if field_info.alias == target_name:
                return field_name, getattr(obj, field_name)

        return None, None

    # Helper: Create a Result from a parsed object
    def create_result_from_parsed(obj: BaseModel) -> Result:
        """Create a Result from a parsed BaseModel object.

        Args:
            obj: The parsed BaseModel instance.

        Returns:
            A Result object.
        """
        # Extract explanation (required)
        explanation_field, explanation_value = get_field_by_name_or_alias(
            obj, "explanation"
        )
        if explanation_field is None:
            raise ValueError("Missing required 'explanation' field")

        # Extract label (optional - can be used to distinguish results in a result set)
        label_field, label_value = get_field_by_name_or_alias(obj, "label")

        # Determine the value
        exclude_from_metadata = {explanation_field}
        if label_field:
            exclude_from_metadata.add(label_field)

        # Look for field with alias="value"
        value: Any
        value_field, value_field_value = get_field_by_name_or_alias(obj, "value")
        if value_field:
            value = value_field_value
            exclude_from_metadata.add(value_field)
        # otherwise use the whole object
        else:
            value = obj.model_dump(exclude=exclude_from_metadata)

        # Collect metadata from remaining fields
        all_fields = obj.model_dump()

        # When the value already has the whole object we don't need metadata
        if value_field is None:
            metadata = None
        else:
            metadata = {
                k: v for k, v in all_fields.items() if k not in exclude_from_metadata
            }

        # Extract references from explanation
        references = extract_references(explanation_value)

        return Result(
            value=value,
            explanation=explanation_value,
            label=label_value,
            metadata=metadata if metadata else None,
            references=references,
        )

    # Handle result set (multiple results)
    if result_set is not False:
        # Parse each item in the list as an instance of the augmented type
        parsed_items = [
            augmented_type.model_validate(item, by_name=True) for item in list_data
        ]

        # Create a Result for each parsed item
        results = [create_result_from_parsed(item) for item in parsed_items]

        # Return as a result set
        return as_resultset(results)
    else:
        # Handle single result
        assert parsed is not None  # parsed is always set for single results
        return create_result_from_parsed(parsed)


def validate_nested_models(model_type: Type[BaseModel], path: str = "") -> list[str]:
    """Recursively validate nested BaseModel types have descriptions on all fields.

    Args:
        model_type: The BaseModel type to validate.
        path: The current property path (using dot notation).

    Returns:
        List of property paths that are missing descriptions.
    """
    missing_descriptions: list[str] = []

    for field_name, field_info in model_type.model_fields.items():
        current_path = f"{path}.{field_name}" if path else field_name

        # Check if field has a description
        if not field_info.description:
            missing_descriptions.append(current_path)

        # Check if this field's type is a nested BaseModel
        field_type = field_info.annotation
        if (
            field_type
            and inspect.isclass(field_type)
            and issubclass(field_type, BaseModel)
        ):
            # Recursively validate nested model
            missing_descriptions.extend(
                validate_nested_models(field_type, current_path)
            )
        elif field_type:
            # Check if it's a list of BaseModels
            origin = get_origin(field_type)
            if origin is list:
                args = get_args(field_type)
                if args and len(args) == 1:
                    inner_type = args[0]
                    if inspect.isclass(inner_type) and issubclass(
                        inner_type, BaseModel
                    ):
                        # Recursively validate list item type
                        missing_descriptions.extend(
                            validate_nested_models(inner_type, current_path)
                        )

    return missing_descriptions


def raise_missing_descriptions(missing_descriptions: list[str]) -> NoReturn:
    error_msg = "The following properties are missing descriptions:\n"
    error_msg += "\n".join(f"  - {prop}" for prop in missing_descriptions)
    error_msg += "\nThe description field is required for prompting the model to provide structured answers."
    raise PrerequisiteError(error_msg)


def augment_type_with_explanation(type: Type[ST]) -> Type[ST]:
    """Augment a type with an explanation field if it doesn't already have one.

    Args:
        type: The BaseModel type to check and potentially augment.

    Returns:
        The original type if it has an explanation field, or a new type
        with an explanation field added.
    """
    # Check if the type already has an explanation field (by name or alias)
    has_explanation = False
    if "explanation" in type.model_fields:
        has_explanation = True
    else:
        # Check for field with alias="explanation"
        for _, field_info in type.model_fields.items():
            if field_info.alias == "explanation":
                has_explanation = True
                break

    # If it already has explanation, return as-is
    if has_explanation:
        return type

    # Create a new type that extends the original with an explanation field
    new_fields = {
        "explanation": (
            str,
            Field(
                description="Please provide an explanation of the answer you have provided. It should include the message id's (e.g. '[M2]') to clarify which message(s) you are referring to."
            ),
        )
    }

    # Use create_model to dynamically create a new type
    augmented_type = create_model(
        f"{type.__name__}WithExplanation",
        __base__=type,
        **new_fields,  # type: ignore
    )

    return augmented_type  # type: ignore


# Module-level tool function for picklability in multiprocessing
async def _answer_tool_impl(**kwargs: Any) -> str:
    """Implementation of the answer tool for structured generation.

    This is defined at module level rather than as a local function
    to ensure it can be pickled when using multiprocessing.
    """
    return ""
