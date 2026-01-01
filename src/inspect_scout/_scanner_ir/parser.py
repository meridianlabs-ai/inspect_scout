"""Parser for scanner Python files using libcst.

Extracts scanner definitions from Python source code into an intermediate
representation (IR) that can be edited and regenerated.
"""

from __future__ import annotations

import ast
import re
from typing import Any

import libcst as cst

from .types import (
    GrepScannerSpec,
    LLMScannerSpec,
    ParseResult,
    ScannerDecoratorSpec,
    ScannerFile,
    StructuredAnswerSpec,
    StructuredField,
)


def parse_scanner_file(source: str) -> ParseResult:
    """Parse a scanner Python file into an IR.

    Parses the source code and extracts the scanner definition if it matches
    the editable patterns. Keeps the CST for later in-place editing.

    Args:
        source: Python source code containing a scanner definition.

    Returns:
        ParseResult with:
        - editable=True and scanner populated if the file matches editable patterns
        - editable=False and advanced_reason if the file is too complex
    """
    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError as e:
        return ParseResult(
            editable=False,
            source=source,
            advanced_reason=f"Syntax error: {e}",
        )

    # Find the @scanner decorated function
    scanner_func = _find_scanner_function(tree)
    if scanner_func is None:
        return ParseResult(
            editable=False,
            source=source,
            advanced_reason="No @scanner decorated function found",
        )

    # Parse decorator
    decorator_spec = _parse_scanner_decorator(scanner_func)

    # Find the return statement with llm_scanner or grep_scanner call
    scanner_call, scanner_type = _find_scanner_call(scanner_func)
    if scanner_call is None:
        return ParseResult(
            editable=False,
            source=source,
            advanced_reason="Uses custom scanner implementation",
        )

    # Parse the scanner call
    if scanner_type == "llm":
        llm_spec, advanced_reason = _parse_llm_scanner_call(scanner_call, tree)
        if llm_spec is None:
            return ParseResult(
                editable=False,
                source=source,
                advanced_reason=advanced_reason or "Could not parse llm_scanner call",
            )

        # Check for structured answer and parse Pydantic model
        structured_model = None
        if llm_spec.answer_type == "structured" and llm_spec.structured_spec:
            structured_model = llm_spec.structured_spec

        scanner_file = ScannerFile(
            function_name=scanner_func.name.value,
            decorator=decorator_spec,
            scanner_type="llm",
            llm_scanner=llm_spec,
            structured_model=structured_model,
        )

    else:  # grep
        grep_spec, advanced_reason = _parse_grep_scanner_call(scanner_call)
        if grep_spec is None:
            return ParseResult(
                editable=False,
                source=source,
                advanced_reason=advanced_reason or "Could not parse grep_scanner call",
            )

        scanner_file = ScannerFile(
            function_name=scanner_func.name.value,
            decorator=decorator_spec,
            scanner_type="grep",
            grep_scanner=grep_spec,
        )

    return ParseResult(
        editable=True,
        scanner=scanner_file,
        source=source,
    )


def _find_scanner_function(tree: cst.Module) -> cst.FunctionDef | None:
    """Find the @scanner decorated function in the module."""
    for node in tree.body:
        if isinstance(node, cst.FunctionDef):
            for decorator in node.decorators:
                if _is_scanner_decorator(decorator):
                    return node
    return None


def _is_scanner_decorator(decorator: cst.Decorator) -> bool:
    """Check if a decorator is @scanner or @scanner(...)."""
    if isinstance(decorator.decorator, cst.Name):
        return decorator.decorator.value == "scanner"
    if isinstance(decorator.decorator, cst.Call):
        if isinstance(decorator.decorator.func, cst.Name):
            return decorator.decorator.func.value == "scanner"
    return False


def _parse_scanner_decorator(func: cst.FunctionDef) -> ScannerDecoratorSpec:
    """Parse the @scanner decorator arguments."""
    spec = ScannerDecoratorSpec()

    for decorator in func.decorators:
        if not _is_scanner_decorator(decorator):
            continue

        if isinstance(decorator.decorator, cst.Call):
            for arg in decorator.decorator.args:
                if arg.keyword is None:
                    continue
                key = arg.keyword.value
                value = _eval_literal(arg.value)

                if key == "messages":
                    spec.messages = value
                elif key == "events":
                    spec.events = value
                elif key == "name":
                    spec.name = value
                elif key == "version":
                    spec.version = value

    return spec


