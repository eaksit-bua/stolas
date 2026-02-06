"""Unit tests for safe wrappers (@as_result, @as_option, @as_validated, @as_many, @as_effect)."""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import as_effect, as_many, as_option, as_result, as_validated
from stolas.types.effect import Effect
from stolas.types.many import Many
from stolas.types.option import Nothing, Some
from stolas.types.result import Error, Ok
from stolas.types.validated import Invalid, Valid


class TestAsResult:
    """Tests for @as_result decorator."""

    def test_returns_ok_on_success(self) -> None:
        @as_result
        def add(a: int, b: int) -> int:
            return a + b

        result = add(2, 3)
        assert isinstance(result, Ok)
        assert result.value == 5

    def test_returns_error_on_exception(self) -> None:
        @as_result
        def divide(a: int, b: int) -> float:
            return a / b

        result = divide(10, 0)
        assert isinstance(result, Error)
        assert isinstance(result.error, ZeroDivisionError)

    def test_preserves_function_name(self) -> None:
        @as_result
        def my_function() -> int:
            return 42

        assert my_function.__name__ == "my_function"

    def test_handles_value_error(self) -> None:
        @as_result
        def validate(x: int) -> int:
            if x < 0:
                raise ValueError("must be positive")
            return x

        result = validate(-1)
        assert isinstance(result, Error)
        assert isinstance(result.error, ValueError)

    def test_handles_kwargs(self) -> None:
        @as_result
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        result = greet("World", greeting="Hi")
        assert isinstance(result, Ok)
        assert result.value == "Hi, World!"

    def test_ok_is_ok(self) -> None:
        @as_result
        def success() -> int:
            return 42

        assert success().is_ok()
        assert not success().is_error()

    def test_error_is_error(self) -> None:
        @as_result
        def fail() -> int:
            raise RuntimeError("fail")

        assert fail().is_error()
        assert not fail().is_ok()


class TestAsOption:
    """Tests for @as_option decorator."""

    def test_returns_some_on_value(self) -> None:
        @as_option
        def get_value() -> int:
            return 42

        result = get_value()
        assert isinstance(result, Some)
        assert result.value == 42

    def test_returns_nothing_on_none(self) -> None:
        @as_option
        def get_none() -> None:
            return None

        result = get_none()
        assert result is Nothing

    def test_dict_get_returns_some(self) -> None:
        @as_option
        def dict_get(d: dict, key: str) -> str | None:
            return d.get(key)

        result = dict_get({"a": "value"}, "a")
        assert isinstance(result, Some)
        assert result.value == "value"

    def test_dict_get_returns_nothing(self) -> None:
        @as_option
        def dict_get(d: dict, key: str) -> str | None:
            return d.get(key)

        result = dict_get({"a": "value"}, "missing")
        assert result is Nothing

    def test_preserves_function_name(self) -> None:
        @as_option
        def my_function() -> int | None:
            return 42

        assert my_function.__name__ == "my_function"

    def test_some_is_some(self) -> None:
        @as_option
        def value() -> int:
            return 1

        assert value().is_some()
        assert not value().is_nothing()

    def test_nothing_is_nothing(self) -> None:
        @as_option
        def none_value() -> None:
            return None

        assert none_value().is_nothing()
        assert not none_value().is_some()


class TestAsValidated:
    """Tests for @as_validated decorator."""

    def test_returns_valid_on_success(self) -> None:
        @as_validated
        def validate(x: int) -> int:
            return x * 2

        result = validate(5)
        assert isinstance(result, Valid)
        assert result.value == 10

    def test_returns_invalid_on_exception(self) -> None:
        @as_validated
        def validate(x: int) -> int:
            if x < 0:
                raise ValueError("must be positive")
            return x

        result = validate(-1)
        assert isinstance(result, Invalid)
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], ValueError)

    def test_preserves_function_name(self) -> None:
        @as_validated
        def my_function() -> int:
            return 42

        assert my_function.__name__ == "my_function"

    def test_handles_multiple_validations(self) -> None:
        @as_validated
        def check_range(x: int) -> int:
            if x < 0:
                raise ValueError("must be non-negative")
            if x > 100:
                raise ValueError("must be <= 100")
            return x

        valid_result = check_range(50)
        assert isinstance(valid_result, Valid)
        assert valid_result.value == 50

        invalid_result = check_range(-1)
        assert isinstance(invalid_result, Invalid)

    def test_valid_is_valid(self) -> None:
        @as_validated
        def success() -> int:
            return 42

        assert success().is_valid()
        assert not success().is_invalid()

    def test_invalid_is_invalid(self) -> None:
        @as_validated
        def fail() -> int:
            raise RuntimeError("fail")

        assert fail().is_invalid()
        assert not fail().is_valid()


