# type: ignore
"""Bootstrap test data for W&B Weave integration tests.

Creates real LLM traces in W&B Weave by invoking models through:
1. Direct OpenAI API calls with Weave tracing
2. Direct Anthropic API calls with Weave tracing
3. Agent workflows with tool calls

This module is marked as type: ignore because weave and other
dependencies are not in the dev requirements.

Usage:
    # Check if bootstrap is complete
    from tests.sources.weave_source.bootstrap import is_bootstrap_complete
    if not is_bootstrap_complete():
        bootstrap_traces()

    # Or run directly
    python -c "from tests.sources.weave_source.bootstrap import main; main()"

Environment Variables:
    WANDB_API_KEY: Required for API access
    WEAVE_PROJECT: Optional, defaults to "inspect-scout/scout-tests"
    OPENAI_API_KEY: Required for OpenAI traces
    ANTHROPIC_API_KEY: Required for Anthropic traces
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any

# Load .env file if available
try:
    import dotenv

    dotenv.load_dotenv()
except ImportError:
    pass


# =============================================================================
# Dependency Installation
# =============================================================================

# Required packages for bootstrap
BOOTSTRAP_PACKAGES = [
    "weave",
    "openai",
    "anthropic",
]


def check_package_installed(package: str) -> bool:
    """Check if a package is installed."""
    try:
        __import__(package.replace("-", "_"))
        return True
    except ImportError:
        return False


def install_packages(packages: list[str]) -> None:
    """Install packages using pip."""
    for package in packages:
        if not check_package_installed(package):
            print(f"  Installing {package}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package, "-q"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                print(f"  Warning: Failed to install {package}")


def ensure_dependencies() -> None:
    """Ensure all required packages are installed."""
    print("\nChecking dependencies...")

    missing = [p for p in BOOTSTRAP_PACKAGES if not check_package_installed(p)]
    if missing:
        print(f"  Missing packages: {', '.join(missing)}")
        print("  Installing missing packages...")
        install_packages(missing)
        print("  Dependencies installed!")
    else:
        print("  All dependencies available")


# Test project name
WEAVE_TEST_PROJECT = os.environ.get("WEAVE_PROJECT", "inspect-scout/scout-tests")

# Required trace names for idempotency check
REQUIRED_TRACES = [
    "scout-test-openai-simple",
    "scout-test-openai-tools",
    "scout-test-openai-multiturn",
    "scout-test-openai-multiturn-tools",
    "scout-test-anthropic-simple",
    "scout-test-anthropic-tools",
    "scout-test-anthropic-multiturn",
    "scout-test-anthropic-multiturn-tools",
]

# Test tag for filtering
SCOUT_TEST_TAG = "scout-test"


def get_weave_client() -> Any:
    """Get a Weave client for bootstrap operations.

    Returns:
        Weave client instance

    Raises:
        ImportError: If weave is not installed
        ValueError: If WANDB_API_KEY is not set
    """
    try:
        import weave
    except ImportError as e:
        raise ImportError(
            "weave package required for bootstrap. Install with: pip install weave"
        ) from e

    api_key = os.environ.get("WANDB_API_KEY")
    if not api_key:
        raise ValueError("WANDB_API_KEY environment variable required")

    return weave.init(WEAVE_TEST_PROJECT)


def is_bootstrap_complete() -> bool:
    """Check if all required test traces exist in Weave.

    Returns:
        True if all required traces exist
    """
    try:
        client = get_weave_client()
    except (ImportError, ValueError):
        return False

    # Query for traces with scout-test attribute
    try:
        calls = list(client.get_calls())
        existing_names = set()
        for call in calls:
            attrs = getattr(call, "attributes", {}) or {}
            if attrs.get("test_name"):
                existing_names.add(attrs["test_name"])
    except Exception:
        return False

    # Check if all required traces exist
    missing = set(REQUIRED_TRACES) - existing_names
    if missing:
        print(f"Missing traces: {missing}")
        return False

    return True


# =============================================================================
# Tool Definitions
# =============================================================================

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name to get weather for.",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time in a timezone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "The timezone name.",
                    }
                },
                "required": ["timezone"],
            },
        },
    },
]

ANTHROPIC_TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name to get weather for.",
                }
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_time",
        "description": "Get the current time in a timezone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "The timezone name.",
                }
            },
            "required": ["timezone"],
        },
    },
]


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a test tool by name.

    Args:
        name: Tool function name
        arguments: Tool arguments

    Returns:
        Tool execution result
    """
    weathers = {
        "San Francisco": "Foggy, 58F",
        "New York": "Sunny, 72F",
        "London": "Rainy, 55F",
        "Tokyo": "Cloudy, 68F",
    }

    if name == "get_weather":
        city = arguments.get("city", "")
        return weathers.get(city, f"Weather data not available for {city}")
    elif name == "get_time":
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        return f"Unknown tool: {name}"


