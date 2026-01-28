# type: ignore
"""Bootstrap test data for LangSmith integration tests.

Creates real LLM traces in LangSmith by invoking models through:
1. LangSmith wrappers (wrap_openai, wrap_anthropic) for raw traces
2. LangChain agents for chain/agent run types

This module is marked as type: ignore because langchain and other
dependencies are not in the dev requirements.

Usage:
    # Check if bootstrap is complete
    from tests.sources.langsmith_source.bootstrap import is_bootstrap_complete
    if not is_bootstrap_complete():
        bootstrap_traces()
        bootstrap_dataset()

    # Or run directly
    python -c "from tests.sources.langsmith_source.bootstrap import main; main()"

Environment Variables:
    LANGSMITH_API_KEY: Required for API access
    LANGSMITH_PROJECT: Optional, defaults to "inspect-scout-tests"
    OPENAI_API_KEY: Required for OpenAI traces
    ANTHROPIC_API_KEY: Required for Anthropic traces
    GOOGLE_API_KEY: Required for Google/Gemini traces
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
    # Core tracing packages
    "langsmith",
    "openai",
    "anthropic",
    # Google/Gemini support
    "google-genai",
    # LangChain agent support (create_agent API)
    "langchain",
    "langchain-openai",
    "langchain-anthropic",
    "langchain-google-genai",
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
LANGSMITH_TEST_PROJECT = os.environ.get("LANGSMITH_PROJECT", "inspect-scout-tests-v2")

# Required trace names for idempotency check
REQUIRED_RAW_TRACES = [
    # Raw provider API traces (via LangSmith wrappers)
    "scout-test-raw-openai-simple-v2",
    "scout-test-raw-openai-tools-v2",
    "scout-test-raw-openai-multiturn-v2",
    "scout-test-raw-anthropic-tools-v2",
    "scout-test-raw-anthropic-multiturn-v2",
    # Note: raw Google trace removed - google.genai API has no LangSmith wrapper
]

REQUIRED_LANGCHAIN_TRACES = [
    # LangChain agent traces (creates chain/agent run types with nested LLM calls)
    "scout-test-langchain-openai-agent-v2",
    "scout-test-langchain-anthropic-agent-v2",
    "scout-test-langchain-google-agent-v2",
    # LangChain multi-turn traces (conversation without tools)
    "scout-test-langchain-openai-multiturn-v2",
    "scout-test-langchain-anthropic-multiturn-v2",
    "scout-test-langchain-google-multiturn-v2",
]

# Combined list for compatibility
REQUIRED_TRACES = REQUIRED_RAW_TRACES + REQUIRED_LANGCHAIN_TRACES

# Test dataset name
LANGSMITH_TEST_DATASET = "scout-test-dataset-v2"

# Test tag for filtering
SCOUT_TEST_TAG = "scout-test"


def get_langsmith_client() -> Any:
    """Get a LangSmith client for bootstrap operations.

    Returns:
        LangSmith Client instance

    Raises:
        ImportError: If langsmith is not installed
        ValueError: If LANGSMITH_API_KEY is not set
    """
    try:
        from langsmith import Client
    except ImportError as e:
        raise ImportError(
            "langsmith package required for bootstrap. "
            "Install with: pip install langsmith"
        ) from e

    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not api_key:
        raise ValueError("LANGSMITH_API_KEY environment variable required")

    return Client(api_key=api_key)


def is_bootstrap_complete() -> bool:
    """Check if all required test traces exist in LangSmith.

    Returns:
        True if all required traces exist with scout-test tag
    """
    try:
        client = get_langsmith_client()
    except (ImportError, ValueError):
        return False

    # Query for traces with scout-test tag
    try:
        existing_runs = list(
            client.list_runs(
                project_name=LANGSMITH_TEST_PROJECT,
                is_root=True,
                filter=f'has(tags, "{SCOUT_TEST_TAG}")',
            )
        )
    except Exception:
        return False

    existing_names = {run.name for run in existing_runs}

    # Check if all required traces exist
    missing = set(REQUIRED_TRACES) - existing_names
    if missing:
        print(f"Missing traces: {missing}")
        return False

    return True


def is_dataset_complete() -> bool:
    """Check if the test dataset exists with examples.

    Returns:
        True if the test dataset exists with at least 3 examples
    """
    try:
        client = get_langsmith_client()
    except (ImportError, ValueError):
        return False

    try:
        examples = list(client.list_examples(dataset_name=LANGSMITH_TEST_DATASET))
        return len(examples) >= 3
    except Exception:
        return False


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
# Raw Provider API Bootstrap Functions
# =============================================================================


def bootstrap_raw_openai_simple() -> None:
    """Create a simple OpenAI trace without tools."""
    import langsmith
    from langsmith.wrappers import wrap_openai
    from openai import OpenAI

    print("  Creating: scout-test-raw-openai-simple-v2")

    # Enable tracing
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    client = wrap_openai(OpenAI())

    # Use trace context to set name and tags
    with langsmith.trace(
        name="scout-test-raw-openai-simple-v2",
        tags=[SCOUT_TEST_TAG, "provider:openai"],
    ):
        client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"},
            ],
        )


def bootstrap_raw_openai_tools() -> None:
    """Create an OpenAI trace with tool calls."""
    import langsmith
    from langsmith.wrappers import wrap_openai
    from openai import OpenAI

    print("  Creating: scout-test-raw-openai-tools-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    client = wrap_openai(OpenAI())

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

    # Use trace context to set name and tags
    with langsmith.trace(
        name="scout-test-raw-openai-tools-v2",
        tags=[SCOUT_TEST_TAG, "provider:openai"],
    ):
        # First call - should request tool use
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
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
            client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=messages,
                tools=OPENAI_TOOLS,
            )


def bootstrap_raw_openai_multiturn() -> None:
    """Create a multi-turn OpenAI conversation trace."""
    import langsmith
    from langsmith.wrappers import wrap_openai
    from openai import OpenAI

    print("  Creating: scout-test-raw-openai-multiturn-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    client = wrap_openai(OpenAI())

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "I'm planning a trip to Japan."},
    ]

    # Use trace context to set name and tags
    with langsmith.trace(
        name="scout-test-raw-openai-multiturn-v2",
        tags=[SCOUT_TEST_TAG, "provider:openai"],
    ):
        # First turn
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=messages,
        )
        messages.append(
            {"role": "assistant", "content": response.choices[0].message.content}
        )

        # Second turn
        messages.append({"role": "user", "content": "What should I see in Tokyo?"})
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=messages,
        )
        messages.append(
            {"role": "assistant", "content": response.choices[0].message.content}
        )

        # Third turn
        messages.append(
            {"role": "user", "content": "What's the best time of year to visit?"}
        )
        client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=messages,
        )


def bootstrap_raw_anthropic_tools() -> None:
    """Create an Anthropic trace with tool calls."""
    import langsmith
    from anthropic import Anthropic
    from langsmith.wrappers import wrap_anthropic

    print("  Creating: scout-test-raw-anthropic-tools-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    client = wrap_anthropic(Anthropic())

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": "What's the weather in Tokyo?",
        }
    ]

    # Use trace context to set name and tags
    with langsmith.trace(
        name="scout-test-raw-anthropic-tools-v2",
        tags=[SCOUT_TEST_TAG, "provider:anthropic"],
    ):
        # First call
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
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
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system="You are a helpful assistant. Use tools when appropriate.",
                messages=messages,
                tools=ANTHROPIC_TOOLS,
            )


def bootstrap_raw_anthropic_multiturn() -> None:
    """Create a multi-turn Anthropic conversation trace (no tools)."""
    import langsmith
    from anthropic import Anthropic
    from langsmith.wrappers import wrap_anthropic

    print("  Creating: scout-test-raw-anthropic-multiturn-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    client = wrap_anthropic(Anthropic())

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "I'm learning to cook Italian food."},
    ]

    # Use trace context to set name and tags
    with langsmith.trace(
        name="scout-test-raw-anthropic-multiturn-v2",
        tags=[SCOUT_TEST_TAG, "provider:anthropic"],
    ):
        # First turn
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful cooking assistant.",
            messages=messages,
        )
        # Extract text content
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
            model="claude-haiku-4-5-20251001",
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
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful cooking assistant.",
            messages=messages,
        )


# =============================================================================
# LangChain Agent Bootstrap Functions
# =============================================================================


def get_weather_tool(city: str) -> str:
    """Get weather for a city (LangChain tool).

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


