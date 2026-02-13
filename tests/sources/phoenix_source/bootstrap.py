# type: ignore

"""Bootstrap script to create test traces in Phoenix.

This script creates real traces using various LLM providers with
OpenInference instrumentation and Phoenix OTEL registration.

Required environment variables:
- PHOENIX_API_KEY: For authenticating with Phoenix
- PHOENIX_COLLECTOR_ENDPOINT: Phoenix collector URL
- OPENAI_API_KEY: For OpenAI traces
- ANTHROPIC_API_KEY: For Anthropic traces
- GOOGLE_API_KEY: For Google GenAI traces (optional)

Usage:
    python -m tests.sources.phoenix_source.bootstrap          # Creates traces if not exist
    python -m tests.sources.phoenix_source.bootstrap --force  # Recreates all traces
"""

import os
import sys
from datetime import datetime
from typing import Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on environment

# All expected trace names
TRACES = [
    # OpenAI (raw API)
    "scout-test-phoenix-openai-simple",
    "scout-test-phoenix-openai-multiturn",
    "scout-test-phoenix-openai-tools",
    "scout-test-phoenix-openai-multiturn-tools",
    # Anthropic (raw API)
    "scout-test-phoenix-anthropic-simple",
    "scout-test-phoenix-anthropic-multiturn",
    "scout-test-phoenix-anthropic-tools",
    "scout-test-phoenix-anthropic-multiturn-tools",
    # Google GenAI (raw API)
    "scout-test-phoenix-google-simple",
    "scout-test-phoenix-google-multiturn",
    "scout-test-phoenix-google-tools",
    "scout-test-phoenix-google-multiturn-tools",
    # LangChain (framework)
    "scout-test-phoenix-langchain-agent",
    "scout-test-phoenix-langchain-multiturn",
    "scout-test-phoenix-langchain-multiturn-tools",
    # PydanticAI (framework)
    "scout-test-phoenix-pydanticai-simple",
    "scout-test-phoenix-pydanticai-tools",
    "scout-test-phoenix-pydanticai-multiturn",
    "scout-test-phoenix-pydanticai-multiturn-tools",
]


def check_dependencies() -> bool:
    """Check if required packages are installed."""
    required = [
        "openai",
        "anthropic",
        "openinference.instrumentation.openai",
        "openinference.instrumentation.anthropic",
        "opentelemetry",
        "phoenix.otel",
    ]
    missing = []

    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print(
            "Install with: pip install openinference-instrumentation-openai "
            "openinference-instrumentation-anthropic arize-phoenix-otel"
        )
        return False

    return True


def check_env_vars() -> bool:
    """Check if required environment variables are set."""
    required = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "PHOENIX_API_KEY",
        "PHOENIX_COLLECTOR_ENDPOINT",
    ]
    missing = [v for v in required if not os.environ.get(v)]

    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        return False

    return True


async def is_bootstrap_complete() -> bool:
    """Check if all required traces already exist in Phoenix.

    Returns:
        True if all required traces exist, False otherwise
    """
    api_key = os.environ.get("PHOENIX_API_KEY")
    base_url = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")

    if not api_key or not base_url:
        print("PHOENIX_API_KEY or PHOENIX_COLLECTOR_ENDPOINT not set")
        return False

    try:
        from phoenix.client import AsyncClient

        client = AsyncClient(base_url=base_url, api_key=api_key)
        spans = await client.spans.get_spans(
            project_identifier="default",
            limit=1000,
        )

        existing_names = {span.get("name", "") for span in spans}

        missing = set(TRACES) - existing_names
        if missing:
            print(f"Missing traces: {missing}")
            return False

        print(f"Found {len(existing_names)} existing spans")
        return True

    except Exception as e:
        print(f"Error checking bootstrap status: {e}")
        return False


