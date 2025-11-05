from collections.abc import Iterator
from typing import Any

from jinja2 import Undefined


class StrictOnUseUndefined(Undefined):
    """Raises an error only when the undefined value is actually used/output.

    This allows Jinja2 templates to use {% for %}/{% else %} and {% if %}/{% else %}
    to handle missing attributes gracefully, while still catching undefined variables
    that are actually rendered.
    """

    def __str__(self) -> str:
        """Raise error when trying to convert to string (i.e., output it)."""
        raise self._undefined_exception(f"{self._undefined_name} is undefined")

    def __iter__(self) -> Iterator[Any]:
        """Return empty iterator instead of raising - allows {% for %}/{% else %}."""
        return iter([])

    def __bool__(self) -> bool:
        """Return False for conditionals - allows {% if %}/{% else %}."""
        return False