def bootstrap_langchain_openai_agent() -> None:
    """Create a LangChain agent trace with OpenAI."""
    try:
        from langchain.agents import create_agent
    except ImportError:
        print("  Skipping LangChain OpenAI agent - langchain packages not installed")
        return

    print("  Creating: scout-test-langchain-openai-agent-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        return get_weather_tool(city)

    agent = create_agent(
        model="openai:gpt-5-mini-2025-08-07",
        tools=[get_weather],
        system_prompt="You are a helpful assistant. Use tools when needed.",
    )

    # Run agent with run_name config
    agent.invoke(
        {
            "messages": [
                {"role": "user", "content": "What's the weather in San Francisco?"}
            ]
        },
        config={
            "run_name": "scout-test-langchain-openai-agent-v2",
            "tags": [SCOUT_TEST_TAG, "provider:openai", "type:agent"],
        },
    )


def bootstrap_langchain_anthropic_agent() -> None:
    """Create a LangChain agent trace with Anthropic."""
    try:
        from langchain.agents import create_agent
    except ImportError:
        print("  Skipping LangChain Anthropic agent - langchain packages not installed")
        return

    print("  Creating: scout-test-langchain-anthropic-agent-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        return get_weather_tool(city)

    agent = create_agent(
        model="anthropic:claude-haiku-4-5-20251001",
        tools=[get_weather],
        system_prompt="You are a helpful assistant. Use tools when needed.",
    )

    # Run agent with run_name config
    agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in Tokyo?"}]},
        config={
            "run_name": "scout-test-langchain-anthropic-agent-v2",
            "tags": [SCOUT_TEST_TAG, "provider:anthropic", "type:agent"],
        },
    )


def bootstrap_langchain_google_agent() -> None:
    """Create a LangChain agent trace with Google."""
    try:
        from langchain.agents import create_agent
    except ImportError:
        print("  Skipping LangChain Google agent - langchain packages not installed")
        return

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("  Skipping LangChain Google agent - GOOGLE_API_KEY not set")
        return

    print("  Creating: scout-test-langchain-google-agent-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        return get_weather_tool(city)

    agent = create_agent(
        model="google_genai:gemini-3-flash-preview",
        tools=[get_weather],
        system_prompt="You are a helpful assistant. Use tools when needed.",
    )

    # Run agent with run_name config
    agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in London?"}]},
        config={
            "run_name": "scout-test-langchain-google-agent-v2",
            "tags": [SCOUT_TEST_TAG, "provider:google", "type:agent"],
        },
    )


# =============================================================================
# LangChain Multi-turn Bootstrap Functions (no tools)
# =============================================================================


def bootstrap_langchain_openai_multiturn() -> None:
    """Create a LangChain multi-turn trace with OpenAI (no tools).

    Creates a single trace with multi-turn conversation history.
    Each invoke creates a separate trace, so we pass the full
    conversation history in one call.
    """
    try:
        from langchain.agents import create_agent
    except ImportError:
        print(
            "  Skipping LangChain OpenAI multi-turn - langchain packages not installed"
        )
        return

    print("  Creating: scout-test-langchain-openai-multiturn-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    agent = create_agent(
        model="openai:gpt-5-mini-2025-08-07",
        tools=[],  # No tools - pure conversation
        system_prompt="You are a helpful travel assistant.",
    )

    # Multi-turn conversation with history included
    # Simulates a 3-turn conversation with prior context
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "I'm planning a trip to Paris."},
        {
            "role": "assistant",
            "content": "Paris is a wonderful destination! When are you planning to visit and how long will you stay?",
        },
        {"role": "user", "content": "I'm thinking of going in April for about a week."},
        {
            "role": "assistant",
            "content": "April is a lovely time to visit Paris. The weather is mild and the spring flowers are blooming. A week gives you plenty of time to explore.",
        },
        {"role": "user", "content": "What should I see first?"},
    ]

    # Single invocation with full conversation history
    agent.invoke(
        {"messages": messages},
        config={
            "run_name": "scout-test-langchain-openai-multiturn-v2",
            "tags": [SCOUT_TEST_TAG, "provider:openai", "type:multiturn"],
        },
    )


