"""Unit tests for Result[T, E] type."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types import Ok, Error


class TestOkCreation:
    """Tests for Ok variant creation."""

    def test_creates_ok_with_value(self) -> None:
        result = Ok(42)
        assert result.value == 42

    def test_ok_repr(self) -> None:
        assert repr(Ok(42)) == "Ok(42)"

    def test_ok_equality(self) -> None:
        assert Ok(42) == Ok(42)
        assert Ok(42) != Ok(99)

    def test_ok_hashable(self) -> None:
        assert hash(Ok(42)) == hash(Ok(42))
        assert len({Ok(42), Ok(42)}) == 1


class TestErrorCreation:
    """Tests for Error variant creation."""

    def test_creates_error_with_value(self) -> None:
        result = Error("failed")
        assert result.error == "failed"

    def test_error_repr(self) -> None:
        assert repr(Error("failed")) == "Error('failed')"

    def test_error_equality(self) -> None:
        assert Error("failed") == Error("failed")
        assert Error("failed") != Error("other")

    def test_error_hashable(self) -> None:
        assert hash(Error("x")) == hash(Error("x"))
        assert len({Error("x"), Error("x")}) == 1


class TestResultImmutability:
    """Tests for immutability."""

    def test_ok_is_immutable(self) -> None:
        result = Ok(42)
        with pytest.raises(AttributeError, match="immutable"):
            result.value = 99

    def test_error_is_immutable(self) -> None:
        result = Error("failed")
        with pytest.raises(AttributeError, match="immutable"):
            result.error = "other"


class TestResultMethods:
    """Tests for Result methods."""

    def test_ok_map(self) -> None:
        result = Ok(10).map(lambda x: x * 2)
        assert result.value == 20

    def test_error_map_noop(self) -> None:
        result = Error("fail").map(lambda x: x * 2)
        assert result.error == "fail"

    def test_ok_map_err_noop(self) -> None:
        result = Ok(10).map_err(lambda e: e.upper())
        assert result.value == 10

    def test_error_map_err(self) -> None:
        result = Error("fail").map_err(lambda e: e.upper())
        assert result.error == "FAIL"

    def test_ok_bind(self) -> None:
        result = Ok(10).bind(lambda x: Ok(x * 2))
        assert result.value == 20

    def test_ok_bind_to_error(self) -> None:
        result = Ok(10).bind(lambda x: Error("failed"))
        assert result.error == "failed"

    def test_error_bind_noop(self) -> None:
        result = Error("fail").bind(lambda x: Ok(x * 2))
        assert result.error == "fail"

    def test_ok_unwrap(self) -> None:
        assert Ok(42).unwrap() == 42

    def test_error_unwrap_raises(self) -> None:
        with pytest.raises(ValueError, match="Called unwrap on Error"):
            Error("fail").unwrap()

    def test_ok_unwrap_or(self) -> None:
        assert Ok(42).unwrap_or(0) == 42

    def test_error_unwrap_or(self) -> None:
        assert Error("fail").unwrap_or(0) == 0

    def test_ok_is_ok(self) -> None:
        assert Ok(42).is_ok() is True
        assert Ok(42).is_error() is False

    def test_error_is_error(self) -> None:
        assert Error("fail").is_ok() is False
        assert Error("fail").is_error() is True


class TestResultPipeline:
    """Tests for pipeline operator."""

    def test_ok_pipeline_with_raw_return(self) -> None:
        result = Ok(10) >> (lambda x: x * 2)
        assert result.value == 20

    def test_ok_pipeline_with_result_return(self) -> None:
        result = Ok(10) >> (lambda x: Ok(x * 2))
        assert result.value == 20

    def test_ok_pipeline_to_error(self) -> None:
        result = Ok(10) >> (lambda x: Error("failed"))
        assert result.error == "failed"

    def test_error_pipeline_short_circuits(self) -> None:
        result = Error("fail") >> (lambda x: x * 2)
        assert result.error == "fail"

    def test_chained_pipeline(self) -> None:
        result = Ok(5) >> (lambda x: x + 1) >> (lambda x: x * 2)
        assert result.value == 12


class TestResultPatternMatching:
    """Tests for pattern matching."""

    def test_match_ok(self) -> None:
        result = Ok(42)
        match result:
            case Ok(value):
                assert value == 42
            case _:
                pytest.fail("Should match Ok")

    def test_match_error(self) -> None:
        result = Error("failed")
        match result:
            case Error(error):
                assert error == "failed"
            case _:
                pytest.fail("Should match Error")


class TestResultEdgeCases:
    """Tests for Result edge cases."""

    def test_ok_delattr_raises(self) -> None:
        ok = Ok(42)
        with pytest.raises(AttributeError, match="immutable"):
            del ok._value

    def test_ok_eq_with_non_ok(self) -> None:
        ok = Ok(42)
        assert ok.__eq__(42) is False

    def test_ok_unwrap_err_raises(self) -> None:
        ok = Ok(42)
        with pytest.raises(ValueError, match="Called unwrap_err on Ok"):
            ok.unwrap_err()

    def test_error_delattr_raises(self) -> None:
        err = Error("oops")
        with pytest.raises(AttributeError, match="immutable"):
            del err._error

    def test_error_eq_with_non_error(self) -> None:
        err = Error("oops")
        assert err.__eq__("oops") is False


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
        TestOkCreation,
        TestErrorCreation,
        TestResultImmutability,
        TestResultMethods,
        TestResultPipeline,
        TestResultPatternMatching,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
