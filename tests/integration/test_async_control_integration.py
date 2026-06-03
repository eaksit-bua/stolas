"""Integration tests across AsyncEffect, bridges, and stolas.control."""

import asyncio
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.control import RetryPolicy, bracket_async, retry, retry_async, timeout
from stolas.types import AsyncEffect, Effect, from_effect, to_effect
from stolas.types.result import Error, Ok


class TestRetryRecoversThroughResultPipeline:
    """A flaky Effect retried then mapped through a Result pipeline succeeds."""

    def test_retry_then_map_yields_final_value(self) -> None:
        tries = {"n": 0}

        def flaky() -> int:
            tries["n"] += 1
            if tries["n"] < 3:
                raise ConnectionError("transient")
            return 10

        pipeline = retry(RetryPolicy(5), Effect(flaky)).map(lambda x: x * 2)
        assert pipeline.run() == 20


class TestAsyncAttemptRetriedToValue:
    """retry_async over attempt error-values recovers to an Ok via retry_on_error."""

    def test_recovers_to_ok_after_error_values(self) -> None:
        tries = {"n": 0}

        async def coro() -> int:
            tries["n"] += 1
            if tries["n"] < 2:
                raise ValueError("flaky")
            return 5

        attempted = AsyncEffect.attempt(coro)
        retried = retry_async(RetryPolicy(4, retry_on_error=True), attempted)
        assert asyncio.run(retried.run()) == Ok(5)


class TestSyncEffectLiftedRetriedAndLowered:
    """A sync Effect lifted to async, retried, then lowered back runs to completion."""

    def test_round_trip_with_async_retry(self) -> None:
        tries = {"n": 0}

        def flaky() -> int:
            tries["n"] += 1
            if tries["n"] < 2:
                raise RuntimeError("transient")
            return 7

        async_effect = from_effect(Effect(flaky))
        retried = retry_async(RetryPolicy(3), async_effect)
        assert to_effect(retried).run() == 7


class TestTimeoutWrappingBracketAsync:
    """timeout around a slow bracket_async raises TimeoutError yet releases."""

    def test_timeout_fires_and_resource_released(self) -> None:
        released: list[str] = []

        async def acquire() -> str:
            return "conn"

        async def use(r: str) -> int:
            await asyncio.sleep(1.0)
            return 1

        async def release(r: str) -> None:
            released.append(r)

        guarded = timeout(
            0.01, AsyncEffect(lambda: bracket_async(acquire, use, release))
        )
        with pytest.raises(TimeoutError):
            asyncio.run(guarded.run())
        assert released == ["conn"]


class TestAttemptErrorFlowsThroughBridge:
    """An async attempt failure surfaces as an Error value through to_effect."""

    def test_error_value_survives_lowering(self) -> None:
        async def coro() -> int:
            raise KeyError("missing")

        result = to_effect(AsyncEffect.attempt(coro)).run()
        assert isinstance(result, Error)
        assert isinstance(result.error, KeyError)