def bootstrap_langchain_anthropic_multiturn() -> None:
    """Create a LangChain multi-turn trace with Anthropic (no tools).

    Creates a single trace with multi-turn conversation history.
    """
    try:
        from langchain.agents import create_agent
    except ImportError:
        print(
            "  Skipping LangChain Anthropic multi-turn - langchain packages not installed"
        )
        return

    print("  Creating: scout-test-langchain-anthropic-multiturn-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    agent = create_agent(
        model="anthropic:claude-haiku-4-5-20251001",
        tools=[],  # No tools - pure conversation
        system_prompt="You are a helpful cooking assistant.",
    )

    # Multi-turn conversation with history included
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "I want to learn to bake bread."},
        {
            "role": "assistant",
            "content": "Bread baking is a wonderful skill to learn! Let's start with a basic recipe. What type of bread interests you - a simple white loaf, whole wheat, or something else?",
        },
        {"role": "user", "content": "Let's start with a simple white loaf."},
        {
            "role": "assistant",
            "content": "A classic white loaf is a great starting point. You'll need flour, water, yeast, salt, and a bit of sugar. The key is proper kneading and letting the dough rise.",
        },
        {"role": "user", "content": "How long should I let it rise?"},
    ]

    # Single invocation with full conversation history
    agent.invoke(
        {"messages": messages},
        config={
            "run_name": "scout-test-langchain-anthropic-multiturn-v2",
            "tags": [SCOUT_TEST_TAG, "provider:anthropic", "type:multiturn"],
        },
    )