def _find_scanner_call(
    func: cst.FunctionDef,
) -> tuple[cst.Call | None, str | None]:
    """Find the llm_scanner or grep_scanner call in the function body.

    Returns (call, scanner_type) or (None, None) if not found.
    Tolerates comments and blank lines before the return statement.
    """
    if not isinstance(func.body, cst.IndentedBlock):
        return None, None

    # Look for the return statement (should be the last non-comment statement)
    for stmt in reversed(func.body.body):
        if isinstance(stmt, cst.SimpleStatementLine):
            for node in stmt.body:
                if isinstance(node, cst.Return) and isinstance(node.value, cst.Call):
                    call = node.value
                    if isinstance(call.func, cst.Name):
                        if call.func.value == "llm_scanner":
                            return call, "llm"
                        elif call.func.value == "grep_scanner":
                            return call, "grep"
        # Skip comments, pass statements, docstrings
        elif isinstance(stmt, cst.EmptyLine):
            continue

    return None, None


def _parse_llm_scanner_call(
    call: cst.Call, tree: cst.Module
) -> tuple[LLMScannerSpec | None, str | None]:
    """Parse llm_scanner(...) call into LLMScannerSpec."""
    question: str | None = None
    answer_type: str | None = None
    labels: list[str] | None = None
    structured_spec: StructuredAnswerSpec | None = None
    model: str | None = None
    retry_refusals: int | None = None
    template: str | None = None

    for arg in call.args:
        if arg.keyword is None:
            continue

        key = arg.keyword.value
        value = arg.value

        if key == "question":
            # Must be a string literal
            if not _is_string_literal(value):
                return None, "Uses dynamic question function"
            question = _eval_literal(value)

        elif key == "answer":
            parsed = _parse_answer_arg(value, tree)
            if parsed is None:
                return None, "Could not parse answer argument"
            answer_type, labels, structured_spec = parsed

        elif key == "model":
            model = _eval_literal(value)

        elif key == "retry_refusals":
            retry_refusals = _eval_literal(value)

        elif key == "template":
            if not _is_string_literal(value):
                return None, "Template must be a string literal"
            template = _eval_literal(value)

        elif key == "template_variables":
            return None, "Uses custom template variables"

        elif key == "preprocessor":
            return None, "Uses custom message preprocessor"

    if question is None:
        return None, "Missing question argument"
    if answer_type is None:
        return None, "Missing answer argument"

    return (
        LLMScannerSpec(
            question=question,
            answer_type=answer_type,  # type: ignore[arg-type]
            labels=labels,
            structured_spec=structured_spec,
            model=model,
            retry_refusals=retry_refusals,
            template=template,
        ),
        None,
    )


def _parse_answer_arg(
    value: cst.BaseExpression, tree: cst.Module
) -> tuple[str, list[str] | None, StructuredAnswerSpec | None] | None:
    """Parse the answer= argument.

    Returns (answer_type, labels, structured_spec) or None if unparseable.
    """
    # Simple literal: "boolean", "numeric", "string"
    if _is_string_literal(value):
        literal = _eval_literal(value)
        if literal in ("boolean", "numeric", "string"):
            return (literal, None, None)

    # List of labels: ["A", "B", "C"]
    if isinstance(value, cst.List):
        labels = []
        for el in value.elements:
            if isinstance(el, cst.Element) and _is_string_literal(el.value):
                labels.append(_eval_literal(el.value))
            else:
                return None
        return ("labels", labels, None)

    # AnswerMultiLabel(labels=[...])
    if isinstance(value, cst.Call):
        func_name = _get_call_name(value)

        if func_name == "AnswerMultiLabel":
            for arg in value.args:
                if arg.keyword and arg.keyword.value == "labels":
                    if isinstance(arg.value, cst.List):
                        labels = []
                        for el in arg.value.elements:
                            if isinstance(el, cst.Element) and _is_string_literal(
                                el.value
                            ):
                                labels.append(_eval_literal(el.value))
                            else:
                                return None
                        return ("multi_labels", labels, None)

        # AnswerStructured(type=ModelName) or AnswerStructured(type=list[ModelName])
        elif func_name == "AnswerStructured":
            for arg in value.args:
                if arg.keyword and arg.keyword.value == "type":
                    model_name, is_list = _parse_type_arg(arg.value)
                    if model_name:
                        # Find the Pydantic model in the tree
                        model_spec = _find_pydantic_model(tree, model_name)
                        if model_spec:
                            model_spec.is_list = is_list
                            return ("structured", None, model_spec)

    return None


