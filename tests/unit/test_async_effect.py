"""Unit tests for the AsyncEffect[T] sibling class."""

import asyncio
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types import AsyncEffect
from stolas.types.result import Error, Ok


async def _value(value: int) -> int:
    return value


async def _boom() -> int:
    raise ValueError("boom")


class TestAsyncEffectRun:
    """AsyncEffect.run awaits a fresh awaitable from the factory."""

    def test_run_awaits_factory_result(self) -> None:
        ae: AsyncEffect[int] = AsyncEffect(lambda: _value(5))
        assert asyncio.run(ae.run()) == 5

    def test_does_not_run_on_creation(self) -> None:
        calls: list[int] = []

        async def factory() -> int:
            calls.append(1)
            return 1

        AsyncEffect(factory)
        assert calls == []

    def test_fresh_awaitable_per_run(self) -> None:
        counter = {"n": 0}

        async def factory() -> int:
            counter["n"] += 1
            return counter["n"]

        ae = AsyncEffect(factory)

        async def both() -> tuple[int, int]:
            return await ae.run(), await ae.run()

        assert asyncio.run(both()) == (1, 2)


class TestAsyncEffectPure:
    """AsyncEffect.pure wraps a value in an async factory."""

    def test_pure_run_returns_value(self) -> None:
        assert asyncio.run(AsyncEffect.pure(11).run()) == 11


class TestAsyncEffectDefer:
    """AsyncEffect.defer wraps a coroutine function and its arguments lazily."""

    def test_defer_passes_args(self) -> None:
        async def add(a: int, b: int) -> int:
            return a + b

        assert asyncio.run(AsyncEffect.defer(add, 3, 4).run()) == 7

    def test_defer_passes_kwargs(self) -> None:
        async def greet(*, name: str) -> str:
            return f"hi {name}"

        assert asyncio.run(AsyncEffect.defer(greet, name="ada").run()) == "hi ada"

    def test_defer_does_not_run_on_creation(self) -> None:
        calls: list[int] = []

        async def fn() -> int:
            calls.append(1)
            return 1

        AsyncEffect.defer(fn)
        assert calls == []


class TestAsyncEffectMap:
    """AsyncEffect.map transforms the eventual result without running early."""

    def test_map_transforms_result(self) -> None:
        ae = AsyncEffect.pure(10).map(lambda x: x * 2)
        assert asyncio.run(ae.run()) == 20

    def test_map_is_lazy(self) -> None:
        calls: list[int] = []

        async def factory() -> int:
            calls.append(1)
            return 1

        AsyncEffect(factory).map(lambda x: x + 1)
        assert calls == []


class TestAsyncEffectBind:
    """AsyncEffect.bind flattens T -> AsyncEffect[U]."""

    def test_bind_flattens(self) -> None:
        ae = AsyncEffect.pure(4).bind(lambda x: AsyncEffect.pure(x * 3))
        assert asyncio.run(ae.run()) == 12

    def test_bind_is_lazy(self) -> None:
        calls: list[int] = []

        async def factory() -> int:
            calls.append(1)
            return 1

        AsyncEffect(factory).bind(lambda x: AsyncEffect.pure(x))
        assert calls == []


class TestAsyncEffectRshift:
    """AsyncEffect.__rshift__ composes a plain function without running."""

    def test_rshift_applies_function(self) -> None:
        ae = AsyncEffect.pure(6) >> (lambda x: x + 1)
        assert asyncio.run(ae.run()) == 7

    def test_rshift_is_lazy(self) -> None:
        calls: list[int] = []

        async def factory() -> int:
            calls.append(1)
            return 1

        AsyncEffect(factory) >> (lambda x: x)
        assert calls == []

    def test_rshift_returns_async_effect(self) -> None:
        assert isinstance(AsyncEffect.pure(1) >> (lambda x: x), AsyncEffect)


class TestAsyncEffectAsResult:
    """AsyncEffect.as_result captures success/failure as a Result value."""

    def test_as_result_success_returns_ok(self) -> None:
        assert asyncio.run(AsyncEffect.pure(8).as_result().run()) == Ok(8)

    def test_as_result_failure_returns_error(self) -> None:
        result = asyncio.run(AsyncEffect(_boom).as_result().run())
        assert isinstance(result, Error)
        assert isinstance(result.error, ValueError)

    def test_as_result_cancelled_error_propagates(self) -> None:
        async def cancel() -> int:
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            asyncio.run(AsyncEffect(cancel).as_result().run())


class TestAsyncEffectAttempt:
    """AsyncEffect.attempt defers a coroutine and captures its outcome."""

    def test_attempt_success_returns_ok(self) -> None:
        assert asyncio.run(AsyncEffect.attempt(_value, 3).run()) == Ok(3)

    def test_attempt_failure_returns_error(self) -> None:
        result = asyncio.run(AsyncEffect.attempt(_boom).run())
        assert isinstance(result, Error)
        assert isinstance(result.error, ValueError)

    def test_attempt_cancelled_error_propagates(self) -> None:
        async def cancel() -> int:
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            asyncio.run(AsyncEffect.attempt(cancel).run())


class TestAsyncEffectImmutability:
    """AsyncEffect is immutable and structurally introspectable."""

    def test_setattr_raises(self) -> None:
        ae = AsyncEffect.pure(1)
        with pytest.raises(AttributeError, match="AsyncEffect is immutable"):
            ae._factory = lambda: _value(1)  # type: ignore[assignment]

    def test_delattr_raises(self) -> None:
        ae = AsyncEffect.pure(1)
        with pytest.raises(AttributeError, match="AsyncEffect is immutable"):
            del ae._factory

    def test_factory_property_returns_factory(self) -> None:
        factory = lambda: _value(1)  # noqa: E731
        assert AsyncEffect(factory).factory is factory

    def test_repr(self) -> None:
        assert repr(AsyncEffect.pure(1)) == "AsyncEffect(<factory>)"


class TestAsyncEffectEquality:
    """AsyncEffect equality and hashing are identity-of-factory based."""

    def test_eq_same_factory_is_true(self) -> None:
        factory = lambda: _value(1)  # noqa: E731
        assert AsyncEffect(factory) == AsyncEffect(factory)

    def test_eq_different_factory_is_false(self) -> None:
        assert AsyncEffect.pure(1) != AsyncEffect.pure(1)

    def test_eq_with_non_async_effect_is_not_equal(self) -> None:
        assert AsyncEffect.pure(1) != 5

    def test_hash_matches_factory_identity(self) -> None:
        factory = lambda: _value(1)  # noqa: E731
        assert hash(AsyncEffect(factory)) == hash(AsyncEffect(factory))