def bootstrap_langchain_google_multiturn() -> None:
    """Create a LangChain multi-turn trace with Google (no tools).

    Creates a single trace with multi-turn conversation history.
    """
    try:
        from langchain.agents import create_agent
    except ImportError:
        print(
            "  Skipping LangChain Google multi-turn - langchain packages not installed"
        )
        return

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("  Skipping LangChain Google multi-turn - GOOGLE_API_KEY not set")
        return

    print("  Creating: scout-test-langchain-google-multiturn-v2")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_TEST_PROJECT

    agent = create_agent(
        model="google_genai:gemini-3-flash-preview",
        tools=[],  # No tools - pure conversation
        system_prompt="You are a helpful fitness coach.",
    )

    # Multi-turn conversation with history included
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "I want to start exercising more."},
        {
            "role": "assistant",
            "content": "That's a great decision! Regular exercise has many benefits. What's your current fitness level and what are your goals?",
        },
        {
            "role": "user",
            "content": "I'm a complete beginner. I just want to get healthier.",
        },
        {
            "role": "assistant",
            "content": "Starting as a beginner is perfect - you can build good habits from the ground up. For general health, a mix of cardio and strength training works well.",
        },
        {"role": "user", "content": "How many times per week should I exercise?"},
    ]

    # Single invocation with full conversation history
    agent.invoke(
        {"messages": messages},
        config={
            "run_name": "scout-test-langchain-google-multiturn-v2",
            "tags": [SCOUT_TEST_TAG, "provider:google", "type:multiturn"],
        },
    )


def bootstrap_langchain_traces() -> None:
    """Bootstrap all LangChain traces (agents and multi-turn)."""
    print("\nBootstrapping LangChain traces...")

    # Agent traces (with tools)
    try:
        bootstrap_langchain_openai_agent()
    except Exception as e:
        print(f"  Failed to create LangChain OpenAI agent: {e}")

    try:
        bootstrap_langchain_anthropic_agent()
    except Exception as e:
        print(f"  Failed to create LangChain Anthropic agent: {e}")

    try:
        bootstrap_langchain_google_agent()
    except Exception as e:
        print(f"  Failed to create LangChain Google agent: {e}")

    # Multi-turn traces (without tools)
    try:
        bootstrap_langchain_openai_multiturn()
    except Exception as e:
        print(f"  Failed to create LangChain OpenAI multi-turn: {e}")

    try:
        bootstrap_langchain_anthropic_multiturn()
    except Exception as e:
        print(f"  Failed to create LangChain Anthropic multi-turn: {e}")

    try:
        bootstrap_langchain_google_multiturn()
    except Exception as e:
        print(f"  Failed to create LangChain Google multi-turn: {e}")

    # Disable tracing after bootstrap
    os.environ.pop("LANGSMITH_TRACING", None)

    print("LangChain bootstrap complete!")


def bootstrap_traces() -> None:
    """Bootstrap all traces (raw provider API and LangChain)."""
    print("\nBootstrapping LangSmith traces...")

    # OpenAI raw traces
    try:
        bootstrap_raw_openai_simple()
    except Exception as e:
        print(f"  Failed to create OpenAI simple trace: {e}")

    try:
        bootstrap_raw_openai_tools()
    except Exception as e:
        print(f"  Failed to create OpenAI tools trace: {e}")

    try:
        bootstrap_raw_openai_multiturn()
    except Exception as e:
        print(f"  Failed to create OpenAI multi-turn trace: {e}")

    # Anthropic raw traces
    try:
        bootstrap_raw_anthropic_tools()
    except Exception as e:
        print(f"  Failed to create Anthropic tools trace: {e}")

    try:
        bootstrap_raw_anthropic_multiturn()
    except Exception as e:
        print(f"  Failed to create Anthropic multi-turn trace: {e}")

    # Note: Raw Google trace removed - google.genai API has no LangSmith wrapper

    # LangChain agent traces (with tools)
    try:
        bootstrap_langchain_openai_agent()
    except Exception as e:
        print(f"  Failed to create LangChain OpenAI agent: {e}")

    try:
        bootstrap_langchain_anthropic_agent()
    except Exception as e:
        print(f"  Failed to create LangChain Anthropic agent: {e}")

    try:
        bootstrap_langchain_google_agent()
    except Exception as e:
        print(f"  Failed to create LangChain Google agent: {e}")

    # LangChain multi-turn traces (without tools)
    try:
        bootstrap_langchain_openai_multiturn()
    except Exception as e:
        print(f"  Failed to create LangChain OpenAI multi-turn: {e}")

    try:
        bootstrap_langchain_anthropic_multiturn()
    except Exception as e:
        print(f"  Failed to create LangChain Anthropic multi-turn: {e}")

    try:
        bootstrap_langchain_google_multiturn()
    except Exception as e:
        print(f"  Failed to create LangChain Google multi-turn: {e}")

    # Disable tracing after bootstrap
    os.environ.pop("LANGSMITH_TRACING", None)

    print("Bootstrap complete!")


