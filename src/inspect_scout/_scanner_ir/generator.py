"""Code generator for scanner Python files.

Generates new scanner files from IR and applies in-place changes to existing files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import libcst as cst

from .formatter import format_with_ruff
from .types import (
    GrepScannerSpec,
    LLMScannerSpec,
    ScannerDecoratorSpec,
    ScannerFile,
    StructuredAnswerSpec,
    StructuredField,
)


class SourceChangedError(Exception):
    """Raised when source file has changed and edits cannot be applied."""

    pass


def source_unchanged(source1: str, source2: str) -> bool:
    """Check if two sources are semantically equivalent.

    Compares the parsed ScannerFile objects, which contain only
    semantic content. This ignores differences in:
    - Comments
    - Whitespace and formatting
    - Line breaks

    Args:
        source1: First source code string.
        source2: Second source code string.

    Returns:
        True if the sources are semantically equivalent.
    """
    from .parser import parse_scanner_file

    result1 = parse_scanner_file(source1)
    result2 = parse_scanner_file(source2)

    # Both must be editable
    if not result1.editable or not result2.editable:
        return False

    # Compare semantic content
    return result1.scanner == result2.scanner


def generate_scanner_file(
    scanner: ScannerFile,
    project_dir: Path | None = None,
) -> str:
    """Generate a new scanner file from scratch.

    Args:
        scanner: Scanner specification to generate code for.
        project_dir: Project directory for formatter config (optional).

    Returns:
        Generated Python source code.
    """
    parts: list[str] = []

    # Generate imports
    parts.append(_generate_imports(scanner))
    parts.append("")

    # Generate Pydantic model if needed
    if scanner.structured_model:
        parts.append(_generate_pydantic_model(scanner.structured_model))
        parts.append("")

    # Generate scanner function
    parts.append(_generate_scanner_function(scanner))
    parts.append("")

    source = "\n".join(parts)

    # Apply formatter
    return format_with_ruff(source, project_dir)


def apply_scanner_changes(
    source: str,
    updated_scanner: ScannerFile,
    file_path: Path | None = None,
    project_dir: Path | None = None,
) -> str:
    """Apply changes to source code, preserving formatting.

    Re-parses source internally to get CST, then uses libcst transformers
    to modify only the changed nodes, keeping comments, whitespace, and
    other formatting intact.

    If file_path is provided, validates that the on-disk content matches
    the provided source before applying changes. This prevents overwriting
    changes made by other editors.

    Args:
        source: The source code the client has (from when they loaded the file).
        updated_scanner: Updated scanner specification from the UI.
        file_path: Optional path to the file on disk for validation.
        project_dir: Project directory for formatter config (optional).

    Returns:
        Modified source code with changes applied.

    Raises:
        SourceChangedError: If on-disk source differs from provided source.
    """
    # If file_path provided, validate source hasn't changed on disk
    if file_path is not None:
        disk_source = file_path.read_text()

        # Compare semantic content (ignores comments, whitespace, formatting)
        if not source_unchanged(source, disk_source):
            raise SourceChangedError(
                "Source file has been modified. Please reload and try again."
            )

        # Use disk source for the actual edit - preserves any comment/formatting changes
        source = disk_source

    # Parse source to get CST
    tree = cst.parse_module(source)

    # Create transformer to apply changes
    transformer = _ScannerTransformer(updated_scanner)
    modified_tree = tree.visit(transformer)

    modified_source = modified_tree.code

    # Apply formatter
    return format_with_ruff(modified_source, project_dir)


def _generate_imports(scanner: ScannerFile) -> str:
    """Generate import statements for a scanner file."""
    inspect_scout_imports = ["Scanner", "scanner"]

    if scanner.scanner_type == "llm":
        inspect_scout_imports.append("llm_scanner")
        if scanner.llm_scanner:
            if scanner.llm_scanner.answer_type == "multi_labels":
                inspect_scout_imports.append("AnswerMultiLabel")
            elif scanner.llm_scanner.answer_type == "structured":
                inspect_scout_imports.append("AnswerStructured")
    else:
        inspect_scout_imports.append("grep_scanner")

    # Sort imports
    inspect_scout_imports.sort()

    lines = []

    # Pydantic imports if needed
    if scanner.structured_model:
        lines.append("from pydantic import BaseModel, Field")
        lines.append("")

    # inspect_scout imports
    if len(inspect_scout_imports) <= 3:
        lines.append(f"from inspect_scout import {', '.join(inspect_scout_imports)}")
    else:
        lines.append("from inspect_scout import (")
        for imp in inspect_scout_imports:
            lines.append(f"    {imp},")
        lines.append(")")

    lines.append("from inspect_scout._transcript.types import Transcript")

    return "\n".join(lines)


def _generate_pydantic_model(spec: StructuredAnswerSpec) -> str:
    """Generate a Pydantic BaseModel class."""
    # Generate nested models first
    parts = []
    if spec.nested_models:
        for nested in spec.nested_models:
            parts.append(_generate_pydantic_model(nested))
            parts.append("")

    lines = [f"class {spec.class_name}(BaseModel):"]

    if not spec.fields:
        lines.append("    pass")
    else:
        for field in spec.fields:
            lines.append(f"    {_generate_field(field)}")

    parts.append("\n".join(lines))
    return "\n".join(parts)


def _generate_field(field: StructuredField) -> str:
    """Generate a single Pydantic field."""
    field_args = []
    if field.alias:
        field_args.append(f'alias="{field.alias}"')
    if field.description:
        # Escape quotes in description
        desc = field.description.replace('"', '\\"')
        field_args.append(f'description="{desc}"')

    if field_args:
        return f"{field.name}: {field.field_type} = Field({', '.join(field_args)})"
    else:
        return f"{field.name}: {field.field_type}"


def _generate_scanner_function(scanner: ScannerFile) -> str:
    """Generate the scanner function."""
    lines = []

    # Decorator
    lines.append(_generate_decorator(scanner.decorator))

    # Function signature
    lines.append(f"def {scanner.function_name}() -> Scanner[Transcript]:")

    # Function body
    if scanner.scanner_type == "llm" and scanner.llm_scanner:
        body = _generate_llm_scanner_call(scanner.llm_scanner)
    elif scanner.scanner_type == "grep" and scanner.grep_scanner:
        body = _generate_grep_scanner_call(scanner.grep_scanner)
    else:
        body = "pass"

    lines.append(f"    return {body}")

    return "\n".join(lines)


def _generate_decorator(spec: ScannerDecoratorSpec) -> str:
    """Generate @scanner(...) decorator."""
    args: list[str] = []

    if spec.messages:
        if spec.messages == "all":
            args.append('messages="all"')
        else:
            args.append(f"messages={spec.messages!r}")

    if spec.events:
        args.append(f"events={spec.events!r}")

    if spec.name:
        args.append(f'name="{spec.name}"')

    if spec.version != 0:
        args.append(f"version={spec.version}")

    if args:
        return f"@scanner({', '.join(args)})"
    else:
        return "@scanner"


def _generate_llm_scanner_call(spec: LLMScannerSpec) -> str:
    """Generate llm_scanner(...) call."""
    args: list[str] = []

    # Question - handle multiline
    question = spec.question.replace("\\", "\\\\").replace('"', '\\"')
    if "\n" in question or len(question) > 60:
        # Use triple quotes for multiline
        question_escaped = spec.question.replace('"""', '\\"\\"\\"')
        args.append(f'question="""{question_escaped}"""')
    else:
        args.append(f'question="{question}"')

    # Answer
    args.append(f"answer={_generate_answer_arg(spec)}")

    # Optional args
    if spec.model:
        args.append(f'model="{spec.model}"')

    if spec.retry_refusals is not None and spec.retry_refusals != 3:
        args.append(f"retry_refusals={spec.retry_refusals}")

    if spec.template:
        template = spec.template.replace("\\", "\\\\").replace('"', '\\"')
        if "\n" in template or len(template) > 60:
            template_escaped = spec.template.replace('"""', '\\"\\"\\"')
            args.append(f'template="""{template_escaped}"""')
        else:
            args.append(f'template="{template}"')

    # Format nicely
    if len(args) <= 2 and all(len(a) < 40 for a in args):
        return f"llm_scanner({', '.join(args)})"
    else:
        formatted_args = ",\n        ".join(args)
        return f"llm_scanner(\n        {formatted_args},\n    )"