def setup_instrumentation() -> Any:
    """Set up OpenInference instrumentation with Phoenix."""
    from openinference.instrumentation.anthropic import AnthropicInstrumentor
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from opentelemetry import trace
    from phoenix.otel import register

    tracer_provider = register(
        project_name="default",
        endpoint=os.environ["PHOENIX_COLLECTOR_ENDPOINT"] + "/v1/traces",
    )

    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)

    # Google GenAI instrumentor (optional)
    if os.environ.get("GOOGLE_API_KEY"):
        try:
            from openinference.instrumentation.google_genai import (
                GoogleGenAIInstrumentor,
            )

            os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
            GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        except ImportError:
            print("Skipping Google GenAI instrumentation (package not installed)")

    # LangChain instrumentor (optional)
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor

        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    except ImportError:
        print("Skipping LangChain instrumentation (package not installed)")

    # PydanticAI span processor (optional)
    try:
        from openinference.instrumentation.pydantic_ai import (
            OpenInferenceSpanProcessor,
        )

        tracer_provider.add_span_processor(OpenInferenceSpanProcessor())
    except ImportError:
        print("Skipping PydanticAI instrumentation (package not installed)")

    return trace.get_tracer(__name__)


async def create_openai_simple_trace(tracer: Any) -> None:
    """Create a simple OpenAI trace."""
    import openai

    client = openai.OpenAI()

    with tracer.start_as_current_span("scout-test-phoenix-openai-simple"):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "Say 'Hello, Scout test!' and nothing else.",
                },
            ],
        )
        print(f"OpenAI simple: {response.choices[0].message.content}")


async def create_openai_multiturn_trace(tracer: Any) -> None:
    """Create a multi-turn OpenAI conversation trace."""
    import openai

    client = openai.OpenAI()

    with tracer.start_as_current_span("scout-test-phoenix-openai-multiturn"):
        messages: list[dict[str, str]] = [
            {"role": "system", "content": "You are a helpful math tutor."},
            {"role": "user", "content": "What is 2 + 2?"},
        ]

        response1 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        print(f"OpenAI multiturn turn 1: {response1.choices[0].message.content}")

        messages.append(
            {"role": "assistant", "content": response1.choices[0].message.content or ""}
        )
        messages.append({"role": "user", "content": "What about 3 + 3?"})

        response2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        print(f"OpenAI multiturn turn 2: {response2.choices[0].message.content}")

        messages.append(
            {"role": "assistant", "content": response2.choices[0].message.content or ""}
        )
        messages.append({"role": "user", "content": "And 5 + 5?"})

        response3 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        print(f"OpenAI multiturn turn 3: {response3.choices[0].message.content}")


async def create_openai_tools_trace(tracer: Any) -> None:
    """Create an OpenAI trace with tool calls."""
    import json

    import openai

    client = openai.OpenAI()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "The city name"},
                    },
                    "required": ["city"],
                },
            },
        }
    ]

    with tracer.start_as_current_span("scout-test-phoenix-openai-tools"):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "What's the weather in San Francisco?"},
            ],
            tools=tools,
            tool_choice="auto",
        )

        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            print(f"OpenAI tools: Tool called - {tool_call.function.name}")

            response2 = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "What's the weather in San Francisco?"},
                    response.choices[0].message,
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            {"temperature": 72, "condition": "sunny"}
                        ),
                    },
                ],
                tools=tools,
            )
            print(f"OpenAI tools: {response2.choices[0].message.content}")


async def create_openai_multiturn_tools_trace(tracer: Any) -> None:
    """Create a multi-turn OpenAI trace with tool calls."""
    import json

    import openai

    client = openai.OpenAI()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "The city name"},
                    },
                    "required": ["city"],
                },
            },
        }
    ]

    with tracer.start_as_current_span("scout-test-phoenix-openai-multiturn-tools"):
        messages: list[Any] = [
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ]

        response1 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        if response1.choices[0].message.tool_calls:
            tool_call1 = response1.choices[0].message.tool_calls[0]
            messages.append(response1.choices[0].message)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call1.id,
                    "content": json.dumps({"temperature": 72, "condition": "sunny"}),
                }
            )

            response1b = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
            )
            messages.append(response1b.choices[0].message)
            print(
                f"OpenAI multiturn-tools turn 1: {response1b.choices[0].message.content}"
            )

        messages.append({"role": "user", "content": "What about New York?"})

        response2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        if response2.choices[0].message.tool_calls:
            tool_call2 = response2.choices[0].message.tool_calls[0]
            messages.append(response2.choices[0].message)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call2.id,
                    "content": json.dumps({"temperature": 45, "condition": "cloudy"}),
                }
            )

            response2b = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
            )
            messages.append(response2b.choices[0].message)
            print(
                f"OpenAI multiturn-tools turn 2: {response2b.choices[0].message.content}"
            )

        messages.append({"role": "user", "content": "Which city is warmer?"})

        response3 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
        )
        print(f"OpenAI multiturn-tools turn 3: {response3.choices[0].message.content}")


