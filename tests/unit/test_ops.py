"""Unit tests for ops decorator composer."""

import os
import sys
from typing import Any, Callable

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import as_result, binary, ops
from stolas.types.result import Error, Ok


# Test decorators
def add_prefix(func: Callable[..., str]) -> Callable[..., str]:
    """Decorator that adds 'prefix_' to result."""

    def wrapper(*args: Any, **kwargs: Any) -> str:
        return "prefix_" + func(*args, **kwargs)

    return wrapper


def add_suffix(func: Callable[..., str]) -> Callable[..., str]:
    """Decorator that adds '_suffix' to result."""

    def wrapper(*args: Any, **kwargs: Any) -> str:
        return func(*args, **kwargs) + "_suffix"

    return wrapper


def uppercase(func: Callable[..., str]) -> Callable[..., str]:
    """Decorator that uppercases result."""

    def wrapper(*args: Any, **kwargs: Any) -> str:
        return func(*args, **kwargs).upper()

    return wrapper


class TestOpsComposer:
    """Tests for ops decorator composer."""

    def test_single_decorator(self) -> None:
        @ops(uppercase)
        def greet(name: str) -> str:
            return f"hello {name}"

        assert greet("world") == "HELLO WORLD"

    def test_two_decorators(self) -> None:
        # @ops(d1, d2) should be d1(d2(f))
        # So add_prefix(add_suffix(f))
        # f returns "test", add_suffix makes "test_suffix", add_prefix makes "prefix_test_suffix"
        @ops(add_prefix, add_suffix)
        def get_value() -> str:
            return "test"

        assert get_value() == "prefix_test_suffix"

    def test_three_decorators(self) -> None:
        # ops applies left-to-right: add_suffix(add_prefix(uppercase(f)))
        # f -> "hello" -> uppercase -> "HELLO" -> add_prefix -> "prefix_HELLO" -> add_suffix -> "prefix_HELLO_suffix"
        @ops(uppercase, add_prefix, add_suffix)
        def get_word() -> str:
            return "hello"

        assert get_word() == "prefix_HELLO_suffix"

    def test_order_matches_stacked_decorators(self) -> None:
        # Verify ops(d1, d2) == @d1 @d2
        @add_prefix
        @add_suffix
        def stacked() -> str:
            return "base"

        @ops(add_prefix, add_suffix)
        def composed() -> str:
            return "base"

        assert stacked() == composed()


class TestOpsWithStolasDecorators:
    """Tests for ops with Stolas library decorators."""

    def test_with_binary(self) -> None:
        @ops(binary)
        def add(a: int, b: int) -> int:
            return a + b

        # Partial application should work
        add_five = add(5)
        assert add_five(3) == 8
        assert add(2, 3) == 5

    def test_with_as_result(self) -> None:
        @ops(as_result)
        def divide(a: int, b: int) -> float:
            return a / b

        result = divide(10, 2)
        assert isinstance(result, Ok)
        assert result.value == 5.0

        error_result = divide(10, 0)
        assert isinstance(error_result, Error)

    def test_combined_as_result_and_binary(self) -> None:
        # With left-to-right order: binary first, then as_result wraps the result
        @ops(binary, as_result)
        def safe_divide(a: int, b: int) -> float:
            return a / b

        # Partial application
        divide_by = safe_divide(10)
        result = divide_by(2)
        assert isinstance(result, Ok)
        assert result.value == 5.0


class TestOpsEdgeCases:
    """Edge case tests for ops."""

    def test_no_decorators(self) -> None:
        @ops()
        def identity(x: int) -> int:
            return x

        assert identity(42) == 42

    def test_preserves_function_for_empty_ops(self) -> None:
        def original(x: int) -> int:
            return x * 2

        decorated = ops()(original)
        assert decorated(5) == 10


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
        TestOpsComposer,
        TestOpsWithStolasDecorators,
        TestOpsEdgeCases,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
