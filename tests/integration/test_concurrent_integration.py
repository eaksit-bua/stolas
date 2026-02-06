"""Integration tests: Async & Concurrent Execution.

Tests for `concurrent()` + `Effect` working correctly in parallel pipelines.
Covers Section 2 of the integration test plan.
"""

import asyncio
import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

import pytest

from stolas.operand import concurrent
from stolas.types.effect import Effect
from stolas.types.result import Ok, Error
from stolas.logic.placeholder import _


# ── Async helper functions ──────────────────────────────────────────────────


async def async_double(x: int) -> int:
    """Async function that doubles the input."""
    await asyncio.sleep(0.01)
    return x * 2


async def async_triple(x: int) -> int:
    """Async function that triples the input."""
    await asyncio.sleep(0.01)
    return x * 3


async def async_add_ten(x: int) -> int:
    """Async function that adds ten."""
    await asyncio.sleep(0.01)
    return x + 10


async def async_fail(x: int) -> int:
    """Async function that always fails."""
    await asyncio.sleep(0.01)
    raise ValueError(f"Failed for {x}")


# ── Test Classes ────────────────────────────────────────────────────────────


class TestParallelAsyncFunctions:
    """Test running multiple async functions via concurrent()."""

    def test_two_async_functions(self) -> None:
        """Run two async functions and verify both results collected."""

        async def run_test() -> None:
            conc_fn = concurrent(async_double, async_triple)
            effect = conc_fn(5)

            assert isinstance(effect, Effect)
            result = await effect.run()
            assert result == (10, 15)

        asyncio.run(run_test())

    def test_three_async_functions(self) -> None:
        """Run three async functions in parallel."""

        async def run_test() -> None:
            conc_fn = concurrent(async_double, async_triple, async_add_ten)
            effect = conc_fn(5)

            result = await effect.run()
            assert result == (10, 15, 15)

        asyncio.run(run_test())

    def test_single_async_function(self) -> None:
        """Single async function still works."""

        async def run_test() -> None:
            conc_fn = concurrent(async_double)
            effect = conc_fn(7)

            result = await effect.run()
            assert result == (14,)

        asyncio.run(run_test())


class TestEffectWrapping:
    """Verify concurrent() returns an Effect containing the async coroutine."""

    def test_returns_effect_without_execution(self) -> None:
        """concurrent() returns Effect, does not execute immediately."""
        call_count = 0

        async def track_call(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        conc_fn = concurrent(track_call)
        effect = conc_fn(5)

        # Should not have executed yet
        assert call_count == 0
        assert isinstance(effect, Effect)

    def test_effect_run_triggers_execution(self) -> None:
        """Calling .run() triggers the async execution."""
        call_count = 0

        async def track_call(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        async def run_test() -> None:
            nonlocal call_count
            conc_fn = concurrent(track_call, track_call)
            effect = conc_fn(5)

            assert call_count == 0
            await effect.run()
            assert call_count == 2

        asyncio.run(run_test())


class TestPipelineWithConcurrent:
    """Test Ok(val) >> concurrent(...) produces correct Effect wrapping tuple."""

    def test_ok_into_concurrent(self) -> None:
        """Ok value flows into concurrent and produces Effect with results."""

        async def run_test() -> None:
            conc_fn = concurrent(async_double, async_triple)
            pipeline_result = Ok(5) >> conc_fn

            assert isinstance(pipeline_result, Ok)
            effect = pipeline_result.unwrap()
            assert isinstance(effect, Effect)

            result = await effect.run()
            assert result == (10, 15)

        asyncio.run(run_test())

    def test_chained_pipeline_with_concurrent(self) -> None:
        """Pipeline with map before concurrent."""

        async def run_test() -> None:
            conc_fn = concurrent(async_double, async_add_ten)
            pipeline_result = Ok(3) >> (_ + 2) >> conc_fn

            effect = pipeline_result.unwrap()
            result = await effect.run()
            # (3 + 2) = 5, then (5 * 2, 5 + 10) = (10, 15)
            assert result == (10, 15)

        asyncio.run(run_test())

    def test_error_skips_concurrent(self) -> None:
        """Error skips concurrent entirely."""
        conc_fn = concurrent(async_double, async_triple)
        pipeline_result = Error("failed") >> conc_fn

        assert isinstance(pipeline_result, Error)
        assert pipeline_result.error == "failed"


class TestErrorInConcurrent:
    """Test that one failing async function properly propagates error."""

    def test_one_failing_function_raises(self) -> None:
        """If one async function fails, the gather raises."""

        async def run_test() -> None:
            conc_fn = concurrent(async_double, async_fail)
            effect = conc_fn(5)

            with pytest.raises(ValueError, match="Failed for 5"):
                await effect.run()

        asyncio.run(run_test())

    def test_all_failing_functions(self) -> None:
        """All failing functions still raises first error."""

        async def run_test() -> None:
            conc_fn = concurrent(async_fail, async_fail)
            effect = conc_fn(3)

            with pytest.raises(ValueError, match="Failed for 3"):
                await effect.run()

        asyncio.run(run_test())


class TestConcurrentWithDifferentInputTypes:
    """Test concurrent with various input types."""

    def test_with_string_input(self) -> None:
        """Concurrent works with string input."""

        async def async_upper(s: str) -> str:
            return s.upper()

        async def async_reverse(s: str) -> str:
            return s[::-1]

        async def run_test() -> None:
            conc_fn = concurrent(async_upper, async_reverse)
            effect = conc_fn("hello")

            result = await effect.run()
            assert result == ("HELLO", "olleh")

        asyncio.run(run_test())

    def test_with_list_input(self) -> None:
        """Concurrent works with list input."""

        async def async_sum(nums: list[int]) -> int:
            return sum(nums)

        async def async_len(nums: list[int]) -> int:
            return len(nums)

        async def run_test() -> None:
            conc_fn = concurrent(async_sum, async_len)
            effect = conc_fn([1, 2, 3, 4, 5])

            result = await effect.run()
            assert result == (15, 5)

        asyncio.run(run_test())
