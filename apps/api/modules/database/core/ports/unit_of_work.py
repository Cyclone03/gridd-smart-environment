from contextlib import AbstractContextManager
from typing import Protocol


class UnitOfWork(Protocol):
    """Transaction : tout ce qui est écrit dans ``atomic()`` est validé ou annulé ensemble."""

    def atomic(self) -> AbstractContextManager: ...