def _generate_answer_arg(spec: LLMScannerSpec) -> str:
    """Generate the answer= argument value."""
    match spec.answer_type:
        case "boolean" | "numeric" | "string":
            return f'"{spec.answer_type}"'

        case "labels":
            return repr(spec.labels)

        case "multi_labels":
            labels_repr = repr(spec.labels)
            return f"AnswerMultiLabel(labels={labels_repr})"

        case "structured":
            if spec.structured_spec:
                type_ref = spec.structured_spec.class_name
                if spec.structured_spec.is_list:
                    type_ref = f"list[{type_ref}]"
                return f"AnswerStructured(type={type_ref})"
            return '"boolean"'

    return '"boolean"'


def _generate_grep_scanner_call(spec: GrepScannerSpec) -> str:
    """Generate grep_scanner(...) call."""
    args: list[str] = []

    # Pattern
    match spec.pattern_type:
        case "single":
            if spec.pattern:
                pattern = spec.pattern.replace("\\", "\\\\").replace('"', '\\"')
                args.append(f'pattern="{pattern}"')
        case "list":
            if spec.patterns:
                args.append(f"pattern={spec.patterns!r}")
        case "labeled":
            if spec.labeled_patterns:
                args.append(f"pattern={spec.labeled_patterns!r}")

    # Optional args with non-default values
    if spec.regex:
        args.append("regex=True")

    if not spec.ignore_case:
        args.append("ignore_case=False")

    if spec.word_boundary:
        args.append("word_boundary=True")

    # Format nicely
    if len(args) <= 2 and all(len(a) < 40 for a in args):
        return f"grep_scanner({', '.join(args)})"
    else:
        formatted_args = ",\n        ".join(args)
        return f"grep_scanner(\n        {formatted_args},\n    )"