async def create_anthropic_simple_trace(tracer: Any) -> None:
    """Create a simple Anthropic trace."""
    import anthropic

    client = anthropic.Anthropic()

    with tracer.start_as_current_span("scout-test-phoenix-anthropic-simple"):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful assistant.",
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello, Scout test!' and nothing else.",
                },
            ],
        )
        first_block = response.content[0] if response.content else None
        content = (
            first_block.text if first_block and hasattr(first_block, "text") else ""
        )
        print(f"Anthropic simple: {content}")


async def create_anthropic_multiturn_trace(tracer: Any) -> None:
    """Create a multi-turn Anthropic conversation trace."""
    import anthropic

    client = anthropic.Anthropic()

    with tracer.start_as_current_span("scout-test-phoenix-anthropic-multiturn"):
        messages: list[dict[str, str]] = [
            {"role": "user", "content": "What is 2 + 2?"},
        ]

        response1 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful math tutor.",
            messages=messages,
        )
        content1 = ""
        if response1.content and hasattr(response1.content[0], "text"):
            content1 = response1.content[0].text
        print(f"Anthropic multiturn turn 1: {content1}")

        messages.append({"role": "assistant", "content": content1})
        messages.append({"role": "user", "content": "What about 3 + 3?"})

        response2 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful math tutor.",
            messages=messages,
        )
        content2 = ""
        if response2.content and hasattr(response2.content[0], "text"):
            content2 = response2.content[0].text
        print(f"Anthropic multiturn turn 2: {content2}")

        messages.append({"role": "assistant", "content": content2})
        messages.append({"role": "user", "content": "And 5 + 5?"})

        response3 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful math tutor.",
            messages=messages,
        )
        content3 = ""
        if response3.content and hasattr(response3.content[0], "text"):
            content3 = response3.content[0].text
        print(f"Anthropic multiturn turn 3: {content3}")


async def create_anthropic_tools_trace(tracer: Any) -> None:
    """Create an Anthropic trace with tool calls."""
    import anthropic

    client = anthropic.Anthropic()

    tools: list[anthropic.types.ToolParam] = [
        {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The city name"},
                },
                "required": ["city"],
            },
        }
    ]

    with tracer.start_as_current_span("scout-test-phoenix-anthropic-tools"):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=[
                {"role": "user", "content": "What's the weather in San Francisco?"},
            ],
        )

        tool_use_block = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use_block = block
                break

        if tool_use_block:
            print(f"Anthropic tools: Tool called - {tool_use_block.name}")

            response2 = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                tools=tools,
                messages=[
                    {"role": "user", "content": "What's the weather in San Francisco?"},
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_block.id,
                                "content": '{"temperature": 72, "condition": "sunny"}',
                            }
                        ],
                    },
                ],
            )
            content = ""
            for block in response2.content:
                if hasattr(block, "text"):
                    content = block.text
                    break
            print(f"Anthropic tools: {content}")


