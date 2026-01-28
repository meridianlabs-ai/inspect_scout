# type: ignore

"""Bootstrap script to create test traces in Logfire.

This script creates real traces using various LLM providers with Logfire
instrumentation. Run this once to populate the test project with data
before running integration tests.

Required environment variables:
- OPENAI_API_KEY: For OpenAI traces
- ANTHROPIC_API_KEY: For Anthropic traces
- LOGFIRE_READ_TOKEN: For querying existing traces (generate from Logfire dashboard)
- GOOGLE_API_KEY: For Google GenAI traces (optional)

Logfire authentication (for writing traces):
    Run `logfire auth` to authenticate via browser (stores credentials in ~/.logfire/default.toml)
    Run `logfire projects use scout-import-testing` to select the test project

Logfire read token (for querying traces):
    Go to https://logfire-us.pydantic.dev/<org>/<project>/settings/read-tokens
    Generate a read token and add LOGFIRE_READ_TOKEN=<token> to .env

Usage:
    python -m tests.sources.logfire_source.bootstrap          # Creates traces if not exist
    python -m tests.sources.logfire_source.bootstrap --force  # Recreates all traces
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

# Required trace names that must exist for tests to pass
REQUIRED_TRACES = [
    "scout-test-openai-simple-v2",
    "scout-test-openai-multiturn-v2",
    "scout-test-openai-tools-v2",
    "scout-test-openai-multiturn-tools-v2",
    "scout-test-anthropic-simple-v2",
    "scout-test-anthropic-multiturn-v2",
    "scout-test-anthropic-tools-v2",
    "scout-test-anthropic-multiturn-tools-v2",
    "scout-test-pydantic-ai-simple-v2",
    "scout-test-pydantic-ai-tools-v2",
    "scout-test-pydantic-ai-multiturn-tools-v2",
    "scout-test-pydantic-ai-openai-multiturn-v2",
    "scout-test-pydantic-ai-anthropic-multiturn-v2",
    "scout-test-pydantic-ai-google-multiturn-v2",
]

# Optional traces (Google GenAI direct instrumentation)
OPTIONAL_TRACES = [
    "scout-test-google-genai-simple-v2",
]


def check_dependencies() -> bool:
    """Check if required packages are installed."""
    required = ["logfire", "openai", "anthropic", "pydantic_ai"]
    missing = []

    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False

    return True


def check_env_vars() -> bool:
    """Check if required environment variables are set."""
    required = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    missing = [v for v in required if not os.environ.get(v)]

    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        return False

    return True


async def is_bootstrap_complete() -> bool:
    """Check if all required traces already exist in Logfire.

    Requires LOGFIRE_READ_TOKEN environment variable for querying.

    Returns:
        True if all required traces exist, False otherwise
    """
    read_token = os.environ.get("LOGFIRE_READ_TOKEN")
    if not read_token:
        print("LOGFIRE_READ_TOKEN not set - cannot check for existing traces")
        print("Generate a read token from Logfire dashboard and add to .env")
        return False

    try:
        from logfire.query_client import AsyncLogfireQueryClient
    except ImportError:
        return False

    try:
        client = AsyncLogfireQueryClient(read_token=read_token)

        # Query for existing trace names matching our scout-test pattern
        # span_name contains the name we set with logfire.span()
        query = """
            SELECT DISTINCT span_name
            FROM records
            WHERE span_name LIKE 'scout-test-%'
        """
        result = await client.query_json_rows(query)

        # Result is a dict with 'columns' and 'rows' keys
        rows = result.get("rows", [])
        existing_names = {row["span_name"] for row in rows}

        # Check if all required traces exist
        missing = set(REQUIRED_TRACES) - existing_names
        if missing:
            print(f"Missing traces: {missing}")
            return False

        print(f"Found {len(existing_names)} existing traces")
        return True

    except Exception as e:
        print(f"Error checking bootstrap status: {e}")
        return False


async def create_openai_simple_trace() -> None:
    """Create a simple OpenAI trace."""
    import logfire
    import openai

    logfire.instrument_openai()

    client = openai.OpenAI()

    with logfire.span("scout-test-openai-simple-v2"):
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "Say 'Hello, Scout test!' and nothing else.",
                },
            ],
        )
        print(f"OpenAI simple: {response.choices[0].message.content}")


async def create_openai_multiturn_trace() -> None:
    """Create a multi-turn OpenAI conversation trace."""
    import logfire
    import openai

    logfire.instrument_openai()

    client = openai.OpenAI()

    with logfire.span("scout-test-openai-multiturn-v2"):
        messages: list[dict[str, str]] = [
            {"role": "system", "content": "You are a helpful math tutor."},
            {"role": "user", "content": "What is 2 + 2?"},
        ]

        # First turn
        response1 = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=messages,  # type: ignore[arg-type]
        )
        print(f"OpenAI multiturn turn 1: {response1.choices[0].message.content}")

        messages.append(
            {"role": "assistant", "content": response1.choices[0].message.content or ""}
        )
        messages.append({"role": "user", "content": "What about 3 + 3?"})

        # Second turn
        response2 = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=messages,  # type: ignore[arg-type]
        )
        print(f"OpenAI multiturn turn 2: {response2.choices[0].message.content}")

        messages.append(
            {"role": "assistant", "content": response2.choices[0].message.content or ""}
        )
        messages.append({"role": "user", "content": "And 5 + 5?"})

        # Third turn
        response3 = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=messages,  # type: ignore[arg-type]
        )
        print(f"OpenAI multiturn turn 3: {response3.choices[0].message.content}")


async def create_openai_tools_trace() -> None:
    """Create an OpenAI trace with tool calls."""
    import json

    import logfire
    import openai

    logfire.instrument_openai()

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

    with logfire.span("scout-test-openai-tools-v2"):
        # First call - should trigger tool use
        response = client.chat.completions.create(  # type: ignore[call-overload]
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "user", "content": "What's the weather in San Francisco?"},
            ],
            tools=tools,
            tool_choice="auto",
        )

        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            print(f"OpenAI tools: Tool called - {tool_call.function.name}")

            # Simulate tool response
            response2 = client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
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
                tools=tools,  # type: ignore[arg-type]
            )
            print(f"OpenAI tools: {response2.choices[0].message.content}")


async def create_openai_multiturn_tools_trace() -> None:
    """Create a multi-turn OpenAI trace with tool calls across turns."""
    import json

    import logfire
    import openai

    logfire.instrument_openai()

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

    with logfire.span("scout-test-openai-multiturn-tools-v2"):
        messages: list[Any] = [
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ]

        # Turn 1: Ask about SF weather
        response1 = client.chat.completions.create(  # type: ignore[call-overload]
            model="gpt-5-mini-2025-08-07",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        if response1.choices[0].message.tool_calls:
            tool_call1 = response1.choices[0].message.tool_calls[0]
            print(
                f"OpenAI multiturn-tools turn 1: Tool called - {tool_call1.function.name}"
            )
            messages.append(response1.choices[0].message)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call1.id,
                    "content": json.dumps({"temperature": 72, "condition": "sunny"}),
                }
            )

            # Get response after tool
            response1b = client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=messages,
                tools=tools,  # type: ignore[arg-type]
            )
            messages.append(response1b.choices[0].message)
            print(
                f"OpenAI multiturn-tools turn 1 response: {response1b.choices[0].message.content}"
            )

        # Turn 2: Ask about NYC weather
        messages.append({"role": "user", "content": "What about New York?"})

        response2 = client.chat.completions.create(  # type: ignore[call-overload]
            model="gpt-5-mini-2025-08-07",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        if response2.choices[0].message.tool_calls:
            tool_call2 = response2.choices[0].message.tool_calls[0]
            print(
                f"OpenAI multiturn-tools turn 2: Tool called - {tool_call2.function.name}"
            )
            messages.append(response2.choices[0].message)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call2.id,
                    "content": json.dumps({"temperature": 45, "condition": "cloudy"}),
                }
            )

            # Get response after tool
            response2b = client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=messages,
                tools=tools,  # type: ignore[arg-type]
            )
            messages.append(response2b.choices[0].message)
            print(
                f"OpenAI multiturn-tools turn 2 response: {response2b.choices[0].message.content}"
            )

        # Turn 3: Ask comparison (no tool needed)
        messages.append({"role": "user", "content": "Which city is warmer?"})

        response3 = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=messages,
            tools=tools,  # type: ignore[arg-type]
        )
        print(f"OpenAI multiturn-tools turn 3: {response3.choices[0].message.content}")


async def create_anthropic_simple_trace() -> None:
    """Create a simple Anthropic trace."""
    import anthropic
    import logfire

    logfire.instrument_anthropic()

    client = anthropic.Anthropic()

    with logfire.span("scout-test-anthropic-simple-v2"):
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


async def create_anthropic_multiturn_trace() -> None:
    """Create a multi-turn Anthropic conversation trace."""
    import anthropic
    import logfire

    logfire.instrument_anthropic()

    client = anthropic.Anthropic()

    with logfire.span("scout-test-anthropic-multiturn-v2"):
        messages: list[dict[str, str]] = [
            {"role": "user", "content": "What is 2 + 2?"},
        ]

        # First turn
        response1 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful math tutor.",
            messages=messages,  # type: ignore[arg-type]
        )
        first_block1 = response1.content[0] if response1.content else None
        content1 = (
            first_block1.text if first_block1 and hasattr(first_block1, "text") else ""
        )
        print(f"Anthropic multiturn turn 1: {content1}")

        messages.append({"role": "assistant", "content": content1})
        messages.append({"role": "user", "content": "What about 3 + 3?"})

        # Second turn
        response2 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful math tutor.",
            messages=messages,  # type: ignore[arg-type]
        )
        first_block2 = response2.content[0] if response2.content else None
        content2 = (
            first_block2.text if first_block2 and hasattr(first_block2, "text") else ""
        )
        print(f"Anthropic multiturn turn 2: {content2}")

        messages.append({"role": "assistant", "content": content2})
        messages.append({"role": "user", "content": "And 5 + 5?"})

        # Third turn
        response3 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful math tutor.",
            messages=messages,  # type: ignore[arg-type]
        )
        first_block3 = response3.content[0] if response3.content else None
        content3 = (
            first_block3.text if first_block3 and hasattr(first_block3, "text") else ""
        )
        print(f"Anthropic multiturn turn 3: {content3}")


async def create_anthropic_tools_trace() -> None:
    """Create an Anthropic trace with tool calls."""
    import anthropic
    import logfire

    logfire.instrument_anthropic()

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

    with logfire.span("scout-test-anthropic-tools-v2"):
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

            # Simulate tool response
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


async def create_anthropic_multiturn_tools_trace() -> None:
    """Create a multi-turn Anthropic trace with tool calls across turns."""
    import anthropic
    import logfire

    logfire.instrument_anthropic()

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

    with logfire.span("scout-test-anthropic-multiturn-tools-v2"):
        messages: list[Any] = [
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ]

        # Turn 1: Ask about SF weather
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
            print(
                f"Anthropic multiturn-tools turn 1: Tool called - {tool_use_block1.name}"
            )
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

            # Get response after tool
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
            print(f"Anthropic multiturn-tools turn 1 response: {content1}")

        # Turn 2: Ask about NYC weather
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
            print(
                f"Anthropic multiturn-tools turn 2: Tool called - {tool_use_block2.name}"
            )
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

            # Get response after tool
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
            print(f"Anthropic multiturn-tools turn 2 response: {content2}")

        # Turn 3: Ask comparison (no tool needed)
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


async def create_google_genai_trace() -> None:
    """Create a Google GenAI trace (optional)."""
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Skipping Google GenAI trace (GOOGLE_API_KEY not set)")
        return

    try:
        import logfire
        from google import genai

        # Enable content capture for Google GenAI
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
        logfire.instrument_google_genai()

        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

        with logfire.span("scout-test-google-genai-simple-v2"):
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents="Say 'Hello, Scout test!' and nothing else.",
            )
            print(f"Google GenAI simple: {response.text}")

    except ImportError:
        print("Skipping Google GenAI trace (google-genai not installed)")
    except Exception as e:
        print(f"Google GenAI trace failed: {e}")


async def create_pydantic_ai_simple_trace() -> None:
    """Create a simple Pydantic AI agent trace."""
    import logfire
    from pydantic_ai import Agent

    logfire.instrument_pydantic_ai()

    agent = Agent(
        "openai:gpt-5-mini-2025-08-07",
        system_prompt="You are a helpful assistant.",
    )

    with logfire.span("scout-test-pydantic-ai-simple-v2"):
        result = await agent.run("Say 'Hello, Scout test!' and nothing else.")
        print(f"Pydantic AI simple: {result.output}")


async def create_pydantic_ai_tools_trace() -> None:
    """Create a Pydantic AI agent trace with tool calls."""
    import logfire
    from pydantic_ai import Agent

    logfire.instrument_pydantic_ai()

    agent = Agent(
        "openai:gpt-5-mini-2025-08-07",
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

    with logfire.span("scout-test-pydantic-ai-tools-v2"):
        result = await agent.run("What's the weather in San Francisco?")
        print(f"Pydantic AI tools: {result.output}")


async def create_pydantic_ai_multiturn_tools_trace() -> None:
    """Create a multi-turn Pydantic AI agent trace with tool calls across turns."""
    import logfire
    from pydantic_ai import Agent

    logfire.instrument_pydantic_ai()

    agent = Agent(
        "openai:gpt-5-mini-2025-08-07",
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

    with logfire.span("scout-test-pydantic-ai-multiturn-tools-v2"):
        # Turn 1: Ask about SF weather (triggers tool)
        result1 = await agent.run("What's the weather in San Francisco?")
        print(f"Pydantic AI multiturn-tools turn 1: {result1.output}")

        # Turn 2: Ask about NYC weather (triggers tool again)
        result2 = await agent.run(
            "What about New York?",
            message_history=result1.all_messages(),
        )
        print(f"Pydantic AI multiturn-tools turn 2: {result2.output}")

        # Turn 3: Ask comparison (no tool needed, uses context)
        result3 = await agent.run(
            "Which city is warmer?",
            message_history=result2.all_messages(),
        )
        print(f"Pydantic AI multiturn-tools turn 3: {result3.output}")


async def create_pydantic_ai_openai_multiturn_trace() -> None:
    """Create a multi-turn Pydantic AI agent conversation trace using OpenAI."""
    import logfire
    from pydantic_ai import Agent

    logfire.instrument_pydantic_ai()

    agent = Agent(
        "openai:gpt-5-mini-2025-08-07",
        system_prompt="You are a helpful math tutor.",
    )

    with logfire.span("scout-test-pydantic-ai-openai-multiturn-v2"):
        # First turn
        result1 = await agent.run("What is 2 + 2?")
        print(f"Pydantic AI OpenAI multiturn turn 1: {result1.output}")

        # Second turn - continue conversation
        result2 = await agent.run(
            "What about 3 + 3?",
            message_history=result1.new_messages(),
        )
        print(f"Pydantic AI OpenAI multiturn turn 2: {result2.output}")

        # Third turn - continue conversation
        result3 = await agent.run(
            "And 5 + 5?",
            message_history=result2.all_messages(),
        )
        print(f"Pydantic AI OpenAI multiturn turn 3: {result3.output}")


async def create_pydantic_ai_anthropic_multiturn_trace() -> None:
    """Create a multi-turn Pydantic AI agent conversation trace using Anthropic."""
    import logfire
    from pydantic_ai import Agent

    logfire.instrument_pydantic_ai()

    agent = Agent(
        "anthropic:claude-haiku-4-5-20251001",
        system_prompt="You are a helpful math tutor.",
    )

    with logfire.span("scout-test-pydantic-ai-anthropic-multiturn-v2"):
        # First turn
        result1 = await agent.run("What is 2 + 2?")
        print(f"Pydantic AI Anthropic multiturn turn 1: {result1.output}")

        # Second turn - continue conversation
        result2 = await agent.run(
            "What about 3 + 3?",
            message_history=result1.new_messages(),
        )
        print(f"Pydantic AI Anthropic multiturn turn 2: {result2.output}")

        # Third turn - continue conversation
        result3 = await agent.run(
            "And 5 + 5?",
            message_history=result2.all_messages(),
        )
        print(f"Pydantic AI Anthropic multiturn turn 3: {result3.output}")


async def create_pydantic_ai_google_multiturn_trace() -> None:
    """Create a multi-turn Pydantic AI agent conversation trace using Google GenAI."""
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Skipping Pydantic AI Google trace (GOOGLE_API_KEY not set)")
        return

    try:
        import logfire
        from pydantic_ai import Agent

        logfire.instrument_pydantic_ai()

        agent = Agent(
            "google-gla:gemini-3-flash-preview",
            system_prompt="You are a helpful math tutor.",
        )

        with logfire.span("scout-test-pydantic-ai-google-multiturn-v2"):
            # First turn
            result1 = await agent.run("What is 2 + 2?")
            print(f"Pydantic AI Google multiturn turn 1: {result1.output}")

            # Second turn - continue conversation
            result2 = await agent.run(
                "What about 3 + 3?",
                message_history=result1.new_messages(),
            )
            print(f"Pydantic AI Google multiturn turn 2: {result2.output}")

            # Third turn - continue conversation
            result3 = await agent.run(
                "And 5 + 5?",
                message_history=result2.all_messages(),
            )
            print(f"Pydantic AI Google multiturn turn 3: {result3.output}")

    except ImportError as e:
        print(f"Skipping Pydantic AI Google trace (missing dependency): {e}")
    except Exception as e:
        print(f"Pydantic AI Google trace failed: {e}")


async def main(force: bool = False) -> None:
    """Run all trace creation functions.

    Args:
        force: If True, create traces even if they already exist
    """
    import logfire

    # Configure logfire using stored credentials from ~/.logfire/default.toml
    # (run `logfire auth` and `logfire projects use scout-import-testing` first)
    logfire.configure(
        service_name="inspect-scout-bootstrap",
        send_to_logfire=True,
    )

    # Check if bootstrap is already complete
    if not force:
        print("Checking if bootstrap is complete...")
        if await is_bootstrap_complete():
            print("Bootstrap already complete! All required traces exist.")
            print("Use --force to recreate traces anyway.")
            return

    print()
    print("Creating test traces in Logfire (using stored credentials)")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Create OpenAI traces
    print("Creating OpenAI simple trace...")
    await create_openai_simple_trace()

    print("Creating OpenAI multi-turn trace...")
    await create_openai_multiturn_trace()

    print("Creating OpenAI tools trace...")
    await create_openai_tools_trace()

    print("Creating OpenAI multi-turn tools trace...")
    await create_openai_multiturn_tools_trace()

    # Create Anthropic traces
    print("Creating Anthropic simple trace...")
    await create_anthropic_simple_trace()

    print("Creating Anthropic multi-turn trace...")
    await create_anthropic_multiturn_trace()

    print("Creating Anthropic tools trace...")
    await create_anthropic_tools_trace()

    print("Creating Anthropic multi-turn tools trace...")
    await create_anthropic_multiturn_tools_trace()

    # Create Google GenAI trace (optional)
    print("Creating Google GenAI trace (if available)...")
    await create_google_genai_trace()

    # Create Pydantic AI traces
    print("Creating Pydantic AI simple trace...")
    await create_pydantic_ai_simple_trace()

    print("Creating Pydantic AI tools trace...")
    await create_pydantic_ai_tools_trace()

    print("Creating Pydantic AI multi-turn tools trace...")
    await create_pydantic_ai_multiturn_tools_trace()

    print("Creating Pydantic AI OpenAI multi-turn trace...")
    await create_pydantic_ai_openai_multiturn_trace()

    print("Creating Pydantic AI Anthropic multi-turn trace...")
    await create_pydantic_ai_anthropic_multiturn_trace()

    print("Creating Pydantic AI Google multi-turn trace...")
    await create_pydantic_ai_google_multiturn_trace()

    print()
    print("Bootstrap complete! Traces should appear in Logfire shortly.")
    print(
        "Run integration tests with: LOGFIRE_RUN_TESTS=1 pytest tests/sources/logfire_source/test_logfire.py -v"
    )


if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)

    if not check_env_vars():
        sys.exit(1)

    import asyncio

    force = "--force" in sys.argv
    asyncio.run(main(force=force))
