"""Unit tests for Option[T] type."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types import Some, Nothing


class TestSomeCreation:
    """Tests for Some variant creation."""

    def test_creates_some_with_value(self) -> None:
        option = Some(42)
        assert option.value == 42

    def test_some_repr(self) -> None:
        assert repr(Some(42)) == "Some(42)"

    def test_some_equality(self) -> None:
        assert Some(42) == Some(42)
        assert Some(42) != Some(99)

    def test_some_hashable(self) -> None:
        assert hash(Some(42)) == hash(Some(42))
        assert len({Some(42), Some(42)}) == 1


class TestNothingCreation:
    """Tests for Nothing singleton."""

    def test_nothing_is_singleton(self) -> None:
        from stolas.types.option import _Nothing

        assert Nothing is _Nothing()

    def test_nothing_repr(self) -> None:
        assert repr(Nothing) == "Nothing"

    def test_nothing_equality(self) -> None:
        from stolas.types.option import _Nothing

        assert Nothing == _Nothing()

    def test_nothing_hashable(self) -> None:
        assert len({Nothing, Nothing}) == 1


class TestOptionImmutability:
    """Tests for immutability."""

    def test_some_is_immutable(self) -> None:
        option = Some(42)
        with pytest.raises(AttributeError, match="immutable"):
            option.value = 99

    def test_nothing_is_immutable(self) -> None:
        with pytest.raises(AttributeError, match="immutable"):
            Nothing.value = 99


class TestOptionMethods:
    """Tests for Option methods."""

    def test_some_map(self) -> None:
        result = Some(10).map(lambda x: x * 2)
        assert result.value == 20

    def test_nothing_map_noop(self) -> None:
        result = Nothing.map(lambda x: x * 2)
        assert result is Nothing

    def test_some_bind(self) -> None:
        result = Some(10).bind(lambda x: Some(x * 2))
        assert result.value == 20

    def test_some_bind_to_nothing(self) -> None:
        result = Some(10).bind(lambda x: Nothing)
        assert result is Nothing

    def test_nothing_bind_noop(self) -> None:
        result = Nothing.bind(lambda x: Some(x * 2))
        assert result is Nothing

    def test_some_unwrap(self) -> None:
        assert Some(42).unwrap() == 42

    def test_nothing_unwrap_raises(self) -> None:
        with pytest.raises(ValueError, match="Called unwrap on Nothing"):
            Nothing.unwrap()

    def test_some_unwrap_or(self) -> None:
        assert Some(42).unwrap_or(0) == 42

    def test_nothing_unwrap_or(self) -> None:
        assert Nothing.unwrap_or(0) == 0

    def test_some_is_some(self) -> None:
        assert Some(42).is_some() is True
        assert Some(42).is_nothing() is False

    def test_nothing_is_nothing(self) -> None:
        assert Nothing.is_some() is False
        assert Nothing.is_nothing() is True


class TestOptionPipeline:
    """Tests for pipeline operator."""

    def test_some_pipeline_with_raw_return(self) -> None:
        result = Some(10) >> (lambda x: x * 2)
        assert result.value == 20

    def test_some_pipeline_with_option_return(self) -> None:
        result = Some(10) >> (lambda x: Some(x * 2))
        assert result.value == 20

    def test_some_pipeline_to_nothing(self) -> None:
        result = Some(10) >> (lambda x: Nothing)
        assert result is Nothing

    def test_nothing_pipeline_short_circuits(self) -> None:
        result = Nothing >> (lambda x: x * 2)
        assert result is Nothing

    def test_chained_pipeline(self) -> None:
        result = Some(5) >> (lambda x: x + 1) >> (lambda x: x * 2)
        assert result.value == 12


class TestOptionPatternMatching:
    """Tests for pattern matching."""

    def test_match_some(self) -> None:
        option = Some(42)
        match option:
            case Some(value):
                assert value == 42
            case _:
                pytest.fail("Should match Some")

    def test_match_nothing(self) -> None:
        match Nothing:
            case Some(_):
                pytest.fail("Should not match Some")
            case _:
                pass  # Expected


class TestOptionEdgeCases:
    """Tests for Option edge cases."""

    def test_some_delattr_raises(self) -> None:
        s = Some(42)
        with pytest.raises(AttributeError, match="immutable"):
            del s._value

    def test_some_eq_with_non_some(self) -> None:
        s = Some(42)
        assert s.__eq__(42) is False

    def test_nothing_delattr_raises(self) -> None:
        with pytest.raises(AttributeError, match="immutable"):
            del Nothing._instance  # type: ignore[attr-defined]


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
        TestSomeCreation,
        TestNothingCreation,
        TestOptionImmutability,
        TestOptionMethods,
        TestOptionPipeline,
        TestOptionPatternMatching,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
