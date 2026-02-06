"""Unit tests for Many[T] type."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types import Many, Some, Nothing


class TestManyCreation:
    """Tests for Many creation."""

    def test_creates_many_from_list(self) -> None:
        many = Many([1, 2, 3])
        assert many.items == (1, 2, 3)

    def test_creates_many_from_tuple(self) -> None:
        many = Many((1, 2, 3))
        assert many.items == (1, 2, 3)

    def test_creates_many_from_generator(self) -> None:
        many = Many(x for x in range(3))
        assert many.items == (0, 1, 2)

    def test_many_repr(self) -> None:
        assert repr(Many([1, 2, 3])) == "Many([1, 2, 3])"

    def test_many_equality(self) -> None:
        assert Many([1, 2, 3]) == Many([1, 2, 3])
        assert Many([1, 2, 3]) != Many([1, 2])

    def test_many_hashable(self) -> None:
        assert hash(Many([1, 2])) == hash(Many([1, 2]))
        assert len({Many([1, 2]), Many([1, 2])}) == 1

    def test_many_pure(self) -> None:
        many = Many.pure(42)
        assert many.items == (42,)

    def test_many_empty(self) -> None:
        many = Many.empty()
        assert many.items == ()


class TestManyImmutability:
    """Tests for immutability."""

    def test_many_is_immutable(self) -> None:
        many = Many([1, 2, 3])
        with pytest.raises(AttributeError, match="immutable"):
            many.items = (4, 5, 6)


class TestManyIteration:
    """Tests for iteration support."""

    def test_many_is_iterable(self) -> None:
        many = Many([1, 2, 3])
        assert list(many) == [1, 2, 3]

    def test_many_len(self) -> None:
        many = Many([1, 2, 3])
        assert len(many) == 3

    def test_many_for_loop(self) -> None:
        result = []
        for item in Many([1, 2, 3]):
            result.append(item * 2)
        assert result == [2, 4, 6]


class TestManyMethods:
    """Tests for Many methods."""

    def test_many_map(self) -> None:
        result = Many([1, 2, 3]).map(lambda x: x * 2)
        assert result.items == (2, 4, 6)

    def test_many_bind(self) -> None:
        result = Many([1, 2, 3]).bind(lambda x: Many([x, x * 10]))
        assert result.items == (1, 10, 2, 20, 3, 30)

    def test_many_filter(self) -> None:
        result = Many([1, 2, 3, 4, 5]).filter(lambda x: x % 2 == 0)
        assert result.items == (2, 4)

    def test_many_first(self) -> None:
        assert Many([1, 2, 3]).first() == Some(1)

    def test_many_first_empty(self) -> None:
        assert Many([]).first() == Nothing

    def test_many_last(self) -> None:
        assert Many([1, 2, 3]).last() == Some(3)

    def test_many_last_empty(self) -> None:
        assert Many([]).last() == Nothing

    def test_many_count(self) -> None:
        assert Many([1, 2, 3]).count() == Some(3)

    def test_many_is_empty(self) -> None:
        assert Many([]).is_empty() is True
        assert Many([1]).is_empty() is False


class TestManyPipeline:
    """Tests for pipeline operator."""

    def test_pipeline_applies_to_all(self) -> None:
        result = Many([1, 2, 3]) >> (lambda x: x * 2)
        assert result.items == (2, 4, 6)

    def test_pipeline_flattens_many_results(self) -> None:
        result = Many([1, 2]) >> (lambda x: Many([x, x * 10]))
        assert result.items == (1, 10, 2, 20)

    def test_chained_pipeline(self) -> None:
        result = Many([1, 2, 3]) >> (lambda x: x + 1) >> (lambda x: x * 2)
        assert result.items == (4, 6, 8)

    def test_pipeline_with_filter_chain(self) -> None:
        result = Many([1, 2, 3, 4, 5]).filter(lambda x: x > 2) >> (lambda x: x * 2)
        assert result.items == (6, 8, 10)


class TestManyPatternMatching:
    """Tests for pattern matching."""

    def test_match_many(self) -> None:
        many = Many([1, 2, 3])
        match many:
            case Many(items):
                assert items == (1, 2, 3)
            case _:
                pytest.fail("Should match Many")

    def test_match_empty_many(self) -> None:
        many = Many([])
        match many:
            case Many(items):
                assert items == ()
            case _:
                pytest.fail("Should match Many")


class TestManyComplexOperations:
    """Tests for complex operations."""

    def test_nested_bind(self) -> None:
        result = (
            Many([1, 2])
            .bind(lambda x: Many([x, x + 10]))
            .bind(lambda y: Many([y, y * 100]))
        )
        assert result.items == (1, 100, 11, 1100, 2, 200, 12, 1200)

    def test_map_then_filter(self) -> None:
        result = Many([1, 2, 3, 4]).map(lambda x: x * 2).filter(lambda x: x > 4)
        assert result.items == (6, 8)


class TestManyEdgeCases:
    """Tests for Many edge cases."""

    def test_delattr_raises(self) -> None:
        m = Many([1, 2, 3])
        with pytest.raises(AttributeError, match="immutable"):
            del m._items

    def test_eq_with_non_many(self) -> None:
        m = Many([1, 2, 3])
        result = m.__eq__([1, 2, 3])
        assert result is NotImplemented

    def test_rshift_exception_fallback(self) -> None:
        def item_func(x: int) -> int:
            if isinstance(x, Many):
                raise TypeError("Not for Many")
            return x * 2

        m = Many([1, 2, 3])
        result = m >> item_func
        assert result == Many([2, 4, 6])

    def test_rshift_with_incompatible_function(self) -> None:
        def multiply_by_two(x: int) -> int:
            return x * 2

        m = Many([1, 2, 3])
        result = m >> multiply_by_two
        assert result == Many([2, 4, 6])

    def test_rshift_returns_non_many_result(self) -> None:
        def get_length(m: Many[int]) -> int:
            return len(m)

        m = Many([1, 2, 3])
        result = m >> get_length  # type: ignore[arg-type]
        assert result == 3

    def test_rshift_returns_many_result(self) -> None:
        from stolas.logic import where

        m = Many([1, 2, 3, 4, 5])
        result = m >> where(lambda x: x > 2)
        assert result == Many([3, 4, 5])


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
        TestManyCreation,
        TestManyImmutability,
        TestManyIteration,
        TestManyMethods,
        TestManyPipeline,
        TestManyPatternMatching,
        TestManyComplexOperations,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