# =============================================================================
# OpenAI Bootstrap Functions
# =============================================================================


def bootstrap_openai_simple() -> None:
    """Create a simple OpenAI trace without tools."""
    import weave
    from openai import OpenAI

    print("  Creating: scout-test-openai-simple")

    client = OpenAI()

    @weave.op()
    def scout_test_openai_simple() -> str:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"},
            ],
        )
        return response.choices[0].message.content or ""

    # Add test metadata as attributes
    with weave.attributes(
        {"test_name": "scout-test-openai-simple", "tag": SCOUT_TEST_TAG}
    ):
        scout_test_openai_simple()


def bootstrap_openai_tools() -> None:
    """Create an OpenAI trace with tool calls."""
    import weave
    from openai import OpenAI

    print("  Creating: scout-test-openai-tools")

    client = OpenAI()

    @weave.op()
    def scout_test_openai_tools() -> str:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Use tools when appropriate.",
            },
            {
                "role": "user",
                "content": "What's the weather in San Francisco?",
            },
        ]

        # First call - should request tool use
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=OPENAI_TOOLS,
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump())

        # Process tool calls
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                result = execute_tool(tool_name, tool_args)

                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": result}
                )

            # Second call with tool results
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=OPENAI_TOOLS,
            )

        return response.choices[0].message.content or ""

    with weave.attributes(
        {"test_name": "scout-test-openai-tools", "tag": SCOUT_TEST_TAG}
    ):
        scout_test_openai_tools()


def bootstrap_openai_multiturn() -> None:
    """Create a multi-turn OpenAI conversation trace."""
    import weave
    from openai import OpenAI

    print("  Creating: scout-test-openai-multiturn")

    client = OpenAI()

    @weave.op()
    def scout_test_openai_multiturn() -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "I'm planning a trip to Japan."},
        ]

        # First turn
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        messages.append(
            {"role": "assistant", "content": response.choices[0].message.content}
        )

        # Second turn
        messages.append({"role": "user", "content": "What should I see in Tokyo?"})
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        messages.append(
            {"role": "assistant", "content": response.choices[0].message.content}
        )

        # Third turn
        messages.append(
            {"role": "user", "content": "What's the best time of year to visit?"}
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        return response.choices[0].message.content or ""

    with weave.attributes(
        {"test_name": "scout-test-openai-multiturn", "tag": SCOUT_TEST_TAG}
    ):
        scout_test_openai_multiturn()


def bootstrap_openai_multiturn_tools() -> None:
    """Create a multi-turn OpenAI trace with tool calls across turns."""
    import weave
    from openai import OpenAI

    print("  Creating: scout-test-openai-multiturn-tools")

    client = OpenAI()

    @weave.op()
    def scout_test_openai_multiturn_tools() -> str:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": "You are a helpful weather assistant. Use tools when needed.",
            },
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ]

        # Turn 1: Ask about SF weather
        response1 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=OPENAI_TOOLS,
        )

        assistant_msg1 = response1.choices[0].message
        messages.append(assistant_msg1.model_dump())

        if assistant_msg1.tool_calls:
            for tool_call in assistant_msg1.tool_calls:
                result = execute_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments),
                )
                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": result}
                )

            response1b = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=OPENAI_TOOLS,
            )
            messages.append(response1b.choices[0].message.model_dump())

        # Turn 2: Ask about NYC weather
        messages.append({"role": "user", "content": "What about New York?"})

        response2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=OPENAI_TOOLS,
        )

        assistant_msg2 = response2.choices[0].message
        messages.append(assistant_msg2.model_dump())

        if assistant_msg2.tool_calls:
            for tool_call in assistant_msg2.tool_calls:
                result = execute_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments),
                )
                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": result}
                )

            response2b = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=OPENAI_TOOLS,
            )
            messages.append(response2b.choices[0].message.model_dump())

        # Turn 3: Ask comparison (no tool needed)
        messages.append({"role": "user", "content": "Which city is warmer?"})

        response3 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=OPENAI_TOOLS,
        )

        return response3.choices[0].message.content or ""

    with weave.attributes(
        {"test_name": "scout-test-openai-multiturn-tools", "tag": SCOUT_TEST_TAG}
    ):
        scout_test_openai_multiturn_tools()