class _ScannerTransformer(cst.CSTTransformer):
    """CST transformer to apply scanner changes in-place."""

    def __init__(self, scanner: ScannerFile) -> None:
        super().__init__()
        self.scanner = scanner
        self._in_scanner_func = False
        self._in_scanner_call = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Track when we're inside the scanner function."""
        if node.name.value == self.scanner.function_name:
            self._in_scanner_func = True
        return True

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Update function name and decorator if needed."""
        if original_node.name.value == self.scanner.function_name:
            self._in_scanner_func = False

            # Update decorator
            new_decorators = []
            for decorator in updated_node.decorators:
                if self._is_scanner_decorator(decorator):
                    new_decorators.append(self._update_decorator(decorator))
                else:
                    new_decorators.append(decorator)

            return updated_node.with_changes(decorators=new_decorators)

        return updated_node

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Update llm_scanner or grep_scanner call arguments."""
        if not self._in_scanner_func:
            return updated_node

        func_name = self._get_call_name(updated_node)

        if func_name == "llm_scanner" and self.scanner.llm_scanner:
            return self._update_llm_scanner_call(updated_node)
        elif func_name == "grep_scanner" and self.scanner.grep_scanner:
            return self._update_grep_scanner_call(updated_node)

        return updated_node

    def _is_scanner_decorator(self, decorator: cst.Decorator) -> bool:
        """Check if decorator is @scanner."""
        if isinstance(decorator.decorator, cst.Name):
            return decorator.decorator.value == "scanner"
        if isinstance(decorator.decorator, cst.Call):
            if isinstance(decorator.decorator.func, cst.Name):
                return decorator.decorator.func.value == "scanner"
        return False

    def _update_decorator(self, decorator: cst.Decorator) -> cst.Decorator:
        """Update @scanner decorator with new args."""
        spec = self.scanner.decorator
        new_args = []

        if spec.messages:
            if spec.messages == "all":
                new_args.append(
                    cst.Arg(
                        keyword=cst.Name("messages"),
                        value=cst.SimpleString('"all"'),
                    )
                )
            else:
                new_args.append(
                    cst.Arg(
                        keyword=cst.Name("messages"),
                        value=_list_to_cst(spec.messages),
                    )
                )

        if spec.events:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("events"),
                    value=_list_to_cst(spec.events),
                )
            )

        if spec.name:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("name"),
                    value=cst.SimpleString(f'"{spec.name}"'),
                )
            )

        if spec.version != 0:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("version"),
                    value=cst.Integer(str(spec.version)),
                )
            )

        if new_args:
            new_call = cst.Call(func=cst.Name("scanner"), args=new_args)
            return decorator.with_changes(decorator=new_call)
        else:
            return decorator.with_changes(decorator=cst.Name("scanner"))

    def _update_llm_scanner_call(self, call: cst.Call) -> cst.Call:
        """Update llm_scanner call with new args."""
        spec = self.scanner.llm_scanner
        if spec is None:
            return call

        new_args = []

        # Question
        question = spec.question.replace("\\", "\\\\").replace('"', '\\"')
        if "\n" in question or len(question) > 60:
            question_escaped = spec.question.replace('"""', '\\"\\"\\"')
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("question"),
                    value=cst.SimpleString(f'"""{question_escaped}"""'),
                )
            )
        else:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("question"),
                    value=cst.SimpleString(f'"{question}"'),
                )
            )

        # Answer
        new_args.append(
            cst.Arg(
                keyword=cst.Name("answer"),
                value=_answer_to_cst(spec),
            )
        )

        # Optional args
        if spec.model:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("model"),
                    value=cst.SimpleString(f'"{spec.model}"'),
                )
            )

        if spec.retry_refusals is not None and spec.retry_refusals != 3:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("retry_refusals"),
                    value=cst.Integer(str(spec.retry_refusals)),
                )
            )

        if spec.template:
            template = spec.template.replace("\\", "\\\\").replace('"', '\\"')
            if "\n" in template or len(template) > 60:
                template_escaped = spec.template.replace('"""', '\\"\\"\\"')
                new_args.append(
                    cst.Arg(
                        keyword=cst.Name("template"),
                        value=cst.SimpleString(f'"""{template_escaped}"""'),
                    )
                )
            else:
                new_args.append(
                    cst.Arg(
                        keyword=cst.Name("template"),
                        value=cst.SimpleString(f'"{template}"'),
                    )
                )

        return call.with_changes(args=new_args)

    def _update_grep_scanner_call(self, call: cst.Call) -> cst.Call:
        """Update grep_scanner call with new args."""
        spec = self.scanner.grep_scanner
        if spec is None:
            return call

        new_args = []

        # Pattern
        match spec.pattern_type:
            case "single":
                if spec.pattern:
                    pattern = spec.pattern.replace("\\", "\\\\").replace('"', '\\"')
                    new_args.append(
                        cst.Arg(
                            keyword=cst.Name("pattern"),
                            value=cst.SimpleString(f'"{pattern}"'),
                        )
                    )
            case "list":
                if spec.patterns:
                    new_args.append(
                        cst.Arg(
                            keyword=cst.Name("pattern"),
                            value=_list_to_cst(spec.patterns),
                        )
                    )
            case "labeled":
                if spec.labeled_patterns:
                    new_args.append(
                        cst.Arg(
                            keyword=cst.Name("pattern"),
                            value=_dict_to_cst(spec.labeled_patterns),
                        )
                    )

        # Optional args with non-default values
        if spec.regex:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("regex"),
                    value=cst.Name("True"),
                )
            )

        if not spec.ignore_case:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("ignore_case"),
                    value=cst.Name("False"),
                )
            )

        if spec.word_boundary:
            new_args.append(
                cst.Arg(
                    keyword=cst.Name("word_boundary"),
                    value=cst.Name("True"),
                )
            )

        return call.with_changes(args=new_args)

    def _get_call_name(self, call: cst.Call) -> str | None:
        """Get the name of a function call."""
        if isinstance(call.func, cst.Name):
            return call.func.value
        return None