def _parse_type_arg(value: cst.BaseExpression) -> tuple[str | None, bool]:
    """Parse type argument, returning (model_name, is_list)."""
    # Simple name: MyModel
    if isinstance(value, cst.Name):
        return (value.value, False)

    # Subscript: list[MyModel]
    if isinstance(value, cst.Subscript):
        if isinstance(value.value, cst.Name) and value.value.value == "list":
            if value.slice and len(value.slice) > 0:
                slice_el = value.slice[0]
                if isinstance(slice_el, cst.SubscriptElement):
                    if isinstance(slice_el.slice, cst.Index):
                        if isinstance(slice_el.slice.value, cst.Name):
                            return (slice_el.slice.value.value, True)

    return (None, False)


def _find_pydantic_model(
    tree: cst.Module, model_name: str
) -> StructuredAnswerSpec | None:
    """Find and parse a Pydantic BaseModel class in the module."""
    for node in tree.body:
        if isinstance(node, cst.ClassDef) and node.name.value == model_name:
            # Check if it inherits from BaseModel
            has_basemodel = False
            for base in node.bases:
                if isinstance(base.value, cst.Name) and base.value.value == "BaseModel":
                    has_basemodel = True
                    break

            if not has_basemodel:
                return None

            # Parse fields
            fields: list[StructuredField] = []
            nested_models: list[StructuredAnswerSpec] = []

            if isinstance(node.body, cst.IndentedBlock):
                for stmt in node.body.body:
                    if isinstance(stmt, cst.SimpleStatementLine):
                        for inner in stmt.body:
                            if isinstance(inner, cst.AnnAssign):
                                field = _parse_field_annotation(inner)
                                if field:
                                    fields.append(field)

                                    # Extract potential model names from type annotation
                                    # Handles wrapped types like list[Model], Model | None
                                    potential_models = _extract_model_names(
                                        field.field_type
                                    )
                                    for nested_name in potential_models:
                                        if (
                                            nested_name != model_name
                                        ):  # Avoid self-reference
                                            nested = _find_pydantic_model(
                                                tree, nested_name
                                            )
                                            if nested and nested not in nested_models:
                                                nested_models.append(nested)

            return StructuredAnswerSpec(
                class_name=model_name,
                fields=fields,
                nested_models=nested_models if nested_models else None,
            )

    return None


def _parse_field_annotation(node: cst.AnnAssign) -> StructuredField | None:
    """Parse a field like: name: str = Field(description='...')."""
    if not isinstance(node.target, cst.Name):
        return None

    name = node.target.value
    type_str = _annotation_to_string(node.annotation.annotation)

    description = ""
    alias = None

    # Parse Field(...) call
    if node.value and isinstance(node.value, cst.Call):
        func_name = _get_call_name(node.value)
        if func_name == "Field":
            for arg in node.value.args:
                if arg.keyword:
                    if arg.keyword.value == "description":
                        description = _eval_literal(arg.value) or ""
                    elif arg.keyword.value == "alias":
                        alias = _eval_literal(arg.value)

    return StructuredField(
        name=name,
        field_type=type_str,
        description=description,
        alias=alias,
    )


def _annotation_to_string(ann: cst.BaseExpression) -> str:
    """Convert type annotation to string."""
    # Use libcst's code generation to get the string representation
    module = cst.Module(body=[])
    return module.code_for_node(ann)


