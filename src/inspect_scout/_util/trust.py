"""Combining content-trust settings."""


def lowest_trust_content(*settings: bool | None) -> bool | None:
    """The combined `trust_content` of several settings: `False` if any is `False`.

    `None` and `True` both mean "trusted unless something else says otherwise",
    so no setting can raise trust that another has lowered.
    """
    return False if any(setting is False for setting in settings) else None
