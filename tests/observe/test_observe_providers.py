"""End-to-end tests for observe() with OpenAI, Anthropic, and Google providers."""

import tempfile
from typing import Any, cast

import pytest
from inspect_scout._observe import observe
from inspect_scout._transcript.database.factory import transcripts_db
from inspect_scout._transcript.types import TranscriptContent

from tests.conftest import skip_if_no_anthropic, skip_if_no_google, skip_if_no_openai

# =============================================================================
# OpenAI Provider Tests (11 tests)
# =============================================================================


class TestOpenAIProvider:
    """Tests for OpenAI SDK capture."""

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_completions_sync(self) -> None:
        """OpenAI Chat Completions API - sync, non-streaming."""
        from openai import OpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="completions_sync",
            ):
                client = OpenAI()
                response = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": "Say hello"}],
                    max_completion_tokens=10,
                )
                assert response.choices[0].message.content is not None

            # Verify transcript was written
            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                t = transcripts[0]
                assert t.task_set == "openai_test"
                assert t.task_id == "completions_sync"
                assert t.model == "gpt-5-mini"

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(t, content)
                assert len(full.messages) >= 2
                assert len(full.events) >= 1

                # Verify model event
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                assert model_events[0].output is not None
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_completions_async(self) -> None:
        """OpenAI Chat Completions API - async, non-streaming."""
        from openai import AsyncOpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="completions_async",
            ):
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": "Say hello"}],
                    max_completion_tokens=10,
                )
                assert response.choices[0].message.content is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                assert len(full.messages) >= 2
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_completions_sync_streaming(self) -> None:
        """OpenAI Chat Completions API - sync, streaming."""
        from openai import OpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="completions_sync_stream",
            ):
                client = OpenAI()
                stream = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": "Say hello"}],
                    max_completion_tokens=10,
                    stream=True,
                )
                chunks = []
                for chunk in stream:
                    chunks.append(chunk)
                assert len(chunks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Verify content was accumulated from stream
                assert model_events[0].output is not None
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_completions_async_streaming(self) -> None:
        """OpenAI Chat Completions API - async, streaming."""
        from openai import AsyncOpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="completions_async_stream",
            ):
                client = AsyncOpenAI()
                stream = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": "Say hello"}],
                    max_completion_tokens=10,
                    stream=True,
                )
                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)
                assert len(chunks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                assert model_events[0].output is not None
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_completions_tool_use(self) -> None:
        """OpenAI Chat Completions API with tool use."""
        from openai import AsyncOpenAI

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="completions_tool_use",
            ):
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "user", "content": "What's the weather in Paris?"}
                    ],
                    tools=cast(Any, tools),
                    tool_choice="required",
                    max_completion_tokens=200,
                )
                assert response.choices[0].message.tool_calls is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Verify tools were captured
                assert len(model_events[0].tools) > 0
                # Verify tool calls in output
                assert model_events[0].output.choices[0].message.tool_calls is not None
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_completions_tool_use_streaming(self) -> None:
        """OpenAI Chat Completions API with tool use - streaming."""
        from openai import AsyncOpenAI

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="completions_tool_stream",
            ):
                client = AsyncOpenAI()
                stream = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "user", "content": "What's the weather in Paris?"}
                    ],
                    tools=cast(Any, tools),
                    tool_choice="required",
                    max_completion_tokens=200,
                    stream=True,
                )
                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)
                assert len(chunks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Tool calls should be accumulated from stream
                assert model_events[0].output.choices[0].message.tool_calls is not None
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_responses_sync(self) -> None:
        """OpenAI Responses API - sync, non-streaming."""
        from openai import OpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="responses_sync",
            ):
                client = OpenAI()
                response = client.responses.create(
                    model="gpt-5-mini",
                    input="Say hello",
                    max_output_tokens=50,
                )
                assert response.output is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_responses_async(self) -> None:
        """OpenAI Responses API - async, non-streaming."""
        from openai import AsyncOpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="responses_async",
            ):
                client = AsyncOpenAI()
                response = await client.responses.create(
                    model="gpt-5-mini",
                    input="Say hello",
                    max_output_tokens=50,
                )
                assert response.output is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_responses_sync_streaming(self) -> None:
        """OpenAI Responses API - sync, streaming."""
        from openai import OpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="responses_sync_stream",
            ):
                client = OpenAI()
                stream = client.responses.create(
                    model="gpt-5-mini-2025-08-07",
                    input="Say hello",
                    max_output_tokens=500,
                    stream=True,
                )
                events = []
                for event in stream:
                    events.append(event)
                assert len(events) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_responses_async_streaming(self) -> None:
        """OpenAI Responses API - async, streaming."""
        from openai import AsyncOpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="responses_async_stream",
            ):
                client = AsyncOpenAI()
                stream = await client.responses.create(
                    model="gpt-5-mini-2025-08-07",
                    input="Say hello",
                    max_output_tokens=500,
                    stream=True,
                )
                events = []
                async for event in stream:
                    events.append(event)
                assert len(events) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_responses_tool_use(self) -> None:
        """OpenAI Responses API with tool use."""
        from openai import AsyncOpenAI

        tools = [
            {
                "type": "function",
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="responses_tool_use",
            ):
                client = AsyncOpenAI()
                response = await client.responses.create(
                    model="gpt-5-mini",
                    input="What's the weather in Paris?",
                    tools=cast(Any, tools),
                    tool_choice="required",
                    max_output_tokens=500,
                )
                # Responses API returns tool calls in output
                assert response.output is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                assert len(model_events[0].tools) > 0
            finally:
                await db.disconnect()

    @skip_if_no_openai
    @pytest.mark.asyncio
    async def test_openai_multi_turn(self) -> None:
        """OpenAI Chat Completions API - multi-turn conversation."""
        from openai import AsyncOpenAI

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="openai",
                task_set="openai_test",
                task_id="multi_turn",
            ):
                client = AsyncOpenAI()
                messages: list[dict[str, str]] = [
                    {"role": "user", "content": "My name is Alice."}
                ]

                # First turn
                response1 = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=cast(Any, messages),
                    max_completion_tokens=50,
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": response1.choices[0].message.content or "",
                    }
                )

                # Second turn
                messages.append({"role": "user", "content": "What is my name?"})
                response2 = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=cast(Any, messages),
                    max_completion_tokens=50,
                )
                assert "Alice" in (response2.choices[0].message.content or "")

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                # Should have multiple model events (one per turn)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 2
                # Should have messages captured
                assert len(full.messages) >= 4  # 2 user + 2 assistant
            finally:
                await db.disconnect()


