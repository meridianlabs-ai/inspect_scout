from collections.abc import Iterator

import pytest
from inspect_scout._jev_scanner._provider import JevRequest

from .fake_jev import REQUESTS


@pytest.fixture
def jev_requests() -> Iterator[list[JevRequest]]:
    """Requests the fake Jev provider receives during the test."""
    REQUESTS.clear()
    yield REQUESTS
    REQUESTS.clear()