async def create_anthropic_multiturn_tools_trace(tracer: Any) -> None:
    """Create a multi-turn Anthropic trace with tool calls."""
    import anthropic

    client = anthropic.Anthropic()

    tools: list[anthropic.types.ToolParam] = [
        {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The city name"},
                },
                "required": ["city"],
            },
        }
    ]

    with tracer.start_as_current_span("scout-test-phoenix-anthropic-multiturn-tools"):
        messages: list[Any] = [
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ]

        response1 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        tool_use_block1 = None
        for block in response1.content:
            if block.type == "tool_use":
                tool_use_block1 = block
                break

        if tool_use_block1:
            messages.append({"role": "assistant", "content": response1.content})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_block1.id,
                            "content": '{"temperature": 72, "condition": "sunny"}',
                        }
                    ],
                }
            )

            response1b = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                tools=tools,
                messages=messages,
            )
            content1 = ""
            for block in response1b.content:
                if hasattr(block, "text"):
                    content1 = block.text
                    break
            messages.append({"role": "assistant", "content": content1})
            print(f"Anthropic multiturn-tools turn 1: {content1}")

        messages.append({"role": "user", "content": "What about New York?"})

        response2 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        tool_use_block2 = None
        for block in response2.content:
            if block.type == "tool_use":
                tool_use_block2 = block
                break

        if tool_use_block2:
            messages.append({"role": "assistant", "content": response2.content})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_block2.id,
                            "content": '{"temperature": 45, "condition": "cloudy"}',
                        }
                    ],
                }
            )

            response2b = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                tools=tools,
                messages=messages,
            )
            content2 = ""
            for block in response2b.content:
                if hasattr(block, "text"):
                    content2 = block.text
                    break
            messages.append({"role": "assistant", "content": content2})
            print(f"Anthropic multiturn-tools turn 2: {content2}")

        messages.append({"role": "user", "content": "Which city is warmer?"})

        response3 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )
        content3 = ""
        for block in response3.content:
            if hasattr(block, "text"):
                content3 = block.text
                break
        print(f"Anthropic multiturn-tools turn 3: {content3}")


async def create_google_simple_trace(tracer: Any) -> None:
    """Create a simple Google GenAI trace."""
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Skipping Google GenAI simple trace (GOOGLE_API_KEY not set)")
        return

    try:
        from google import genai

        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

        with tracer.start_as_current_span("scout-test-phoenix-google-simple"):
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Say 'Hello, Scout test!' and nothing else.",
            )
            print(f"Google simple: {response.text}")

    except ImportError:
        print("Skipping Google GenAI simple trace (google-genai not installed)")
    except Exception as e:
        print(f"Google GenAI simple trace failed: {e}")


async def create_google_multiturn_trace(tracer: Any) -> None:
    """Create a multi-turn Google GenAI conversation trace."""
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Skipping Google GenAI multiturn trace (GOOGLE_API_KEY not set)")
        return

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

        with tracer.start_as_current_span("scout-test-phoenix-google-multiturn"):
            # Turn 1
            response1 = client.models.generate_content(
                model="gemini-2.0-flash",
                contents="What is 2 + 2? Reply with just the number.",
                config=types.GenerateContentConfig(
                    system_instruction="You are a helpful math tutor.",
                ),
            )
            print(f"Google multiturn turn 1: {response1.text}")

            # Turn 2: Build conversation history
            response2 = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text="What is 2 + 2? Reply with just the number."
                            )
                        ],
                    ),
                    types.Content(
                        role="model",
                        parts=[types.Part(text=response1.text or "4")],
                    ),
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text="What about 3 + 3? Reply with just the number."
                            )
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction="You are a helpful math tutor.",
                ),
            )
            print(f"Google multiturn turn 2: {response2.text}")

            # Turn 3
            response3 = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text="What is 2 + 2? Reply with just the number."
                            )
                        ],
                    ),
                    types.Content(
                        role="model",
                        parts=[types.Part(text=response1.text or "4")],
                    ),
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text="What about 3 + 3? Reply with just the number."
                            )
                        ],
                    ),
                    types.Content(
                        role="model",
                        parts=[types.Part(text=response2.text or "6")],
                    ),
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text="And 5 + 5? Reply with just the number.")
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction="You are a helpful math tutor.",
                ),
            )
            print(f"Google multiturn turn 3: {response3.text}")

    except ImportError:
        print("Skipping Google GenAI multiturn trace (google-genai not installed)")
    except Exception as e:
        print(f"Google GenAI multiturn trace failed: {e}")


