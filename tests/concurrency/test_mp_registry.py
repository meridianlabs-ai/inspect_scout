"""Tests for cross-process semaphore registry behavior."""

import logging
import multiprocessing
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from inspect_ai.util import AdaptiveConcurrency
from inspect_scout._concurrency._mp_registry import ParentSemaphoreRegistry

REGISTRY_LOGGER = "inspect_scout._concurrency._mp_registry"


@pytest_asyncio.fixture
async def parent_registry() -> AsyncIterator[ParentSemaphoreRegistry]:
    manager = multiprocessing.get_context("spawn").Manager()
    try:
        yield ParentSemaphoreRegistry(manager)
    finally:
        manager.shutdown()


@pytest.mark.asyncio
async def test_get_or_create_warns_on_unsupported_resizable(
    parent_registry: ParentSemaphoreRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger=REGISTRY_LOGGER):
        sem = await parent_registry.get_or_create(
            "resizable-sem", 2, None, True, resizable=True
        )
        # cached retrieval must not warn again
        await parent_registry.get_or_create(
            "resizable-sem", 2, None, True, resizable=True
        )

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "resizable" in warnings[0].getMessage()
    # degrades to a working fixed-limit semaphore
    assert sem.concurrency == 2


@pytest.mark.asyncio
async def test_get_or_create_warns_on_unsupported_adaptive(
    parent_registry: ParentSemaphoreRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger=REGISTRY_LOGGER):
        sem = await parent_registry.get_or_create(
            "adaptive-sem", 2, None, True, adaptive=AdaptiveConcurrency()
        )

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "adaptive" in warnings[0].getMessage()
    assert sem.concurrency == 2


@pytest.mark.asyncio
async def test_get_or_create_no_warning_for_fixed_semaphore(
    parent_registry: ParentSemaphoreRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger=REGISTRY_LOGGER):
        await parent_registry.get_or_create("fixed-sem", 2, None, True)

    assert not [r for r in caplog.records if r.levelno == logging.WARNING]
