"""Type stubs for concurrent module."""

from typing import Any, Awaitable, Callable, TypeVar

from stolas.types.effect import Effect

T = TypeVar("T")
U = TypeVar("U")

def concurrent(
    *funcs: Callable[[T], Awaitable[Any]],
) -> Callable[[T], Effect[Awaitable[tuple[Any, ...]]]]:
    """Run multiple async functions in parallel on the same input."""
    ...
