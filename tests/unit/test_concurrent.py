"""Unit tests for concurrent module."""

import asyncio
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import concurrent
from stolas.types.effect import Effect


class TestConcurrentFunction:
    """Tests for concurrent function."""

    def test_returns_effect(self) -> None:
        async def double(x: int) -> int:
            return x * 2

        result = concurrent(double)(5)
        assert isinstance(result, Effect)

    def test_runs_single_function(self) -> None:
        async def double(x: int) -> int:
            return x * 2

        effect = concurrent(double)(5)
        result = asyncio.run(effect.run())
        assert result == (10,)

    def test_runs_multiple_functions_in_parallel(self) -> None:
        async def double(x: int) -> int:
            return x * 2

        async def triple(x: int) -> int:
            return x * 3

        effect = concurrent(double, triple)(5)
        result = asyncio.run(effect.run())
        assert result == (10, 15)

    def test_runs_three_functions(self) -> None:
        async def add_one(x: int) -> int:
            return x + 1

        async def add_two(x: int) -> int:
            return x + 2

        async def add_three(x: int) -> int:
            return x + 3

        effect = concurrent(add_one, add_two, add_three)(10)
        result = asyncio.run(effect.run())
        assert result == (11, 12, 13)

    def test_preserves_order(self) -> None:
        async def slow(x: int) -> str:
            await asyncio.sleep(0.01)
            return "slow"

        async def fast(x: int) -> str:
            return "fast"

        effect = concurrent(slow, fast)(0)
        result = asyncio.run(effect.run())
        assert result == ("slow", "fast")


class TestConcurrentPipeline:
    """Tests for concurrent in pipeline context."""

    def test_with_lambda_transform(self) -> None:
        async def square(x: int) -> int:
            return x * x

        async def cube(x: int) -> int:
            return x * x * x

        value = 3
        effect = concurrent(square, cube)(value)
        result = asyncio.run(effect.run())
        assert result == (9, 27)


def _run_test_method(instance: object, method_name: str) -> tuple[str, str]:
    """Run a single test method and return result."""
    test_name = f"{instance.__class__.__name__}.{method_name}"
    try:
        getattr(instance, method_name)()
        return (test_name, "PASS")
    except Exception as e:
        return (test_name, f"FAIL: {e}")


def _run_test_class(test_class: type) -> list[tuple[str, str]]:
    """Run all test methods in a test class."""
    instance = test_class()
    results: list[tuple[str, str]] = []
    for method_name in dir(instance):
        if method_name.startswith("test_"):
            results.append(_run_test_method(instance, method_name))
    return results


def _print_results(results: list[tuple[str, str]]) -> None:
    """Print test results summary."""
    for test_name, status in results:
        print(f"{status}: {test_name}")

    passed = sum(1 for _, status in results if status == "PASS")
    failed = len(results) - passed
    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}")


if __name__ == "__main__":
    test_classes = [
        TestConcurrentFunction,
        TestConcurrentPipeline,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