# =============================================================================
# Anthropic Bootstrap Functions
# =============================================================================


def bootstrap_anthropic_simple() -> None:
    """Create a simple Anthropic trace without tools."""
    import weave
    from anthropic import Anthropic

    print("  Creating: scout-test-anthropic-simple")

    client = Anthropic()

    @weave.op()
    def scout_test_anthropic_simple() -> str:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a helpful assistant.",
            messages=[{"role": "user", "content": "What is the capital of France?"}],
        )
        # Extract text content
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    with weave.attributes(
        {"test_name": "scout-test-anthropic-simple", "tag": SCOUT_TEST_TAG}
    ):
        scout_test_anthropic_simple()


def bootstrap_anthropic_tools() -> None:
    """Create an Anthropic trace with tool calls."""
    import weave
    from anthropic import Anthropic

    print("  Creating: scout-test-anthropic-tools")

    client = Anthropic()

    @weave.op()
    def scout_test_anthropic_tools() -> str:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": "What's the weather in Tokyo?"}
        ]

        # First call
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a helpful assistant. Use tools when appropriate.",
            messages=messages,
            tools=ANTHROPIC_TOOLS,
        )

        # Add assistant response
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # Process tool calls
        tool_results = []
        for block in assistant_content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_args = block.input
                result = execute_tool(tool_name, tool_args)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

            # Second call with tool results
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                system="You are a helpful assistant. Use tools when appropriate.",
                messages=messages,
                tools=ANTHROPIC_TOOLS,
            )

        # Extract text content
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    with weave.attributes(
        {"test_name": "scout-test-anthropic-tools", "tag": SCOUT_TEST_TAG}
    ):
        scout_test_anthropic_tools()


def bootstrap_anthropic_multiturn() -> None:
    """Create a multi-turn Anthropic conversation trace."""
    import weave
    from anthropic import Anthropic

    print("  Creating: scout-test-anthropic-multiturn")

    client = Anthropic()

    @weave.op()
    def scout_test_anthropic_multiturn() -> str:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": "I'm learning to cook Italian food."},
        ]

        # First turn
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a helpful cooking assistant.",
            messages=messages,
        )
        assistant_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                assistant_text = block.text
                break
        messages.append({"role": "assistant", "content": assistant_text})

        # Second turn
        messages.append(
            {"role": "user", "content": "What's an easy pasta dish to start with?"}
        )
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a helpful cooking assistant.",
            messages=messages,
        )
        assistant_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                assistant_text = block.text
                break
        messages.append({"role": "assistant", "content": assistant_text})

        # Third turn
        messages.append({"role": "user", "content": "How do I make it al dente?"})
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a helpful cooking assistant.",
            messages=messages,
        )

        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    with weave.attributes(
        {"test_name": "scout-test-anthropic-multiturn", "tag": SCOUT_TEST_TAG}
    ):
        scout_test_anthropic_multiturn()