async def create_google_tools_trace(tracer: Any) -> None:
    """Create a Google GenAI trace with tool calls."""
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Skipping Google GenAI tools trace (GOOGLE_API_KEY not set)")
        return

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

        get_weather = types.FunctionDeclaration(
            name="get_weather",
            description="Get the current weather for a city.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "city": types.Schema(type="STRING", description="The city name"),
                },
                required=["city"],
            ),
        )

        tool = types.Tool(function_declarations=[get_weather])

        with tracer.start_as_current_span("scout-test-phoenix-google-tools"):
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents="What's the weather in San Francisco?",
                config=types.GenerateContentConfig(tools=[tool]),
            )

            # Check for function call
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        print(f"Google tools: Tool called - {part.function_call.name}")

                        # Provide tool result
                        response2 = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[
                                types.Content(
                                    role="user",
                                    parts=[
                                        types.Part(
                                            text="What's the weather in San Francisco?"
                                        )
                                    ],
                                ),
                                response.candidates[0].content,
                                types.Content(
                                    role="user",
                                    parts=[
                                        types.Part(
                                            function_response=types.FunctionResponse(
                                                name="get_weather",
                                                response={
                                                    "temperature": 72,
                                                    "condition": "sunny",
                                                },
                                            )
                                        )
                                    ],
                                ),
                            ],
                            config=types.GenerateContentConfig(tools=[tool]),
                        )
                        print(f"Google tools: {response2.text}")
                        break

    except ImportError:
        print("Skipping Google GenAI tools trace (google-genai not installed)")
    except Exception as e:
        print(f"Google GenAI tools trace failed: {e}")


async def create_google_multiturn_tools_trace(tracer: Any) -> None:
    """Create a multi-turn Google GenAI trace with tool calls."""
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Skipping Google GenAI multiturn-tools trace (GOOGLE_API_KEY not set)")
        return

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

        get_weather = types.FunctionDeclaration(
            name="get_weather",
            description="Get the current weather for a city.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "city": types.Schema(type="STRING", description="The city name"),
                },
                required=["city"],
            ),
        )

        tool = types.Tool(function_declarations=[get_weather])

        with tracer.start_as_current_span("scout-test-phoenix-google-multiturn-tools"):
            # Turn 1: Ask about SF weather
            response1 = client.models.generate_content(
                model="gemini-2.0-flash",
                contents="What's the weather in San Francisco?",
                config=types.GenerateContentConfig(tools=[tool]),
            )

            history: list[types.Content] = [
                types.Content(
                    role="user",
                    parts=[types.Part(text="What's the weather in San Francisco?")],
                ),
            ]

            # Handle tool call from turn 1
            if response1.candidates and response1.candidates[0].content.parts:
                fc_part = None
                for part in response1.candidates[0].content.parts:
                    if part.function_call:
                        fc_part = part
                        break

                if fc_part:
                    print(
                        f"Google multiturn-tools turn 1: Tool called - {fc_part.function_call.name}"
                    )
                    history.append(response1.candidates[0].content)
                    history.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name="get_weather",
                                        response={
                                            "temperature": 72,
                                            "condition": "sunny",
                                        },
                                    )
                                )
                            ],
                        )
                    )

                    response1b = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=history,
                        config=types.GenerateContentConfig(tools=[tool]),
                    )
                    history.append(response1b.candidates[0].content)
                    print(f"Google multiturn-tools turn 1 response: {response1b.text}")

            # Turn 2: Ask about NYC weather
            history.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text="What about New York?")],
                )
            )

            response2 = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=history,
                config=types.GenerateContentConfig(tools=[tool]),
            )

            if response2.candidates and response2.candidates[0].content.parts:
                fc_part2 = None
                for part in response2.candidates[0].content.parts:
                    if part.function_call:
                        fc_part2 = part
                        break

                if fc_part2:
                    print(
                        f"Google multiturn-tools turn 2: Tool called - {fc_part2.function_call.name}"
                    )
                    history.append(response2.candidates[0].content)
                    history.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name="get_weather",
                                        response={
                                            "temperature": 45,
                                            "condition": "cloudy",
                                        },
                                    )
                                )
                            ],
                        )
                    )

                    response2b = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=history,
                        config=types.GenerateContentConfig(tools=[tool]),
                    )
                    history.append(response2b.candidates[0].content)
                    print(f"Google multiturn-tools turn 2 response: {response2b.text}")

            # Turn 3: Comparison (no tool needed)
            history.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text="Which city is warmer?")],
                )
            )

            response3 = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=history,
                config=types.GenerateContentConfig(tools=[tool]),
            )
            print(f"Google multiturn-tools turn 3: {response3.text}")

    except ImportError:
        print(
            "Skipping Google GenAI multiturn-tools trace (google-genai not installed)"
        )
    except Exception as e:
        print(f"Google GenAI multiturn-tools trace failed: {e}")


