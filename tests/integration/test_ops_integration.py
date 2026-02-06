"""Integration tests: Decorator Stacking (@ops).

Tests for decorator composition with `@ops`.
Covers Section 8 of the integration test plan.
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import (
    ops,
    binary,
    as_result,
    as_option,
    as_effect,
    as_validated,
    ternary,
)
from stolas.types.result import Ok, Error
from stolas.types.option import Some, Nothing
from stolas.types.effect import Effect
from stolas.types.validated import Valid, Invalid
from stolas.logic.placeholder import _


# ── Test Classes ────────────────────────────────────────────────────────────


class TestBinaryAsResult:
    """@ops(binary, as_result) produces curried, safe function."""

    def test_binary_as_result_success(self) -> None:
        """Curried binary function with as_result returns Ok on success."""

        @ops(binary, as_result)
        def divide(a: int, b: int) -> float:
            return a / b

        # Full application
        result = divide(10)(2)
        assert isinstance(result, Ok)
        assert result.value == 5.0

    def test_binary_as_result_failure(self) -> None:
        """Curried binary function with as_result returns Error on exception."""

        @ops(binary, as_result)
        def divide(a: int, b: int) -> float:
            return a / b

        result = divide(10)(0)
        assert isinstance(result, Error)
        assert isinstance(result.error, ZeroDivisionError)

    def test_partial_application(self) -> None:
        """Partial application works correctly."""

        @ops(binary, as_result)
        def add(a: int, b: int) -> int:
            return a + b

        add_five = add(5)  # Partial application
        result = add_five(3)

        assert isinstance(result, Ok)
        assert result.value == 8

    def test_in_pipeline(self) -> None:
        """Curried safe function in pipeline."""

        @ops(binary, as_result)
        def multiply(a: int, b: int) -> int:
            return a * b

        result = Ok(5) >> multiply(3)

        assert isinstance(result, Ok)
        assert result.value == 15


class TestTernaryCurrying:
    """Multi-argument currying with ternary decorator."""

    def test_ternary_currying(self) -> None:
        """Ternary function supports multiple partial applications."""

        @ops(ternary)
        def add_three(a: int, b: int, c: int) -> int:
            return a + b + c

        add_one = add_three(1)
        add_one_two = add_one(2)
        result = add_one_two(3)

        assert result == 6

    def test_ternary_in_pipeline(self) -> None:
        """Ternary curried function in pipeline."""

        @ops(ternary)
        def concat(a: str, b: str, c: str) -> str:
            return f"{a}-{b}-{c}"

        concat_hello = concat("hello")
        concat_hello_world = concat_hello("world")
        result = concat_hello_world("!")

        assert result == "hello-world-!"


class TestBinaryAsEffect:
    """Curried function with deferred execution."""

    def test_binary_as_effect_deferred(self) -> None:
        """Binary function with as_effect defers execution."""
        call_count = 0

        @ops(binary, as_effect)
        def add(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        effect = add(3)(4)

        assert call_count == 0  # Not executed yet
        assert isinstance(effect, Effect)

        result = effect.run()
        assert call_count == 1
        assert result == 7

    def test_effect_composition(self) -> None:
        """Effect from curried function can be composed."""

        @ops(binary, as_effect)
        def multiply(a: int, b: int) -> int:
            return a * b

        effect = multiply(3)(4)
        composed = effect >> (_ + 10)

        result = composed.run()
        assert result == 22  # 3 * 4 + 10


class TestAsValidatedStandalone:
    """as_validated works standalone (not with @ops currying)."""

    def test_as_validated_success(self) -> None:
        """as_validated returns Valid on success."""

        @as_validated
        def safe_divide(a: int, b: int) -> float:
            return a / b

        result = safe_divide(10, 2)
        assert isinstance(result, Valid)
        assert result.value == 5.0

    def test_as_validated_failure(self) -> None:
        """as_validated returns Invalid on failure."""

        @as_validated
        def safe_divide(a: int, b: int) -> float:
            return a / b

        result = safe_divide(10, 0)
        assert isinstance(result, Invalid)
        assert isinstance(result.errors[0], ZeroDivisionError)


class TestAsOptionStandalone:
    """as_option works standalone (not with @ops currying)."""

    def test_as_option_some(self) -> None:
        """as_option returns Some when value returned."""

        @as_option
        def find_value(x: int) -> int | None:
            return x if x > 0 else None

        result = find_value(5)
        assert isinstance(result, Some)
        assert result.value == 5

    def test_as_option_nothing(self) -> None:
        """as_option returns Nothing when None returned."""

        @as_option
        def find_value(x: int) -> int | None:
            return x if x > 0 else None

        result = find_value(-5)
        assert result is Nothing


class TestDecoratorOrderMatters:
    """Verify decorator order produces expected behavior."""

    def test_binary_then_as_result(self) -> None:
        """binary, then as_result: curry first, then wrap."""

        @ops(binary, as_result)
        def sub(a: int, b: int) -> int:
            return a - b

        result = sub(10)(3)
        assert isinstance(result, Ok)
        assert result.value == 7

    def test_multiple_binary_as_result_in_pipeline(self) -> None:
        """Multiple curried safe functions in pipeline."""

        @ops(binary, as_result)
        def add(a: int, b: int) -> int:
            return a + b

        @ops(binary, as_result)
        def multiply(a: int, b: int) -> int:
            return a * b

        # Chain: Start with 5, add 3 (=8), multiply by 2 (=16)
        result = Ok(5) >> add(3) >> multiply(2)

        assert isinstance(result, Ok)
        assert result.value == 16


class TestPartialApplicationInPipeline:
    """Curried function used mid-pipeline with >>."""

    def test_curried_in_ok_pipeline(self) -> None:
        """Partial application flows through Ok pipeline."""

        @ops(binary, as_result)
        def add(a: int, b: int) -> int:
            return a + b

        @ops(binary, as_result)
        def multiply(a: int, b: int) -> int:
            return a * b

        # Chain: Start with 5, add 3 (=8), multiply by 2 (=16)
        result = Ok(5) >> add(3) >> multiply(2)

        assert isinstance(result, Ok)
        assert result.value == 16

    def test_partial_applied_multiple_times(self) -> None:
        """Same partial function used multiple times."""

        @ops(binary, as_result)
        def add(a: int, b: int) -> int:
            return a + b

        add_ten = add(10)

        result1 = Ok(5) >> add_ten
        result2 = Ok(15) >> add_ten

        assert result1.unwrap() == 15
        assert result2.unwrap() == 25

    def test_error_in_pipeline_stops_execution(self) -> None:
        """When Error occurs in pipeline, subsequent steps are skipped."""

        @ops(binary, as_result)
        def divide(a: int, b: int) -> float:
            return a / b

        @ops(binary, as_result)
        def add(a: float, b: float) -> float:
            return a + b

        # Start with Error, everything should be skipped
        result = Error("initial error") >> divide(2) >> add(100)

        assert isinstance(result, Error)
        assert result.error == "initial error"


class TestOpsWithPlainFunctions:
    """@ops with just one decorator."""

    def test_ops_binary_only(self) -> None:
        """@ops(binary) just curries."""

        @ops(binary)
        def add(a: int, b: int) -> int:
            return a + b

        result = add(3)(4)
        assert result == 7

    def test_ops_as_result_only(self) -> None:
        """@ops(as_result) just wraps."""

        @ops(as_result)
        def risky(x: int) -> int:
            if x < 0:
                raise ValueError("Negative!")
            return x * 2

        assert risky(5) == Ok(10)
        assert isinstance(risky(-1), Error)


class TestOpsWithPipelineChaining:
    """Complex pipeline chaining with @ops decorated functions."""

    def test_full_pipeline_scenario(self) -> None:
        """Realistic pipeline with multiple curried functions."""

        @ops(binary, as_result)
        def validate_positive(threshold: int, value: int) -> int:
            if value < threshold:
                raise ValueError(f"Value {value} below threshold {threshold}")
            return value

        @ops(binary, as_result)
        def scale(factor: int, value: int) -> int:
            return value * factor

        @ops(binary, as_result)
        def offset(amount: int, value: int) -> int:
            return value + amount

        # Pipeline: validate >= 0, then scale by 2, then offset by 10
        result = Ok(5) >> validate_positive(0) >> scale(2) >> offset(10)

        assert isinstance(result, Ok)
        assert result.value == 20  # (5 * 2) + 10

        # Failing validation
        result = Ok(-5) >> validate_positive(0) >> scale(2) >> offset(10)

        assert isinstance(result, Error)

    def test_pipeline_with_option_standalone(self) -> None:
        """Pipeline with Option-returning functions (not curried with @ops)."""

        @as_option
        def lookup(key: str) -> int | None:
            data = {"a": 1, "b": 2, "c": 3}
            return data.get(key)

        result = lookup("a")
        assert isinstance(result, Some)
        assert result.value == 1

        result = lookup("z")
        assert result is Nothing

    def test_combined_result_and_effect(self) -> None:
        """Combine Result and Effect in pipeline."""

        @ops(binary, as_result)
        def safe_divide(a: int, b: int) -> float:
            return a / b

        @ops(binary, as_effect)
        def deferred_multiply(a: float, b: float) -> float:
            return a * b

        # Divide first
        div_result = safe_divide(10)(2)
        assert isinstance(div_result, Ok)
        assert div_result.value == 5.0

        # Then create deferred multiplication
        effect = deferred_multiply(div_result.unwrap())(3)
        assert isinstance(effect, Effect)
        assert effect.run() == 15.0
