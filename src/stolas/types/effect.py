"""Effect[T] and AsyncEffect[T]: lazy evaluation monads for deferred side effects.

``Effect`` wraps a synchronous thunk; ``AsyncEffect`` is a *sibling* class
(no shared interpreter) wrapping a factory that produces a fresh awaitable on
every run, so native ``async``/``await`` drives execution. Bridges connect the
two: ``Effect.to_async``/``from_effect`` lift a sync effect into the async
world, and ``to_effect`` runs an ``AsyncEffect`` to completion via
``asyncio.run``.
"""

import asyncio
from typing import Any, Awaitable, Callable, Generic, TypeVar

from stolas.types.result import Error, Ok, Result

T = TypeVar("T")
U = TypeVar("U")


class Effect(Generic[T]):
    """Wraps a callable for lazy evaluation."""

    __slots__ = ("_thunk",)
    __match_args__ = ("thunk",)
    _thunk: Callable[[], T]

    def __init__(self, thunk: Callable[[], T]) -> None:
        object.__setattr__(self, "_thunk", thunk)

    @property
    def thunk(self) -> Callable[[], T]:
        return self._thunk

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Effect is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Effect is immutable")

    def __repr__(self) -> str:
        return "Effect(<thunk>)"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Effect):
            return NotImplemented
        return self._thunk is other._thunk

    def __hash__(self) -> int:
        return hash(id(self._thunk))

    def __rshift__(self, func: Callable[[T], U]) -> "Effect[U]":
        """Compose without executing."""

        def composed() -> U:
            result = self._thunk()
            if isinstance(result, Effect):
                return func(result.run())
            return func(result)

        return Effect(composed)

    def map(self, func: Callable[[T], U]) -> "Effect[U]":
        """Transform the eventual result T -> U."""

        def mapped() -> U:
            return func(self._thunk())

        return Effect(mapped)

    def bind(self, func: Callable[[T], "Effect[U]"]) -> "Effect[U]":
        """Transform T -> Effect[U], flattening the result."""

        def bound() -> U:
            return func(self._thunk()).run()

        return Effect(bound)

    def run(self) -> T:
        """Execute the effect and return the result."""
        return self._thunk()

    def as_result(self) -> "Effect[Result[T, Exception]]":
        """Wrap this effect so ``.run()`` yields ``Ok``/``Error`` (errors-as-values).

        Running the returned effect executes ``self``'s thunk; a returned value
        becomes ``Ok(value)`` and a raised ``Exception`` becomes ``Error(exc)``.
        ``BaseException`` (e.g. ``KeyboardInterrupt``) is allowed to propagate.
        """

        def attempted() -> Result[T, Exception]:
            try:
                return Ok(self._thunk())
            except Exception as exc:
                return Error(exc)

        return Effect(attempted)

    def to_async(self) -> "AsyncEffect[T]":
        """Lift this synchronous effect into an :class:`AsyncEffect`."""

        async def factory() -> T:
            return self._thunk()

        return AsyncEffect(factory)

    @staticmethod
    def pure(value: T) -> "Effect[T]":
        """Wrap a pure value in an Effect."""
        return Effect(lambda: value)

    @staticmethod
    def defer(func: Callable[..., T], *args: Any, **kwargs: Any) -> "Effect[T]":
        """Create an Effect from a function and its arguments."""
        return Effect(lambda: func(*args, **kwargs))

    @staticmethod
    def attempt(thunk: Callable[[], T]) -> "Effect[Result[T, Exception]]":
        """Create an effect that runs ``thunk`` capturing failure as a value.

        ``.run()`` returns ``Ok(thunk())`` on success or ``Error(exc)`` when
        ``thunk`` raises an ``Exception``. ``BaseException`` propagates.
        """
        return Effect(thunk).as_result()


class AsyncEffect(Generic[T]):
    """Wraps a factory producing a fresh awaitable for lazy async evaluation."""

    __slots__ = ("_factory",)
    __match_args__ = ("factory",)
    _factory: Callable[[], Awaitable[T]]

    def __init__(self, factory: Callable[[], Awaitable[T]]) -> None:
        object.__setattr__(self, "_factory", factory)

    @property
    def factory(self) -> Callable[[], Awaitable[T]]:
        return self._factory

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("AsyncEffect is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("AsyncEffect is immutable")

    def __repr__(self) -> str:
        return "AsyncEffect(<factory>)"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, AsyncEffect):
            return NotImplemented
        return self._factory is other._factory

    def __hash__(self) -> int:
        return hash(id(self._factory))

    def __rshift__(self, func: Callable[[T], U]) -> "AsyncEffect[U]":
        """Compose without executing."""

        async def composed() -> U:
            return func(await self._factory())

        return AsyncEffect(composed)

    def map(self, func: Callable[[T], U]) -> "AsyncEffect[U]":
        """Transform the eventual result T -> U."""

        async def mapped() -> U:
            return func(await self._factory())

        return AsyncEffect(mapped)

    def bind(self, func: Callable[[T], "AsyncEffect[U]"]) -> "AsyncEffect[U]":
        """Transform T -> AsyncEffect[U], flattening the result."""

        async def bound() -> U:
            return await func(await self._factory()).run()

        return AsyncEffect(bound)

    async def run(self) -> T:
        """Await a fresh awaitable from the factory and return the result."""
        return await self._factory()

    def as_result(self) -> "AsyncEffect[Result[T, Exception]]":
        """Wrap this effect so ``.run()`` yields ``Ok``/``Error`` (errors-as-values).

        A returned value becomes ``Ok(value)`` and a raised ``Exception``
        becomes ``Error(exc)``. ``BaseException`` -- notably
        ``asyncio.CancelledError`` -- is allowed to propagate.
        """

        async def attempted() -> Result[T, Exception]:
            try:
                return Ok(await self._factory())
            except Exception as exc:
                return Error(exc)

        return AsyncEffect(attempted)

    @staticmethod
    def pure(value: T) -> "AsyncEffect[T]":
        """Wrap a pure value in an AsyncEffect."""

        async def factory() -> T:
            return value

        return AsyncEffect(factory)

    @staticmethod
    def defer(
        coro_fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> "AsyncEffect[T]":
        """Create an AsyncEffect from a coroutine function and its arguments."""
        return AsyncEffect(lambda: coro_fn(*args, **kwargs))

    @staticmethod
    def attempt(
        coro_fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> "AsyncEffect[Result[T, Exception]]":
        """Create an effect that awaits ``coro_fn`` capturing failure as a value.

        ``.run()`` returns ``Ok(value)`` on success or ``Error(exc)`` when the
        awaitable raises an ``Exception``. ``BaseException`` (including
        ``asyncio.CancelledError``) propagates.
        """
        return AsyncEffect.defer(coro_fn, *args, **kwargs).as_result()


def from_effect(effect: Effect[T]) -> AsyncEffect[T]:
    """Lift a synchronous :class:`Effect` into an :class:`AsyncEffect`."""
    return effect.to_async()


def to_effect(ae: AsyncEffect[T]) -> Effect[T]:
    """Bridge an :class:`AsyncEffect` to a synchronous :class:`Effect`.

    The returned effect's ``.run()`` drives the awaitable to completion via
    :func:`asyncio.run`. It therefore must NOT be run from inside an already
    running event loop -- doing so raises a clear ``RuntimeError``.
    """

    def runner() -> T:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(ae.run())
        raise RuntimeError(
            "to_effect cannot run inside a running event loop; "
            "await the AsyncEffect directly (e.g. `await ae.run()`) instead."
        )

    return Effect(runner)
