"""Type stubs for the control module."""

from typing import Any, Awaitable, Callable, TypeVar

from stolas.types.effect import AsyncEffect, Effect

T = TypeVar("T")
R = TypeVar("R")

__all__ = [
    "bracket",
    "bracket_async",
    "RetryPolicy",
    "retry",
    "retry_async",
    "timeout",
]

def bracket(
    acquire: Callable[[], R],
    use: Callable[[R], T],
    release: Callable[[R], Any],
) -> T: ...
async def bracket_async(
    acquire: Callable[[], Awaitable[R]],
    use: Callable[[R], Awaitable[T]],
    release: Callable[[R], Awaitable[Any]],
) -> T: ...

class RetryPolicy:
    __match_args__: tuple[str, ...]

    def __init__(
        self,
        attempts: int,
        delay: float = ...,
        backoff: float = ...,
        retry_on_error: bool = ...,
    ) -> None: ...
    @property
    def attempts(self) -> int: ...
    @property
    def delay(self) -> float: ...
    @property
    def backoff(self) -> float: ...
    @property
    def retry_on_error(self) -> bool: ...
    def __eq__(self, other: Any) -> bool: ...
    def __hash__(self) -> int: ...

def retry(policy: RetryPolicy, effect: Effect[T]) -> Effect[T]: ...
def retry_async(policy: RetryPolicy, effect: AsyncEffect[T]) -> AsyncEffect[T]: ...
def timeout(seconds: float, ae: AsyncEffect[T]) -> AsyncEffect[T]: ...