def _list_to_cst(items: Sequence[str]) -> cst.List:
    """Convert a list of strings to CST List node."""
    elements = [cst.Element(cst.SimpleString(f'"{item}"')) for item in items]
    return cst.List(elements=elements)


def _dict_to_cst(d: dict[str, list[str]]) -> cst.Dict:
    """Convert a dict of string->list[str] to CST Dict node."""
    elements = []
    for key, values in d.items():
        elements.append(
            cst.DictElement(
                key=cst.SimpleString(f'"{key}"'),
                value=_list_to_cst(values),
            )
        )
    return cst.Dict(elements=elements)


def _answer_to_cst(spec: LLMScannerSpec) -> cst.BaseExpression:
    """Convert answer spec to CST expression."""
    match spec.answer_type:
        case "boolean" | "numeric" | "string":
            return cst.SimpleString(f'"{spec.answer_type}"')

        case "labels":
            if spec.labels:
                return _list_to_cst(spec.labels)
            return cst.SimpleString('"boolean"')

        case "multi_labels":
            if spec.labels:
                return cst.Call(
                    func=cst.Name("AnswerMultiLabel"),
                    args=[
                        cst.Arg(
                            keyword=cst.Name("labels"),
                            value=_list_to_cst(spec.labels),
                        )
                    ],
                )
            return cst.SimpleString('"boolean"')

        case "structured":
            if spec.structured_spec:
                type_name = spec.structured_spec.class_name
                if spec.structured_spec.is_list:
                    type_expr: cst.BaseExpression = cst.Subscript(
                        value=cst.Name("list"),
                        slice=[cst.SubscriptElement(cst.Index(cst.Name(type_name)))],
                    )
                else:
                    type_expr = cst.Name(type_name)

                return cst.Call(
                    func=cst.Name("AnswerStructured"),
                    args=[
                        cst.Arg(
                            keyword=cst.Name("type"),
                            value=type_expr,
                        )
                    ],
                )
            return cst.SimpleString('"boolean"')

    return cst.SimpleString('"boolean"')
