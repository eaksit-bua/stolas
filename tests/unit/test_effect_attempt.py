"""Unit tests for Effect.attempt, Effect.as_result, and Effect.to_async."""

import asyncio
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types import AsyncEffect, Effect
from stolas.types.result import Error, Ok


class TestEffectAttemptSuccess:
    """Effect.attempt captures a successful thunk as Ok."""

    def test_attempt_success_returns_ok(self) -> None:
        effect = Effect.attempt(lambda: 42)
        assert effect.run() == Ok(42)

    def test_attempt_does_not_run_on_creation(self) -> None:
        ran: list[int] = []
        Effect.attempt(lambda: ran.append(1))
        assert ran == []


class TestEffectAttemptFailure:
    """Effect.attempt captures a raised Exception as Error."""

    def test_attempt_failure_returns_error(self) -> None:
        exc = ValueError("boom")

        def thunk() -> int:
            raise exc

        assert Effect.attempt(thunk).run() == Error(exc)

    def test_attempt_error_wraps_the_exact_exception(self) -> None:
        exc = KeyError("missing")

        def thunk() -> int:
            raise exc

        result = Effect.attempt(thunk).run()
        assert isinstance(result, Error)
        assert result.error is exc


class TestEffectAttemptBaseExceptionPropagates:
    """BaseException is never captured by Effect.attempt."""

    def test_keyboard_interrupt_propagates(self) -> None:
        def thunk() -> int:
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            Effect.attempt(thunk).run()

    def test_system_exit_propagates(self) -> None:
        def thunk() -> int:
            raise SystemExit

        with pytest.raises(SystemExit):
            Effect.attempt(thunk).run()


class TestEffectAsResult:
    """Effect.as_result wraps an existing effect's outcome as a Result."""

    def test_as_result_success_returns_ok(self) -> None:
        assert Effect.pure(7).as_result().run() == Ok(7)

    def test_as_result_failure_returns_error(self) -> None:
        exc = RuntimeError("nope")

        def thunk() -> int:
            raise exc

        assert Effect(thunk).as_result().run() == Error(exc)

    def test_as_result_does_not_run_on_creation(self) -> None:
        ran: list[int] = []
        Effect(lambda: ran.append(1)).as_result()
        assert ran == []

    def test_as_result_base_exception_propagates(self) -> None:
        def thunk() -> int:
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            Effect(thunk).as_result().run()


class TestEffectToAsync:
    """Effect.to_async lifts a sync Effect into an AsyncEffect."""

    def test_to_async_returns_async_effect(self) -> None:
        assert isinstance(Effect.pure(1).to_async(), AsyncEffect)

    def test_to_async_run_yields_thunk_value(self) -> None:
        assert asyncio.run(Effect.pure(99).to_async().run()) == 99

    def test_to_async_defers_side_effect_until_run(self) -> None:
        ran: list[int] = []
        ae = Effect(lambda: ran.append(1)).to_async()
        assert ran == []
        asyncio.run(ae.run())
        assert ran == [1]
