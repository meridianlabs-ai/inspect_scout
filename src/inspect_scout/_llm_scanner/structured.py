import inspect
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
    Model,
    ModelOutput,
    execute_tools,
    get_model,
)
from inspect_ai.tool import ToolDef, ToolFunction, ToolParams
from inspect_ai.util import JSONSchema
from pydantic import BaseModel

from inspect_scout._llm_scanner.types import AnswerStructured
from inspect_scout._scanner.result import Reference, Result, result_set


async def structured_generate(
    input: str | list[ChatMessage],
    schema: JSONSchema,
    answer_tool: str | None = "answer",
    model: str | Model | None = None,
    max_attempts: int = 3,
) -> tuple[dict[str, Any] | None, list[ChatMessage], ModelOutput]:
    # resolve input
    input = [ChatMessageUser(content=input)] if isinstance(input, str) else input

    # resolve model
    model = get_model(model)

    # create a dynamic tool definition for the answer tool
    async def answer(**kwargs: Any) -> str:
        return ""

    answer_tooldef = ToolDef(
        tool=answer,
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
        output = await model.generate(
            input=messages,
            tools=[answer_tooldef],
            tool_choice=ToolFunction(answer_tooldef.name),
        )
        messages.append(output.message)

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
                output.completion = to_json_str_safe(answer_tool_call.arguments)

            # exit if there was a successful call of the answer tool
            if isinstance(messages[-1], ChatMessageTool):
                tool_message = messages[-1]
                if tool_message.error is None:
                    # set the value to the object return by the model and break
                    value = answer_tool_call.arguments
                    break

        # keep going
        attempts += 1

    # return resultd
    return value, messages, output


ST = TypeVar("ST", bound=BaseModel)


def structured_schema(type: Type[ST], result_set: bool) -> JSONSchema:
    # get the target type for validation (either the type itself for single,
    # or the inner type from the list field for multiple)
    target_type = get_target_type(type, result_set)

    # validate that the target type has required fields
    # (note: these requirements only apply to the target type, not nested types)
    validate_required_fields(target_type, result_set)

    # validate descriptions on all fields including nested BaseModel types
    # we use validate_nested_models to handle nested BaseModel types properly
    # (Pydantic uses $ref for nested models which complicates JSON schema validation)
    missing_descriptions = validate_nested_models(target_type)
    if missing_descriptions:
        raise_missing_descriptions(missing_descriptions)

    # return the schema for the original type (not the target type)
    return JSONSchema.model_validate(type.model_json_schema(by_alias=False))


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
        A Result object (or result_set if answer.result_set is True).
    """
    # Parse the validated JSON output into the Pydantic model
    parsed = answer.type.model_validate_json(output.completion)

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
    def create_result_from_parsed(obj: BaseModel, require_label: bool) -> Result:
        """Create a Result from a parsed BaseModel object.

        Args:
            obj: The parsed BaseModel instance.
            require_label: Whether to require a label field.

        Returns:
            A Result object.
        """
        # Extract explanation (required)
        explanation_field, explanation_value = get_field_by_name_or_alias(
            obj, "explanation"
        )
        if explanation_field is None:
            raise ValueError("Missing required 'explanation' field")

        # Extract label (required for result sets, optional otherwise)
        label_field, label_value = get_field_by_name_or_alias(obj, "label")
        if require_label and label_field is None:
            raise ValueError("Missing required 'label' field for result set")

        # Determine the value based on answer.result_value
        exclude_from_metadata = {explanation_field}
        if label_field:
            exclude_from_metadata.add(label_field)

        value: Any
        if answer.result_value == "true":
            value = True
        elif answer.result_value == "object":
            # Use the entire object minus explanation and label
            value = obj.model_dump(exclude=exclude_from_metadata)
        else:  # answer.result_value is None
            # Look for field with alias="value"
            value_field, value_field_value = get_field_by_name_or_alias(obj, "value")
            if value_field:
                value = value_field_value
                exclude_from_metadata.add(value_field)
            else:
                value = True

        # Collect metadata from remaining fields
        all_fields = obj.model_dump()

        # When result_value="object", the value already contains the non-special fields
        # so we don't duplicate them in metadata
        if answer.result_value == "object":
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
    if answer.result_set:
        # Extract the single list field from the wrapper
        fields = type(parsed).model_fields
        if len(fields) != 1:
            raise ValueError(
                f"Result set wrapper must have exactly one field, got {len(fields)}"
            )

        list_field_name = list(fields.keys())[0]
        list_value = getattr(parsed, list_field_name)

        if not isinstance(list_value, list):
            raise ValueError(f"Result set field '{list_field_name}' must be a list")

        # Create a Result for each item in the list
        results = [
            create_result_from_parsed(item, require_label=True) for item in list_value
        ]

        # Return as a result set
        return result_set(results)
    else:
        # Handle single result
        return create_result_from_parsed(parsed, require_label=False)


def get_target_type(type: Type[ST], result_set: bool) -> Type[BaseModel]:
    """Get the target type for field validation.

    For single results, returns the type itself.
    For multiple results, extracts and returns the inner type from the list field.
    """
    if not result_set:
        return type

    # For multiple results, extract the inner type from the list field
    fields = type.model_fields
    if len(fields) != 1:
        # This should have already been caught by get_validation_target
        raise PrerequisiteError(
            "For multiple results, the type must have exactly one field."
        )

    field_name = list(fields.keys())[0]
    field_info = fields[field_name]

    # Get the type annotation
    annotation = field_info.annotation

    # Check if it's a list type
    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        if args and len(args) == 1:
            inner_type = args[0]
            # Type narrowing: check if inner_type is a BaseModel subclass
            # Use inspect.isclass() to handle classes with custom metaclasses like Pydantic
            if inspect.isclass(inner_type):
                try:
                    if issubclass(inner_type, BaseModel):
                        return inner_type
                except TypeError:
                    # issubclass() can fail for some types
                    pass

    raise PrerequisiteError(
        f"Could not extract BaseModel type from list field '{field_name}'. "
        f"Annotation: {annotation}, Origin: {origin}, Args: {get_args(annotation) if origin else 'N/A'}"
    )


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


def validate_required_fields(target_type: Type[BaseModel], result_set: bool) -> None:
    """Validate that the target type has required fields.

    Args:
        target_type: The BaseModel type to validate.
        result_set: Whether expecting single or multiple results.

    Raises:
        PrerequisiteError: If required fields are missing.

    Notes:
        - 'explanation' field is always required (both single and multiple)
        - 'label' field is only required for multiple results
    """
    fields = target_type.model_fields

    # Helper to check if a field annotation is exactly str (required, not optional)
    def is_str_required(annotation: Any) -> bool:
        return annotation is str

    # Check for label field (only required for multiple results)
    if result_set:
        has_label = False
        if "label" in fields and is_str_required(fields["label"].annotation):
            has_label = True
        else:
            # Check for field with alias="label"
            for _field_name, field_info in fields.items():
                if field_info.alias == "label" and is_str_required(
                    field_info.annotation
                ):
                    has_label = True
                    break

        if not has_label:
            raise PrerequisiteError(
                f"The type '{target_type.__name__}' must have a required 'label' field of type str. "
                "This can be achieved with a field named 'label' or a field with alias='label'. "
                "The field cannot be Optional."
            )

    # Check for explanation field (always required)
    has_explanation = False
    if "explanation" in fields and is_str_required(fields["explanation"].annotation):
        has_explanation = True
    else:
        # Check for field with alias="explanation"
        for _field_name, field_info in fields.items():
            if field_info.alias == "explanation" and is_str_required(
                field_info.annotation
            ):
                has_explanation = True
                break

    if not has_explanation:
        raise PrerequisiteError(
            f"The type '{target_type.__name__}' must have a required 'explanation' field of type str. "
            "This can be achieved with a field named 'explanation' or a field with alias='explanation'. "
            "The field cannot be Optional."
        )
