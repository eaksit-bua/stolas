"""Control combinators for effectful flow: bracket, retry, and timeout.

These helpers wrap :class:`~stolas.types.effect.Effect` and
:class:`~stolas.types.effect.AsyncEffect` rather than retrofitting them. They
follow the framework's errors-as-values stance: ``attempt``/``retry`` catch
``Exception`` only, so ``KeyboardInterrupt``, ``SystemExit`` and
``asyncio.CancelledError`` always propagate. ``timeout`` is async-only by
design (decision D8).
"""

import asyncio
import time
from typing import Any, Awaitable, Callable, TypeVar

from stolas.types.effect import AsyncEffect, Effect
from stolas.types.result import Error

__all__ = [
    "bracket",
    "bracket_async",
    "RetryPolicy",
    "retry",
    "retry_async",
    "timeout",
]

T = TypeVar("T")
R = TypeVar("R")


def bracket(
    acquire: Callable[[], R],
    use: Callable[[R], T],
    release: Callable[[R], Any],
) -> T:
    """Acquire a resource, ``use`` it, and ALWAYS ``release`` it.

    ``release(resource)`` runs in a ``finally`` block, so it executes even when
    ``use`` raises -- mirroring a ``with`` statement. The result of ``use`` is
    returned; an exception from ``use`` propagates after release.
    """
    resource = acquire()
    try:
        return use(resource)
    finally:
        release(resource)


async def bracket_async(
    acquire: Callable[[], Awaitable[R]],
    use: Callable[[R], Awaitable[T]],
    release: Callable[[R], Awaitable[Any]],
) -> T:
    """Async analogue of :func:`bracket` with awaitable acquire/use/release.

    ``release(resource)`` is awaited in a ``finally`` block, so it runs even if
    ``use`` raises (including on cancellation).
    """
    resource = await acquire()
    try:
        return await use(resource)
    finally:
        await release(resource)


class RetryPolicy:
    """Immutable configuration for :func:`retry` / :func:`retry_async`.

    ``attempts`` is the total number of tries (>= 1). ``delay`` is the initial
    pause in seconds before a re-run; ``backoff`` multiplies the delay after
    each failed attempt. When ``retry_on_error`` is ``True``, an ``Error``
    (``Result``) value returned by the effect is treated as a failure and
    triggers a retry (the error-as-value idiom), in addition to raised
    exceptions.
    """

    __slots__ = ("_attempts", "_delay", "_backoff", "_retry_on_error")
    __match_args__ = ("attempts", "delay", "backoff", "retry_on_error")
    _attempts: int
    _delay: float
    _backoff: float
    _retry_on_error: bool

    def __init__(
        self,
        attempts: int,
        delay: float = 0.0,
        backoff: float = 1.0,
        retry_on_error: bool = False,
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts must be >= 1")
        object.__setattr__(self, "_attempts", attempts)
        object.__setattr__(self, "_delay", delay)
        object.__setattr__(self, "_backoff", backoff)
        object.__setattr__(self, "_retry_on_error", retry_on_error)

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def delay(self) -> float:
        return self._delay

    @property
    def backoff(self) -> float:
        return self._backoff

    @property
    def retry_on_error(self) -> bool:
        return self._retry_on_error

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("RetryPolicy is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("RetryPolicy is immutable")

    def __repr__(self) -> str:
        return (
            f"RetryPolicy(attempts={self._attempts!r}, delay={self._delay!r}, "
            f"backoff={self._backoff!r}, retry_on_error={self._retry_on_error!r})"
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, RetryPolicy):
            return NotImplemented
        return (
            self._attempts == other._attempts
            and self._delay == other._delay
            and self._backoff == other._backoff
            and self._retry_on_error == other._retry_on_error
        )

    def __hash__(self) -> int:
        return hash((self._attempts, self._delay, self._backoff, self._retry_on_error))


def retry(policy: RetryPolicy, effect: Effect[T]) -> Effect[T]:
    """Wrap ``effect`` so its ``.run()`` re-runs on failure per ``policy``.

    A failure is a raised ``Exception`` (``BaseException`` propagates). When
    ``policy.retry_on_error`` is ``True``, an ``Error`` value returned by the
    effect is also a failure. After exhausting ``policy.attempts``, the last
    exception is re-raised (or the last ``Error`` value returned).
    """

    def runner() -> T:
        delay = policy.delay
        last_exc: Exception | None = None
        for index in range(policy.attempts):
            last_exc = None
            try:
                value = effect.run()
            except Exception as exc:
                last_exc = exc
            else:
                if not (policy.retry_on_error and isinstance(value, Error)):
                    return value
            if index + 1 >= policy.attempts:
                break
            time.sleep(delay)
            delay *= policy.backoff
        if last_exc is not None:
            raise last_exc
        return value

    return Effect(runner)


def retry_async(policy: RetryPolicy, effect: AsyncEffect[T]) -> AsyncEffect[T]:
    """Async analogue of :func:`retry` for an :class:`AsyncEffect`.

    Delays use :func:`asyncio.sleep`; ``asyncio.CancelledError`` (a
    ``BaseException``) is never caught and so always propagates.
    """

    async def runner() -> T:
        delay = policy.delay
        last_exc: Exception | None = None
        for index in range(policy.attempts):
            last_exc = None
            try:
                value = await effect.run()
            except Exception as exc:
                last_exc = exc
            else:
                if not (policy.retry_on_error and isinstance(value, Error)):
                    return value
            if index + 1 >= policy.attempts:
                break
            await asyncio.sleep(delay)
            delay *= policy.backoff
        if last_exc is not None:
            raise last_exc
        return value

    return AsyncEffect(runner)


def timeout(seconds: float, ae: AsyncEffect[T]) -> AsyncEffect[T]:
    """Wrap ``ae`` so its ``.run()`` raises ``TimeoutError`` past ``seconds``.

    Async-only by design (decision D8): there is deliberately no synchronous
    ``timeout``. Cancellation of the inner awaitable is driven by
    :func:`asyncio.wait_for`.
    """

    async def runner() -> T:
        return await asyncio.wait_for(ae.run(), seconds)

    return AsyncEffect(runner)