# =============================================================================
# Anthropic Provider Tests (11 tests)
# =============================================================================


class TestAnthropicProvider:
    """Tests for Anthropic SDK capture."""

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_sync(self) -> None:
        """Anthropic Messages API - sync, non-streaming."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="sync",
            ):
                client = anthropic.Anthropic()
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Say hello"}],
                )
                block = response.content[0]
                assert block.type == "text" and block.text is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                t = transcripts[0]

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(t, content)
                assert len(full.messages) >= 2
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Verify model was captured in event
                assert "claude-haiku-4-5" in model_events[0].model
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_async(self) -> None:
        """Anthropic Messages API - async, non-streaming."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="async",
            ):
                client = anthropic.AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Say hello"}],
                )
                block = response.content[0]
                assert block.type == "text" and block.text is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_sync_streaming(self) -> None:
        """Anthropic Messages API - sync, streaming with stream=True."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="sync_stream",
            ):
                client = anthropic.Anthropic()
                stream = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Say hello"}],
                    stream=True,
                )
                events = []
                for event in stream:
                    events.append(event)
                assert len(events) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                assert model_events[0].output is not None
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_async_streaming(self) -> None:
        """Anthropic Messages API - async, streaming with stream=True."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="async_stream",
            ):
                client = anthropic.AsyncAnthropic()
                stream = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Say hello"}],
                    stream=True,
                )
                events = []
                async for event in stream:
                    events.append(event)
                assert len(events) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_stream_manager(self) -> None:
        """Anthropic Messages API - async stream manager (.stream())."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="stream_manager",
            ):
                client = anthropic.AsyncAnthropic()
                async with client.messages.stream(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Say hello"}],
                ) as stream:
                    message = await stream.get_final_message()
                    block = message.content[0]
                    assert block.type == "text" and block.text is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_tool_use(self) -> None:
        """Anthropic Messages API with tool use."""
        import anthropic

        tools = [
            {
                "name": "get_weather",
                "description": "Get weather for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="tool_use",
            ):
                client = anthropic.AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=100,
                    messages=[
                        {"role": "user", "content": "What's the weather in Paris?"}
                    ],
                    tools=cast(Any, tools),
                    tool_choice={"type": "tool", "name": "get_weather"},
                )
                # Find tool_use block in response
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
                assert len(tool_use_blocks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                assert len(model_events[0].tools) > 0
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_tool_use_streaming(self) -> None:
        """Anthropic Messages API with tool use - streaming."""
        import anthropic

        tools = [
            {
                "name": "get_weather",
                "description": "Get weather for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="tool_use_stream",
            ):
                client = anthropic.AsyncAnthropic()
                stream = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=100,
                    messages=[
                        {"role": "user", "content": "What's the weather in Paris?"}
                    ],
                    tools=cast(Any, tools),
                    tool_choice={"type": "tool", "name": "get_weather"},
                    stream=True,
                )
                events = []
                async for event in stream:
                    events.append(event)
                assert len(events) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Verify tools were captured
                assert len(model_events[0].tools) > 0
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_thinking(self) -> None:
        """Anthropic Messages API with extended thinking."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="thinking",
            ):
                client = anthropic.AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    thinking={"type": "enabled", "budget_tokens": 1024},
                    messages=[{"role": "user", "content": "What is 2+2?"}],
                )
                # Verify thinking block in response
                thinking_blocks = [b for b in response.content if b.type == "thinking"]
                assert len(thinking_blocks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Verify output was captured
                assert model_events[0].output is not None
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_thinking_streaming(self) -> None:
        """Anthropic Messages API with extended thinking - streaming."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="thinking_stream",
            ):
                client = anthropic.AsyncAnthropic()
                stream = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    thinking={"type": "enabled", "budget_tokens": 1024},
                    messages=[{"role": "user", "content": "What is 2+2?"}],
                    stream=True,
                )
                events = []
                async for event in stream:
                    events.append(event)
                assert len(events) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Verify output was captured
                assert model_events[0].output is not None
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_web_search(self) -> None:
        """Anthropic Messages API with web search server tool."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="web_search",
            ):
                client = anthropic.AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    messages=[
                        {
                            "role": "user",
                            "content": "What is the current weather in Tokyo?",
                        }
                    ],
                    tools=[{"type": "web_search_20250305", "name": "web_search"}],
                )
                assert response.content is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Verify output was captured
                assert model_events[0].output is not None
            finally:
                await db.disconnect()

    @skip_if_no_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_multi_turn(self) -> None:
        """Anthropic Messages API - multi-turn conversation."""
        import anthropic

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="anthropic",
                task_set="anthropic_test",
                task_id="multi_turn",
            ):
                client = anthropic.AsyncAnthropic()
                messages: list[dict[str, str]] = [
                    {"role": "user", "content": "My name is Bob."}
                ]

                # First turn
                response1 = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=50,
                    messages=cast(Any, messages),
                )
                block1 = response1.content[0]
                assert block1.type == "text"
                messages.append({"role": "assistant", "content": block1.text})

                # Second turn
                messages.append({"role": "user", "content": "What is my name?"})
                response2 = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=50,
                    messages=cast(Any, messages),
                )
                block2 = response2.content[0]
                assert block2.type == "text" and "Bob" in block2.text

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                # Should have multiple model events (one per turn)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 2
                # Should have messages captured
                assert len(full.messages) >= 4  # 2 user + 2 assistant
            finally:
                await db.disconnect()