# =============================================================================
# LangChain Trace Functions
# =============================================================================


def _get_weather_tool(city: str) -> str:
    """Get weather for a city (shared tool implementation).

    Args:
        city: The city name to get weather for.

    Returns:
        Weather description string.
    """
    weathers = {
        "San Francisco": "Foggy, 58F",
        "New York": "Sunny, 72F",
        "London": "Rainy, 55F",
        "Tokyo": "Cloudy, 68F",
    }
    return weathers.get(city, f"Weather data not available for {city}")


async def create_langchain_agent_trace(tracer: Any) -> None:
    """Create a LangChain agent trace with tool calls."""
    try:
        from langchain.agents import create_agent
    except ImportError:
        print("Skipping LangChain agent trace (langchain not installed)")
        return

    def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        return _get_weather_tool(city)

    agent = create_agent(
        model="openai:gpt-4o-mini",
        tools=[get_weather],
        system_prompt="You are a helpful assistant. Use tools when needed.",
    )

    with tracer.start_as_current_span("scout-test-phoenix-langchain-agent"):
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "What's the weather in San Francisco?",
                    }
                ]
            },
        )
        print(f"LangChain agent: {result['messages'][-1].content}")


async def create_langchain_multiturn_trace(tracer: Any) -> None:
    """Create a LangChain multi-turn conversation trace (no tools)."""
    try:
        from langchain.agents import create_agent
    except ImportError:
        print("Skipping LangChain multiturn trace (langchain not installed)")
        return

    agent = create_agent(
        model="openai:gpt-4o-mini",
        tools=[],
        system_prompt="You are a helpful travel assistant.",
    )

    # Multi-turn conversation with history included in a single invocation
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "I'm planning a trip to Paris."},
        {
            "role": "assistant",
            "content": "Paris is a wonderful destination! "
            "When are you planning to visit and how long will you stay?",
        },
        {"role": "user", "content": "I'm thinking of going in April for about a week."},
        {
            "role": "assistant",
            "content": "April is a lovely time to visit Paris. "
            "The weather is mild and the spring flowers are blooming.",
        },
        {"role": "user", "content": "What should I see first?"},
    ]

    with tracer.start_as_current_span("scout-test-phoenix-langchain-multiturn"):
        result = agent.invoke({"messages": messages})
        print(f"LangChain multiturn: {result['messages'][-1].content}")


async def create_langchain_multiturn_tools_trace(tracer: Any) -> None:
    """Create a LangChain multi-turn trace with tool calls across turns.

    3 conversational turns:
    - Turn 1: Ask weather in SF -> tool call -> response
    - Turn 2: Ask weather in NYC -> tool call -> response
    - Turn 3: Ask comparison -> no tool -> response
    """
    try:
        from langchain.agents import create_agent
    except ImportError:
        print("Skipping LangChain multiturn-tools trace (langchain not installed)")
        return

    def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        return _get_weather_tool(city)

    agent = create_agent(
        model="openai:gpt-4o-mini",
        tools=[get_weather],
        system_prompt="You are a helpful weather assistant. Use tools when needed.",
    )

    with tracer.start_as_current_span("scout-test-phoenix-langchain-multiturn-tools"):
        # Turn 1: Ask about SF weather (triggers tool)
        result1 = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "What's the weather in San Francisco?",
                    }
                ]
            },
        )
        print(f"LangChain multiturn-tools turn 1: {result1['messages'][-1].content}")

        # Turn 2: Continue conversation asking about NYC
        messages = result1["messages"] + [
            {"role": "user", "content": "What about New York?"}
        ]
        result2 = agent.invoke({"messages": messages})
        print(f"LangChain multiturn-tools turn 2: {result2['messages'][-1].content}")

        # Turn 3: Ask comparison (no tool needed)
        messages = result2["messages"] + [
            {"role": "user", "content": "Which city is warmer?"}
        ]
        result3 = agent.invoke({"messages": messages})
        print(f"LangChain multiturn-tools turn 3: {result3['messages'][-1].content}")


