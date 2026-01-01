"""Tests for scanner IR generator."""

from inspect_scout._scanner_ir import (
    GrepScannerSpec,
    LLMScannerSpec,
    ScannerDecoratorSpec,
    ScannerFile,
    StructuredAnswerSpec,
    StructuredField,
    generate_scanner_file,
    parse_scanner_file,
)


class TestGenerateLLMScanner:
    """Tests for generating llm_scanner code."""

    def test_generate_boolean_scanner(self) -> None:
        """Generate a simple boolean scanner."""
        scanner = ScannerFile(
            function_name="refusal_check",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Did the assistant refuse?",
                answer_type="boolean",
            ),
        )

        source = generate_scanner_file(scanner)

        assert "def refusal_check()" in source
        assert '@scanner(messages="all")' in source
        assert 'question="Did the assistant refuse?"' in source
        assert 'answer="boolean"' in source

    def test_generate_numeric_scanner_with_options(self) -> None:
        """Generate scanner with model and retry options."""
        scanner = ScannerFile(
            function_name="rate_efficiency",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Rate 1-10",
                answer_type="numeric",
                model="openai/gpt-4o",
                retry_refusals=5,
            ),
        )

        source = generate_scanner_file(scanner)

        assert 'model="openai/gpt-4o"' in source
        assert "retry_refusals=5" in source

    def test_generate_labels_scanner(self) -> None:
        """Generate scanner with label list."""
        scanner = ScannerFile(
            function_name="quality",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Rate quality",
                answer_type="labels",
                labels=["Excellent", "Good", "Poor"],
            ),
        )

        source = generate_scanner_file(scanner)

        # Check labels are present (quote style may vary with formatter)
        assert "Excellent" in source
        assert "Good" in source
        assert "Poor" in source

    def test_generate_multi_labels_scanner(self) -> None:
        """Generate scanner with AnswerMultiLabel."""
        scanner = ScannerFile(
            function_name="categories",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Categories?",
                answer_type="multi_labels",
                labels=["A", "B", "C"],
            ),
        )

        source = generate_scanner_file(scanner)

        assert "AnswerMultiLabel" in source
        assert "labels=" in source

    def test_generate_structured_scanner(self) -> None:
        """Generate scanner with AnswerStructured."""
        scanner = ScannerFile(
            function_name="analyze",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Analyze",
                answer_type="structured",
                structured_spec=StructuredAnswerSpec(
                    class_name="Analysis",
                    fields=[
                        StructuredField(
                            name="score",
                            field_type="int",
                            description="Score 1-10",
                        ),
                        StructuredField(
                            name="reason",
                            field_type="str",
                            description="Explanation",
                        ),
                    ],
                ),
            ),
            structured_model=StructuredAnswerSpec(
                class_name="Analysis",
                fields=[
                    StructuredField(
                        name="score",
                        field_type="int",
                        description="Score 1-10",
                    ),
                    StructuredField(
                        name="reason",
                        field_type="str",
                        description="Explanation",
                    ),
                ],
            ),
        )

        source = generate_scanner_file(scanner)

        assert "class Analysis(BaseModel):" in source
        assert "score: int" in source
        assert "reason: str" in source
        assert "AnswerStructured(type=Analysis)" in source

    def test_generate_with_template(self) -> None:
        """Generate scanner with custom template."""
        scanner = ScannerFile(
            function_name="custom",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Q?",
                answer_type="boolean",
                template="Custom: {{ question }}",
            ),
        )

        source = generate_scanner_file(scanner)

        assert 'template="Custom: {{ question }}"' in source


class TestGenerateGrepScanner:
    """Tests for generating grep_scanner code."""

    def test_generate_single_pattern(self) -> None:
        """Generate grep_scanner with single pattern."""
        scanner = ScannerFile(
            function_name="find_error",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="grep",
            grep_scanner=GrepScannerSpec(
                pattern_type="single",
                pattern="error",
            ),
        )

        source = generate_scanner_file(scanner)

        assert "grep_scanner" in source
        assert 'pattern="error"' in source

    def test_generate_pattern_list(self) -> None:
        """Generate grep_scanner with pattern list."""
        scanner = ScannerFile(
            function_name="find_issues",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="grep",
            grep_scanner=GrepScannerSpec(
                pattern_type="list",
                patterns=["error", "warning"],
            ),
        )

        source = generate_scanner_file(scanner)

        # Check patterns are present (quote style may vary)
        assert "error" in source
        assert "warning" in source

    def test_generate_labeled_patterns(self) -> None:
        """Generate grep_scanner with labeled patterns."""
        scanner = ScannerFile(
            function_name="categorize",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="grep",
            grep_scanner=GrepScannerSpec(
                pattern_type="labeled",
                labeled_patterns={
                    "errors": ["error", "failed"],
                    "warnings": ["warning"],
                },
            ),
        )

        source = generate_scanner_file(scanner)

        # Check labels are present (quote style may vary)
        assert "errors" in source
        assert "warnings" in source

    def test_generate_with_regex(self) -> None:
        """Generate grep_scanner with regex enabled."""
        scanner = ScannerFile(
            function_name="find_url",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="grep",
            grep_scanner=GrepScannerSpec(
                pattern_type="single",
                pattern=r"https?://\S+",
                regex=True,
                ignore_case=False,
            ),
        )

        source = generate_scanner_file(scanner)

        assert "regex=True" in source
        assert "ignore_case=False" in source


