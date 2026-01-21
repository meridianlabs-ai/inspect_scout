from datetime import datetime, timezone

_version: str = datetime.now(timezone.utc).isoformat()


def get_config_version() -> str:
    return _version


def bump_config_version() -> None:
    global _version
    _version = datetime.now(timezone.utc).isoformat()
