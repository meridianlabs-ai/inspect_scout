from typing import Any

from rich.console import RenderableType
from typing_extensions import override

from .._recorder.recorder import Status
from .protocol import Display


class DisplayNone(Display):
    @override
    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        markup: bool | None = None,
        highlight: bool | None = None,
    ) -> None:
        pass

    @override
    def scan_interrupted(self, message: RenderableType, status: Status) -> None:
        pass

    @override
    def scan_complete(self, status: Status) -> None:
        pass