def bootstrap_anthropic_multiturn_tools() -> None:
    """Create a multi-turn Anthropic trace with tool calls across turns."""
    import weave
    from anthropic import Anthropic

    print("  Creating: scout-test-anthropic-multiturn-tools")

    client = Anthropic()

    @weave.op()
    def scout_test_anthropic_multiturn_tools() -> str:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ]

        # Turn 1: Ask about SF weather
        response1 = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a helpful weather assistant. Use tools when needed.",
            messages=messages,
            tools=ANTHROPIC_TOOLS,
        )

        messages.append({"role": "assistant", "content": response1.content})

        tool_results = []
        for block in response1.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

            response1b = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                system="You are a helpful weather assistant. Use tools when needed.",
                messages=messages,
                tools=ANTHROPIC_TOOLS,
            )
            text_content = ""
            for block in response1b.content:
                if hasattr(block, "text"):
                    text_content = block.text
                    break
            messages.append({"role": "assistant", "content": text_content})

        # Turn 2: Ask about NYC weather
        messages.append({"role": "user", "content": "What about New York?"})

        response2 = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a helpful weather assistant. Use tools when needed.",
            messages=messages,
            tools=ANTHROPIC_TOOLS,
        )

        messages.append({"role": "assistant", "content": response2.content})

        tool_results = []
        for block in response2.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

            response2b = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                system="You are a helpful weather assistant. Use tools when needed.",
                messages=messages,
                tools=ANTHROPIC_TOOLS,
            )
            text_content = ""
            for block in response2b.content:
                if hasattr(block, "text"):
                    text_content = block.text
                    break
            messages.append({"role": "assistant", "content": text_content})

        # Turn 3: Ask comparison (no tool needed)
        messages.append({"role": "user", "content": "Which city is warmer?"})

        response3 = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a helpful weather assistant. Use tools when needed.",
            messages=messages,
            tools=ANTHROPIC_TOOLS,
        )

        for block in response3.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    with weave.attributes(
        {"test_name": "scout-test-anthropic-multiturn-tools", "tag": SCOUT_TEST_TAG}
    ):
        scout_test_anthropic_multiturn_tools()


# =============================================================================
# Bootstrap Orchestration
# =============================================================================


def bootstrap_traces() -> None:
    """Bootstrap all traces."""
    import weave

    print("\nBootstrapping W&B Weave traces...")

    # Initialize weave
    weave.init(WEAVE_TEST_PROJECT)

    # OpenAI traces
    try:
        bootstrap_openai_simple()
    except Exception as e:
        print(f"  Failed to create OpenAI simple trace: {e}")

    try:
        bootstrap_openai_tools()
    except Exception as e:
        print(f"  Failed to create OpenAI tools trace: {e}")

    try:
        bootstrap_openai_multiturn()
    except Exception as e:
        print(f"  Failed to create OpenAI multi-turn trace: {e}")

    try:
        bootstrap_openai_multiturn_tools()
    except Exception as e:
        print(f"  Failed to create OpenAI multi-turn-tools trace: {e}")

    # Anthropic traces
    try:
        bootstrap_anthropic_simple()
    except Exception as e:
        print(f"  Failed to create Anthropic simple trace: {e}")

    try:
        bootstrap_anthropic_tools()
    except Exception as e:
        print(f"  Failed to create Anthropic tools trace: {e}")

    try:
        bootstrap_anthropic_multiturn()
    except Exception as e:
        print(f"  Failed to create Anthropic multi-turn trace: {e}")

    try:
        bootstrap_anthropic_multiturn_tools()
    except Exception as e:
        print(f"  Failed to create Anthropic multi-turn-tools trace: {e}")

    print("Bootstrap complete!")


def ensure_bootstrap() -> None:
    """Ensure test data exists, bootstrapping if needed."""
    if not is_bootstrap_complete():
        bootstrap_traces()


def main() -> None:
    """Main entry point for manual bootstrap."""
    print(f"W&B Weave Bootstrap for project: {WEAVE_TEST_PROJECT}")
    print("=" * 50)

    # Install missing dependencies
    ensure_dependencies()

    # Check current state
    print("\nChecking current state...")
    traces_complete = is_bootstrap_complete()

    print(f"  Traces complete: {traces_complete}")

    if traces_complete:
        print("\nBootstrap already complete!")
        return

    # Run bootstrap
    bootstrap_traces()

    print("\n" + "=" * 50)
    print("Bootstrap complete!")
    print(f"Project URL: https://wandb.ai/{WEAVE_TEST_PROJECT}/weave")


if __name__ == "__main__":
    main()