# =============================================================================
# PydanticAI Trace Functions
# =============================================================================


async def create_pydanticai_simple_trace(tracer: Any) -> None:
    """Create a simple PydanticAI agent trace."""
    try:
        from pydantic_ai import Agent
    except ImportError:
        print("Skipping PydanticAI simple trace (pydantic-ai not installed)")
        return

    agent = Agent(
        "openai:gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
    )

    with tracer.start_as_current_span("scout-test-phoenix-pydanticai-simple"):
        result = await agent.run("Say 'Hello, Scout test!' and nothing else.")
        print(f"PydanticAI simple: {result.output}")


async def create_pydanticai_tools_trace(tracer: Any) -> None:
    """Create a PydanticAI agent trace with tool calls."""
    try:
        from pydantic_ai import Agent
    except ImportError:
        print("Skipping PydanticAI tools trace (pydantic-ai not installed)")
        return

    agent = Agent(
        "openai:gpt-4o-mini",
        system_prompt="You are a helpful weather assistant.",
    )

    @agent.tool_plain
    def get_weather(city: str) -> str:
        """Get the current weather for a city.

        Args:
            city: The city name to get weather for.

        Returns:
            Weather information as a string.
        """
        return f"The weather in {city} is sunny with a temperature of 72F."

    with tracer.start_as_current_span("scout-test-phoenix-pydanticai-tools"):
        result = await agent.run("What's the weather in San Francisco?")
        print(f"PydanticAI tools: {result.output}")


async def create_pydanticai_multiturn_trace(tracer: Any) -> None:
    """Create a multi-turn PydanticAI agent conversation trace."""
    try:
        from pydantic_ai import Agent
    except ImportError:
        print("Skipping PydanticAI multiturn trace (pydantic-ai not installed)")
        return

    agent = Agent(
        "openai:gpt-4o-mini",
        system_prompt="You are a helpful math tutor.",
    )

    with tracer.start_as_current_span("scout-test-phoenix-pydanticai-multiturn"):
        # Turn 1
        result1 = await agent.run("What is 2 + 2?")
        print(f"PydanticAI multiturn turn 1: {result1.output}")

        # Turn 2 - continue conversation
        result2 = await agent.run(
            "What about 3 + 3?",
            message_history=result1.new_messages(),
        )
        print(f"PydanticAI multiturn turn 2: {result2.output}")

        # Turn 3 - continue conversation
        result3 = await agent.run(
            "And 5 + 5?",
            message_history=result2.all_messages(),
        )
        print(f"PydanticAI multiturn turn 3: {result3.output}")


async def create_pydanticai_multiturn_tools_trace(tracer: Any) -> None:
    """Create a multi-turn PydanticAI agent trace with tool calls across turns."""
    try:
        from pydantic_ai import Agent
    except ImportError:
        print("Skipping PydanticAI multiturn-tools trace (pydantic-ai not installed)")
        return

    agent = Agent(
        "openai:gpt-4o-mini",
        system_prompt="You are a helpful weather assistant.",
    )

    @agent.tool_plain
    def get_weather(city: str) -> str:
        """Get the current weather for a city.

        Args:
            city: The city name to get weather for.

        Returns:
            Weather information as a string.
        """
        weather_data = {
            "san francisco": "sunny with a temperature of 72F",
            "new york": "cloudy with a temperature of 45F",
        }
        return f"The weather in {city} is {weather_data.get(city.lower(), 'unknown')}."

    with tracer.start_as_current_span("scout-test-phoenix-pydanticai-multiturn-tools"):
        # Turn 1: Ask about SF weather (triggers tool)
        result1 = await agent.run("What's the weather in San Francisco?")
        print(f"PydanticAI multiturn-tools turn 1: {result1.output}")

        # Turn 2: Ask about NYC weather (triggers tool again)
        result2 = await agent.run(
            "What about New York?",
            message_history=result1.all_messages(),
        )
        print(f"PydanticAI multiturn-tools turn 2: {result2.output}")

        # Turn 3: Ask comparison (no tool needed, uses context)
        result3 = await agent.run(
            "Which city is warmer?",
            message_history=result2.all_messages(),
        )
        print(f"PydanticAI multiturn-tools turn 3: {result3.output}")


