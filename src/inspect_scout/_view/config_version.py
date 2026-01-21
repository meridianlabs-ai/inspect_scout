from datetime import datetime, timezone

import anyio

_version: str = datetime.now(timezone.utc).isoformat()
_condition: anyio.Condition | None = None


def get_config_version() -> str:
    return _version


def get_condition() -> anyio.Condition:
    global _condition
    if _condition is None:
        _condition = anyio.Condition()
    return _condition


async def bump_config_version() -> None:
    global _version
    _version = datetime.now(timezone.utc).isoformat()
    async with get_condition():
        get_condition().notify_all()