class TestGenerateDecorator:
    """Tests for generating @scanner decorator."""

    def test_generate_messages_list(self) -> None:
        """Generate with messages list."""
        scanner = ScannerFile(
            function_name="filtered",
            decorator=ScannerDecoratorSpec(messages=["user", "assistant"]),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(question="Q?", answer_type="boolean"),
        )

        source = generate_scanner_file(scanner)

        # Check for messages filter (quote style may vary with formatter)
        assert "messages=" in source
        assert "user" in source
        assert "assistant" in source

    def test_generate_with_events(self) -> None:
        """Generate with events filter."""
        scanner = ScannerFile(
            function_name="with_events",
            decorator=ScannerDecoratorSpec(
                messages="all",
                events=["tool", "error"],
            ),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(question="Q?", answer_type="boolean"),
        )

        source = generate_scanner_file(scanner)

        # Check for events filter (quote style may vary with formatter)
        assert "events=" in source
        assert "tool" in source
        assert "error" in source

    def test_generate_with_version(self) -> None:
        """Generate with version number."""
        scanner = ScannerFile(
            function_name="versioned",
            decorator=ScannerDecoratorSpec(messages="all", version=2),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(question="Q?", answer_type="boolean"),
        )

        source = generate_scanner_file(scanner)

        assert "version=2" in source


class TestRoundTrip:
    """Tests for parse -> generate -> parse round-tripping."""

    def test_round_trip_boolean_scanner(self) -> None:
        """Round-trip a boolean scanner."""
        scanner = ScannerFile(
            function_name="test_scanner",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Did it work?",
                answer_type="boolean",
            ),
        )

        # Generate
        source = generate_scanner_file(scanner)

        # Parse back
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.function_name == scanner.function_name
        assert result.scanner.scanner_type == scanner.scanner_type
        assert result.scanner.llm_scanner is not None
        assert scanner.llm_scanner is not None
        assert result.scanner.llm_scanner.question == scanner.llm_scanner.question
        assert result.scanner.llm_scanner.answer_type == scanner.llm_scanner.answer_type

    def test_round_trip_grep_scanner(self) -> None:
        """Round-trip a grep scanner."""
        scanner = ScannerFile(
            function_name="find_pattern",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="grep",
            grep_scanner=GrepScannerSpec(
                pattern_type="list",
                patterns=["error", "warning"],
                regex=True,
            ),
        )

        # Generate
        source = generate_scanner_file(scanner)

        # Parse back
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.scanner_type == "grep"
        assert result.scanner.grep_scanner is not None
        assert result.scanner.grep_scanner.patterns == ["error", "warning"]
        assert result.scanner.grep_scanner.regex is True

    def test_round_trip_with_all_options(self) -> None:
        """Round-trip scanner with all options."""
        scanner = ScannerFile(
            function_name="full_options",
            decorator=ScannerDecoratorSpec(
                messages=["user", "assistant"],
                events=["tool"],
                version=3,
            ),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Complex question?",
                answer_type="numeric",
                model="anthropic/claude-3",
                retry_refusals=2,
                template="Custom: {{ question }}",
            ),
        )

        # Generate
        source = generate_scanner_file(scanner)

        # Parse back
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        spec = result.scanner.llm_scanner
        assert spec is not None
        assert spec.model == "anthropic/claude-3"
        assert spec.retry_refusals == 2
        assert spec.template == "Custom: {{ question }}"

    def test_round_trip_nested_structured_scanner(self) -> None:
        """Round-trip a scanner with nested Pydantic models."""
        scanner = ScannerFile(
            function_name="analyze",
            decorator=ScannerDecoratorSpec(messages="all"),
            scanner_type="llm",
            llm_scanner=LLMScannerSpec(
                question="Analyze",
                answer_type="structured",
                structured_spec=StructuredAnswerSpec(
                    class_name="Analysis",
                    fields=[
                        StructuredField(
                            name="score", field_type="int", description="Score"
                        ),
                        StructuredField(
                            name="details", field_type="Details", description="Details"
                        ),
                    ],
                    nested_models=[
                        StructuredAnswerSpec(
                            class_name="Details",
                            fields=[
                                StructuredField(
                                    name="reason",
                                    field_type="str",
                                    description="Reason",
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            structured_model=StructuredAnswerSpec(
                class_name="Analysis",
                fields=[
                    StructuredField(
                        name="score", field_type="int", description="Score"
                    ),
                    StructuredField(
                        name="details", field_type="Details", description="Details"
                    ),
                ],
                nested_models=[
                    StructuredAnswerSpec(
                        class_name="Details",
                        fields=[
                            StructuredField(
                                name="reason", field_type="str", description="Reason"
                            ),
                        ],
                    ),
                ],
            ),
        )

        # Generate
        source = generate_scanner_file(scanner)

        # Verify nested model is in generated code
        assert "class Details(BaseModel):" in source
        assert "class Analysis(BaseModel):" in source

        # Parse back
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.structured_model is not None
        assert result.scanner.structured_model.class_name == "Analysis"
        assert result.scanner.structured_model.nested_models is not None
        assert len(result.scanner.structured_model.nested_models) == 1
        assert result.scanner.structured_model.nested_models[0].class_name == "Details"