def _parse_grep_scanner_call(
    call: cst.Call,
) -> tuple[GrepScannerSpec | None, str | None]:
    """Parse grep_scanner(...) call into GrepScannerSpec."""
    pattern: str | None = None
    patterns: list[str] | None = None
    labeled_patterns: dict[str, list[str]] | None = None
    pattern_type: str | None = None
    regex = False
    ignore_case = True
    word_boundary = False

    for arg in call.args:
        if arg.keyword is None:
            # Positional argument - must be pattern
            parsed = _parse_pattern_arg(arg.value)
            if parsed is None:
                return None, "Could not parse pattern argument"
            pattern_type, pattern, patterns, labeled_patterns = parsed
            continue

        key = arg.keyword.value
        value = arg.value

        if key == "pattern":
            parsed = _parse_pattern_arg(value)
            if parsed is None:
                return None, "Could not parse pattern argument"
            pattern_type, pattern, patterns, labeled_patterns = parsed

        elif key == "regex":
            regex = _eval_literal(value) or False

        elif key == "ignore_case":
            ignore_case = _eval_literal(value)
            if ignore_case is None:
                ignore_case = True

        elif key == "word_boundary":
            word_boundary = _eval_literal(value) or False

    if pattern_type is None:
        return None, "Missing pattern argument"

    return (
        GrepScannerSpec(
            pattern_type=pattern_type,  # type: ignore[arg-type]
            pattern=pattern,
            patterns=patterns,
            labeled_patterns=labeled_patterns,
            regex=regex,
            ignore_case=ignore_case,
            word_boundary=word_boundary,
        ),
        None,
    )


def _parse_pattern_arg(
    value: cst.BaseExpression,
) -> tuple[str, str | None, list[str] | None, dict[str, list[str]] | None] | None:
    """Parse the pattern= argument for grep_scanner.

    Returns (pattern_type, pattern, patterns, labeled_patterns) or None.
    """
    # Single string pattern
    if _is_string_literal(value):
        return ("single", _eval_literal(value), None, None)

    # List of patterns
    if isinstance(value, cst.List):
        patterns = []
        for el in value.elements:
            if isinstance(el, cst.Element) and _is_string_literal(el.value):
                patterns.append(_eval_literal(el.value))
            else:
                return None
        return ("list", None, patterns, None)

    # Dict of labeled patterns
    if isinstance(value, cst.Dict):
        labeled: dict[str, list[str]] = {}
        for el in value.elements:  # type: ignore[assignment]
            if isinstance(el, cst.DictElement):
                if not _is_string_literal(el.key):
                    return None
                label = _eval_literal(el.key)

                # Value can be string or list of strings
                if _is_string_literal(el.value):
                    labeled[label] = [_eval_literal(el.value)]
                elif isinstance(el.value, cst.List):
                    patterns = []
                    for list_el in el.value.elements:
                        if isinstance(list_el, cst.Element) and _is_string_literal(
                            list_el.value
                        ):
                            patterns.append(_eval_literal(list_el.value))
                        else:
                            return None
                    labeled[label] = patterns
                else:
                    return None
            else:
                return None
        return ("labeled", None, None, labeled)

    return None


def _is_string_literal(node: cst.BaseExpression) -> bool:
    """Check if node is a string literal."""
    if isinstance(node, cst.SimpleString | cst.FormattedString):
        return True
    if isinstance(node, cst.ConcatenatedString):
        return True
    return False


def _get_call_name(call: cst.Call) -> str | None:
    """Get the name of a function call."""
    if isinstance(call.func, cst.Name):
        return call.func.value
    return None


def _eval_literal(node: cst.BaseExpression) -> Any:
    """Safely evaluate a literal expression."""
    try:
        module = cst.Module(body=[])
        code = module.code_for_node(node)
        return ast.literal_eval(code)
    except (ValueError, SyntaxError):
        return None


def _extract_model_names(type_str: str) -> list[str]:
    """Extract potential model names from a type annotation string.

    Handles:
    - Simple: "MyModel" -> ["MyModel"]
    - Optional: "MyModel | None" -> ["MyModel"]
    - List: "list[MyModel]" -> ["MyModel"]
    - Dict values: "dict[str, MyModel]" -> ["MyModel"]
    - Nested: "list[MyModel | None]" -> ["MyModel"]

    Returns list of uppercase names that could be Pydantic models.
    """
    # Known builtins that start with uppercase but aren't custom models
    builtins = {
        "str",
        "int",
        "float",
        "bool",
        "None",
        "Any",
        "list",
        "dict",
        "set",
        "tuple",
        "Optional",
        "Union",
        "Literal",
        "List",
        "Dict",
        "Set",
        "Tuple",
        "Type",
        "Callable",
        "Sequence",
        "Mapping",
        "Iterable",
    }

    # Match word boundaries for identifiers starting with uppercase
    candidates = re.findall(r"\b([A-Z][a-zA-Z0-9_]*)\b", type_str)

    return [name for name in candidates if name not in builtins]