class TestAsMany:
    """Tests for @as_many decorator."""

    def test_returns_many_from_list(self) -> None:
        @as_many
        def get_numbers(n: int) -> list[int]:
            return list(range(n))

        result = get_numbers(5)
        assert isinstance(result, Many)
        assert result.items == (0, 1, 2, 3, 4)

    def test_returns_many_from_generator(self) -> None:
        @as_many
        def gen_numbers(n: int) -> list[int]:
            return [x * 2 for x in range(n)]

        result = gen_numbers(3)
        assert isinstance(result, Many)
        assert result.items == (0, 2, 4)

    def test_empty_iterable(self) -> None:
        @as_many
        def empty_list() -> list[int]:
            return []

        result = empty_list()
        assert isinstance(result, Many)
        assert result.is_empty()

    def test_preserves_function_name(self) -> None:
        @as_many
        def my_function() -> list[int]:
            return [1, 2, 3]

        assert my_function.__name__ == "my_function"

    def test_many_map_works(self) -> None:
        @as_many
        def get_numbers() -> list[int]:
            return [1, 2, 3]

        result = get_numbers().map(lambda x: x * 2)
        assert result.items == (2, 4, 6)

    def test_many_filter_works(self) -> None:
        @as_many
        def get_numbers() -> list[int]:
            return [1, 2, 3, 4, 5]

        result = get_numbers().filter(lambda x: x % 2 == 0)
        assert result.items == (2, 4)


class TestAsEffect:
    """Tests for @as_effect decorator."""

    def test_returns_effect(self) -> None:
        @as_effect
        def compute(x: int) -> int:
            return x * 2

        result = compute(5)
        assert isinstance(result, Effect)

    def test_defers_execution(self) -> None:
        call_count = 0

        @as_effect
        def side_effect() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        effect = side_effect()
        assert call_count == 0
        effect.run()
        assert call_count == 1

    def test_run_returns_value(self) -> None:
        @as_effect
        def compute(x: int, y: int) -> int:
            return x + y

        result = compute(3, 4).run()
        assert result == 7

    def test_preserves_function_name(self) -> None:
        @as_effect
        def my_function() -> int:
            return 42

        assert my_function.__name__ == "my_function"

    def test_effect_map_works(self) -> None:
        @as_effect
        def get_value() -> int:
            return 10

        result = get_value().map(lambda x: x * 2).run()
        assert result == 20

    def test_multiple_runs(self) -> None:
        call_count = 0

        @as_effect
        def counter() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        effect = counter()
        assert effect.run() == 1
        assert effect.run() == 2
        assert effect.run() == 3


class TestSafeWithCurried:
    """Tests for as_result and as_effect with Curried functions."""

    def test_as_result_with_curried_exception(self) -> None:
        from stolas.operand import binary, ops

        @ops(binary, as_result)
        def divide(a: int, b: int) -> float:
            return a / b

        result = divide(10)(0)
        assert isinstance(result, Error)
        assert isinstance(result.error, ZeroDivisionError)

    def test_as_effect_with_curried(self) -> None:
        from stolas.operand import binary, ops

        @ops(binary, as_effect)
        def add(a: int, b: int) -> int:
            return a + b

        effect = add(3)(4)
        assert isinstance(effect, Effect)
        assert effect.run() == 7


def _run_test_method(instance: object, method_name: str) -> tuple[str, str]:
    """Run a single test method and return result."""
    test_name = f"{instance.__class__.__name__}.{method_name}"
    try:
        getattr(instance, method_name)()
        return (test_name, "✅ PASS")
    except Exception as e:
        return (test_name, f"❌ FAIL: {e}")


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

    passed = sum(1 for _, status in results if "PASS" in status)
    failed = len(results) - passed
    print(f"\nTotal: {len(results)} | ✅ Passed: {passed} | ❌ Failed: {failed}")


if __name__ == "__main__":
    test_classes = [
        TestAsResult,
        TestAsOption,
        TestAsValidated,
        TestAsMany,
        TestAsEffect,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