# =============================================================================
# Google Provider Tests (9 tests)
# =============================================================================


class TestGoogleProvider:
    """Tests for Google GenAI SDK capture."""

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_sync(self) -> None:
        """Google GenAI - sync, non-streaming."""
        from google import genai

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="sync",
            ):
                client = genai.Client()
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents="Say hello",
                    config={"max_output_tokens": 10},
                )
                assert response.text is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                t = transcripts[0]
                assert t.model is not None and "gemini" in t.model.lower()

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(t, content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_async(self) -> None:
        """Google GenAI - async, non-streaming."""
        from google import genai

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="async",
            ):
                client = genai.Client()
                response = await client.aio.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents="Say hello",
                    config={"max_output_tokens": 10},
                )
                assert response.text is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_sync_streaming(self) -> None:
        """Google GenAI - sync, streaming."""
        from google import genai

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="sync_stream",
            ):
                client = genai.Client()
                stream = client.models.generate_content_stream(
                    model="gemini-3-flash-preview",
                    contents="Say hello",
                    config={"max_output_tokens": 10},
                )
                chunks = []
                for chunk in stream:
                    chunks.append(chunk)
                assert len(chunks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_async_streaming(self) -> None:
        """Google GenAI - async, streaming."""
        from google import genai

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="async_stream",
            ):
                client = genai.Client()
                stream = await client.aio.models.generate_content_stream(
                    model="gemini-3-flash-preview",
                    contents="Say hello",
                    config={"max_output_tokens": 10},
                )
                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)
                assert len(chunks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_tool_use(self) -> None:
        """Google GenAI with tool use."""
        from google import genai
        from google.genai.types import FunctionDeclaration, Tool

        get_weather = FunctionDeclaration(
            name="get_weather",
            description="Get weather for a location",
            parameters=cast(
                Any,
                {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            ),
        )
        tools = [Tool(function_declarations=[get_weather])]

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="tool_use",
            ):
                client = genai.Client()
                response = await client.aio.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents="What's the weather in Paris?",
                    config=cast(
                        Any,
                        {
                            "tools": tools,
                            "tool_config": {"function_calling_config": {"mode": "ANY"}},
                            "max_output_tokens": 100,
                        },
                    ),
                )
                # Check for function call in response
                has_function_call = any(
                    hasattr(part, "function_call") and part.function_call
                    for candidate in (response.candidates or [])
                    for part in (candidate.content.parts or [])  # type: ignore[union-attr]
                    if candidate.content
                )
                assert has_function_call

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
                # Verify output was captured
                assert model_events[0].output is not None
            finally:
                await db.disconnect()

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_tool_use_streaming(self) -> None:
        """Google GenAI with tool use - streaming."""
        from google import genai
        from google.genai.types import FunctionDeclaration, Tool

        get_weather = FunctionDeclaration(
            name="get_weather",
            description="Get weather for a location",
            parameters=cast(
                Any,
                {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            ),
        )
        tools = [Tool(function_declarations=[get_weather])]

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="tool_use_stream",
            ):
                client = genai.Client()
                stream = await client.aio.models.generate_content_stream(
                    model="gemini-3-flash-preview",
                    contents="What's the weather in Paris?",
                    config=cast(
                        Any,
                        {
                            "tools": tools,
                            "tool_config": {"function_calling_config": {"mode": "ANY"}},
                            "max_output_tokens": 100,
                        },
                    ),
                )
                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)
                assert len(chunks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_thinking(self) -> None:
        """Google GenAI with thinking (reasoning)."""
        from google import genai

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="thinking",
            ):
                client = genai.Client()
                response = await client.aio.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents="What is 2+2?",
                    config={
                        "max_output_tokens": 1000,
                        "thinking_config": {"thinking_budget": 500},
                    },
                )
                assert response.text is not None

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_thinking_streaming(self) -> None:
        """Google GenAI with thinking (reasoning) - streaming."""
        from google import genai

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="thinking_stream",
            ):
                client = genai.Client()
                stream = await client.aio.models.generate_content_stream(
                    model="gemini-3-flash-preview",
                    contents="What is 2+2?",
                    config={
                        "max_output_tokens": 1000,
                        "thinking_config": {"thinking_budget": 500},
                    },
                )
                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)
                assert len(chunks) > 0

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 1
            finally:
                await db.disconnect()

    @skip_if_no_google
    @pytest.mark.asyncio
    async def test_google_multi_turn(self) -> None:
        """Google GenAI - multi-turn conversation."""
        from google import genai
        from google.genai.types import Content, Part

        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(
                db=db,
                provider="google",
                task_set="google_test",
                task_id="multi_turn",
            ):
                client = genai.Client()

                # First turn
                response1 = await client.aio.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents="My name is Carol.",
                    config={"max_output_tokens": 50},
                )

                # Build multi-turn history
                history = [
                    Content(role="user", parts=[Part(text="My name is Carol.")]),
                    Content(role="model", parts=[Part(text=response1.text or "")]),
                    Content(role="user", parts=[Part(text="What is my name?")]),
                ]

                # Second turn
                response2 = await client.aio.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=history,  # type: ignore[arg-type]
                    config={"max_output_tokens": 50},
                )
                assert "Carol" in (response2.text or "")

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                # Should have multiple model events (one per turn)
                model_events = [e for e in full.events if e.event == "model"]
                assert len(model_events) >= 2
            finally:
                await db.disconnect()
