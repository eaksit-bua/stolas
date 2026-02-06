"""Unit tests for arity decorators."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import binary, quaternary, ternary, unary
from stolas.operand.arity import Curried
from stolas.types.result import Ok


@unary
def double(x: int) -> int:
    """Double a number."""
    return x * 2


@binary
def scale(factor: int, x: int) -> int:
    """Scale x by factor."""
    return x * factor


@ternary
def add_three(a: int, b: int, c: int) -> int:
    """Add three numbers."""
    return a + b + c


@quaternary
def combine_four(a: str, b: str, c: str, d: str) -> str:
    """Combine four strings."""
    return a + b + c + d


class TestUnary:
    """Tests for @unary decorator."""

    def test_immediate_execution(self) -> None:
        assert double(5) == 10

    def test_returns_curried(self) -> None:
        assert isinstance(double, Curried)

    def test_empty_call_returns_self(self) -> None:
        result = double()
        assert result is double

    def test_extra_args_raises(self) -> None:
        with pytest.raises(TypeError, match="takes 1 positional arguments but 2"):
            double(1, 2)

    def test_wrong_arity_definition_raises(self) -> None:
        with pytest.raises(TypeError, match="@unary requires exactly 1 parameters"):

            @unary
            def wrong(a: int, b: int) -> int:
                return a + b


class TestBinary:
    """Tests for @binary decorator."""

    def test_immediate_execution(self) -> None:
        assert scale(2, 5) == 10

    def test_partial_application(self) -> None:
        double_scale = scale(2)
        assert isinstance(double_scale, Curried)
        assert double_scale(5) == 10

    def test_chained_partial(self) -> None:
        assert scale(2)(5) == 10

    def test_empty_call_returns_self(self) -> None:
        result = scale()
        assert result is scale

    def test_extra_args_raises(self) -> None:
        with pytest.raises(TypeError, match="takes 2 positional arguments but 3"):
            scale(1, 2, 3)

    def test_extra_args_on_partial_raises(self) -> None:
        partial = scale(2)
        with pytest.raises(TypeError, match="takes 2 positional arguments but 3"):
            partial(3, 4)

    def test_wrong_arity_definition_raises(self) -> None:
        with pytest.raises(TypeError, match="@binary requires exactly 2 parameters"):

            @binary
            def wrong(a: int) -> int:
                return a


class TestTernary:
    """Tests for @ternary decorator."""

    def test_immediate_execution(self) -> None:
        assert add_three(1, 2, 3) == 6

    def test_partial_one_arg(self) -> None:
        partial = add_three(1)
        assert isinstance(partial, Curried)
        assert partial(2, 3) == 6

    def test_partial_two_args(self) -> None:
        partial = add_three(1, 2)
        assert isinstance(partial, Curried)
        assert partial(3) == 6

    def test_chained_partial(self) -> None:
        assert add_three(1)(2)(3) == 6
        assert add_three(1)(2, 3) == 6
        assert add_three(1, 2)(3) == 6

    def test_empty_call_returns_self(self) -> None:
        result = add_three()
        assert result is add_three

    def test_extra_args_raises(self) -> None:
        with pytest.raises(TypeError, match="takes 3 positional arguments but 4"):
            add_three(1, 2, 3, 4)

    def test_wrong_arity_definition_raises(self) -> None:
        with pytest.raises(TypeError, match="@ternary requires exactly 3 parameters"):

            @ternary
            def wrong(a: int, b: int) -> int:
                return a + b


class TestQuaternary:
    """Tests for @quaternary decorator."""

    def test_immediate_execution(self) -> None:
        assert combine_four("a", "b", "c", "d") == "abcd"

    def test_partial_one_arg(self) -> None:
        partial = combine_four("a")
        assert partial("b", "c", "d") == "abcd"

    def test_partial_two_args(self) -> None:
        partial = combine_four("a", "b")
        assert partial("c", "d") == "abcd"

    def test_partial_three_args(self) -> None:
        partial = combine_four("a", "b", "c")
        assert partial("d") == "abcd"

    def test_chained_partial(self) -> None:
        assert combine_four("a")("b")("c")("d") == "abcd"
        assert combine_four("a", "b")("c")("d") == "abcd"
        assert combine_four("a")("b", "c")("d") == "abcd"

    def test_extra_args_raises(self) -> None:
        with pytest.raises(TypeError, match="takes 4 positional arguments but 5"):
            combine_four("a", "b", "c", "d", "e")

    def test_wrong_arity_definition_raises(self) -> None:
        with pytest.raises(
            TypeError, match="@quaternary requires exactly 4 parameters"
        ):

            @quaternary
            def wrong(a: str, b: str, c: str) -> str:
                return a + b + c


class TestCurriedMetadata:
    """Tests for Curried metadata preservation."""

    def test_preserves_doc(self) -> None:
        assert double.__doc__ == "Double a number."
        assert scale.__doc__ == "Scale x by factor."

    def test_preserves_name(self) -> None:
        assert double.__name__ == "double"
        assert scale.__name__ == "scale"

    def test_preserves_annotations(self) -> None:
        assert "x" in double.__annotations__
        assert "return" in double.__annotations__

    def test_repr_unfilled(self) -> None:
        assert repr(scale) == "scale(?, ?)"

    def test_repr_partial_filled(self) -> None:
        partial = scale(2)
        assert repr(partial) == "scale(factor=2, ?)"

    def test_repr_ternary_partial(self) -> None:
        partial = add_three(1, 2)
        assert repr(partial) == "add_three(a=1, b=2, ?)"


class TestPipelineIntegration:
    """Tests for pipeline operator integration."""

    def test_binary_with_ok(self) -> None:
        result = Ok(10) >> scale(2)
        assert isinstance(result, Ok)
        assert result.value == 20

    def test_ternary_partial_with_ok(self) -> None:
        result = Ok(3) >> add_three(1, 2)
        assert isinstance(result, Ok)
        assert result.value == 6

    def test_chained_pipeline(self) -> None:
        result = Ok(5) >> scale(2) >> scale(3)
        assert isinstance(result, Ok)
        assert result.value == 30


class TestCurriedWrapper:
    """Test Curried with wrapper function."""

    def test_wrapper_applied_on_execution(self) -> None:
        from stolas.operand.arity import Curried

        def add(a: int, b: int) -> int:
            return a + b

        def triple(x: int) -> int:
            return x * 3

        curried = Curried(add, 2, wrapper=triple)
        result = curried(3, 4)  # add(3,4)=7, then triple(7)=21
        assert result == 21


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
        TestUnary,
        TestBinary,
        TestTernary,
        TestQuaternary,
        TestCurriedMetadata,
        TestPipelineIntegration,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