# =============================================================================
# Dataset Bootstrap
# =============================================================================


def bootstrap_dataset() -> None:
    """Create a test dataset with sample examples."""
    print("\nBootstrapping LangSmith dataset...")

    client = get_langsmith_client()

    # Check if dataset exists
    try:
        examples = list(client.list_examples(dataset_name=LANGSMITH_TEST_DATASET))
        if len(examples) >= 3:
            print(f"  Dataset {LANGSMITH_TEST_DATASET} already exists with examples")
            return
    except Exception:
        pass

    # Create or get dataset
    try:
        dataset = client.create_dataset(
            LANGSMITH_TEST_DATASET,
            description="Test dataset for inspect-scout LangSmith tests",
        )
    except Exception:
        # Dataset may already exist
        datasets = list(client.list_datasets())
        dataset = next((d for d in datasets if d.name == LANGSMITH_TEST_DATASET), None)
        if not dataset:
            raise ValueError(
                f"Could not create or find dataset {LANGSMITH_TEST_DATASET}"
            ) from None

    # Add examples
    examples_data = [
        {
            "inputs": {"input": "What is the capital of France?"},
            "outputs": {"output": "The capital of France is Paris."},
            "metadata": {"category": "geography", "difficulty": "easy"},
        },
        {
            "inputs": {
                "messages": [
                    {"role": "user", "content": "Explain photosynthesis briefly."}
                ]
            },
            "outputs": {
                "response": "Photosynthesis is the process by which plants convert "
                "sunlight, water, and carbon dioxide into glucose and oxygen."
            },
            "metadata": {"category": "science", "difficulty": "medium"},
        },
        {
            "inputs": {"input": "Write a haiku about programming."},
            "outputs": {
                "output": "Code flows like water\n"
                "Bugs hide in the shadowed depths\n"
                "Debug brings the light"
            },
            "metadata": {"category": "creative", "difficulty": "medium"},
        },
    ]

    for i, example in enumerate(examples_data):
        try:
            client.create_example(
                inputs=example["inputs"],
                outputs=example["outputs"],
                metadata=example.get("metadata"),
                dataset_id=dataset.id,
            )
            print(f"  Created example {i + 1}")
        except Exception as e:
            print(f"  Failed to create example {i + 1}: {e}")

    print("Dataset bootstrap complete!")


# =============================================================================
# Ensure Bootstrap Fixture
# =============================================================================


def ensure_bootstrap() -> None:
    """Ensure test data exists, bootstrapping if needed.

    This function is designed to be called from a pytest fixture
    to ensure test data is available before integration tests run.
    """
    if not is_bootstrap_complete():
        bootstrap_traces()

    if not is_dataset_complete():
        bootstrap_dataset()


def main() -> None:
    """Main entry point for manual bootstrap."""
    print(f"LangSmith Bootstrap for project: {LANGSMITH_TEST_PROJECT}")
    print("=" * 50)

    # Install missing dependencies
    ensure_dependencies()

    # Check current state
    print("\nChecking current state...")
    traces_complete = is_bootstrap_complete()
    dataset_complete = is_dataset_complete()

    print(f"  Traces complete: {traces_complete}")
    print(f"  Dataset complete: {dataset_complete}")

    if traces_complete and dataset_complete:
        print("\nBootstrap already complete!")
        return

    # Run bootstrap
    if not traces_complete:
        bootstrap_traces()

    if not dataset_complete:
        bootstrap_dataset()

    print("\n" + "=" * 50)
    print("Bootstrap complete!")
    print(
        f"Project URL: https://smith.langchain.com/o/default/projects/p/{LANGSMITH_TEST_PROJECT}"
    )


if __name__ == "__main__":
    main()