async def main(force: bool = False) -> None:
    """Run all trace creation functions.

    Args:
        force: If True, create traces even if they already exist
    """
    if not force:
        print("Checking if bootstrap is complete...")
        if await is_bootstrap_complete():
            print("Bootstrap already complete! All required traces exist.")
            print("Use --force to recreate traces anyway.")
            return

    tracer = setup_instrumentation()

    print()
    print("Creating test traces in Phoenix")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    print("Creating OpenAI simple trace...")
    await create_openai_simple_trace(tracer)

    print("Creating OpenAI multi-turn trace...")
    await create_openai_multiturn_trace(tracer)

    print("Creating OpenAI tools trace...")
    await create_openai_tools_trace(tracer)

    print("Creating OpenAI multi-turn tools trace...")
    await create_openai_multiturn_tools_trace(tracer)

    print("Creating Anthropic simple trace...")
    await create_anthropic_simple_trace(tracer)

    print("Creating Anthropic multi-turn trace...")
    await create_anthropic_multiturn_trace(tracer)

    print("Creating Anthropic tools trace...")
    await create_anthropic_tools_trace(tracer)

    print("Creating Anthropic multi-turn tools trace...")
    await create_anthropic_multiturn_tools_trace(tracer)

    # Create Google GenAI traces (optional)
    print("Creating Google GenAI simple trace...")
    await create_google_simple_trace(tracer)

    print("Creating Google GenAI multi-turn trace...")
    await create_google_multiturn_trace(tracer)

    print("Creating Google GenAI tools trace...")
    await create_google_tools_trace(tracer)

    print("Creating Google GenAI multi-turn tools trace...")
    await create_google_multiturn_tools_trace(tracer)

    # Create LangChain traces (optional)
    print("Creating LangChain agent trace...")
    try:
        await create_langchain_agent_trace(tracer)
    except Exception as e:
        print(f"LangChain agent trace failed: {e}")

    print("Creating LangChain multi-turn trace...")
    try:
        await create_langchain_multiturn_trace(tracer)
    except Exception as e:
        print(f"LangChain multiturn trace failed: {e}")

    print("Creating LangChain multi-turn tools trace...")
    try:
        await create_langchain_multiturn_tools_trace(tracer)
    except Exception as e:
        print(f"LangChain multiturn-tools trace failed: {e}")

    # Create PydanticAI traces (optional)
    print("Creating PydanticAI simple trace...")
    try:
        await create_pydanticai_simple_trace(tracer)
    except Exception as e:
        print(f"PydanticAI simple trace failed: {e}")

    print("Creating PydanticAI tools trace...")
    try:
        await create_pydanticai_tools_trace(tracer)
    except Exception as e:
        print(f"PydanticAI tools trace failed: {e}")

    print("Creating PydanticAI multi-turn trace...")
    try:
        await create_pydanticai_multiturn_trace(tracer)
    except Exception as e:
        print(f"PydanticAI multiturn trace failed: {e}")

    print("Creating PydanticAI multi-turn tools trace...")
    try:
        await create_pydanticai_multiturn_tools_trace(tracer)
    except Exception as e:
        print(f"PydanticAI multiturn-tools trace failed: {e}")

    print()
    print("Bootstrap complete! Traces should appear in Phoenix shortly.")
    print(
        "Run integration tests with: "
        "PHOENIX_RUN_TESTS=1 pytest tests/sources/phoenix_source/test_phoenix.py -v"
    )


if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)

    if not check_env_vars():
        sys.exit(1)

    import asyncio

    force = "--force" in sys.argv
    asyncio.run(main(force=force))
