"""Unit tests for the Effect <-> AsyncEffect bridges."""

import asyncio
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types import AsyncEffect, Effect, from_effect, to_effect


class TestFromEffect:
    """from_effect lifts a synchronous Effect into an AsyncEffect."""

    def test_from_effect_returns_async_effect(self) -> None:
        assert isinstance(from_effect(Effect.pure(1)), AsyncEffect)

    def test_from_effect_run_yields_value(self) -> None:
        assert asyncio.run(from_effect(Effect.pure(123)).run()) == 123

    def test_from_effect_is_lazy(self) -> None:
        ran: list[int] = []
        from_effect(Effect(lambda: ran.append(1)))
        assert ran == []


class TestToEffect:
    """to_effect bridges an AsyncEffect back to a synchronous Effect."""

    def test_to_effect_returns_effect(self) -> None:
        assert isinstance(to_effect(AsyncEffect.pure(1)), Effect)

    def test_to_effect_run_drives_awaitable(self) -> None:
        assert to_effect(AsyncEffect.pure(55)).run() == 55

    def test_to_effect_is_lazy(self) -> None:
        calls: list[int] = []

        async def factory() -> int:
            calls.append(1)
            return 1

        to_effect(AsyncEffect(factory))
        assert calls == []


class TestToEffectInsideRunningLoop:
    """to_effect must refuse to run inside an already running event loop."""

    def test_run_inside_loop_raises_runtime_error(self) -> None:
        effect = to_effect(AsyncEffect.pure(1))

        async def driver() -> None:
            effect.run()

        with pytest.raises(
            RuntimeError, match="cannot run inside a running event loop"
        ):
            asyncio.run(driver())


class TestRoundTrip:
    """Lifting and lowering preserves the produced value."""

    def test_effect_to_async_and_back(self) -> None:
        assert to_effect(from_effect(Effect.pure(9))).run() == 9
