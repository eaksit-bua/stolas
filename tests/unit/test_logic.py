"""Unit tests for logic module: common, access, flow, collection, utils."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.logic import (
    alt,
    apply,
    at,
    both,
    call,
    chain,
    check,
    compose,
    const,
    contains,
    count,
    either,
    find,
    first,
    fmt,
    get,
    identity,
    last,
    negate,
    pair,
    sort,
    strict,
    tap,
    tee,
    when,
    where,
    wrap,
)
from stolas.types.many import Many
from stolas.types.option import Nothing, Some
from stolas.types.result import Error, Ok


class TestIdentityFunction:
    """Tests for identity function."""

    def test_returns_input_unchanged(self) -> None:
        assert identity(42) == 42

    def test_returns_string_unchanged(self) -> None:
        assert identity("hello") == "hello"

    def test_returns_none_unchanged(self) -> None:
        assert identity(None) is None

    def test_returns_object_unchanged(self) -> None:
        obj = {"key": "value"}
        assert identity(obj) is obj


class TestConstFunction:
    """Tests for const function."""

    def test_always_returns_constant_value(self) -> None:
        always_five = const(5)
        assert always_five(1) == 5
        assert always_five("anything") == 5
        assert always_five(None) == 5

    def test_ignores_input_argument(self) -> None:
        always_hello = const("hello")
        assert always_hello(999) == "hello"

    def test_returns_same_object_reference(self) -> None:
        obj = {"data": 1}
        always_obj = const(obj)
        assert always_obj(None) is obj


class TestTapFunction:
    """Tests for tap function."""

    def test_returns_input_unchanged(self) -> None:
        result = tap(lambda x: None)(42)
        assert result == 42

    def test_executes_side_effect(self) -> None:
        captured: list[int] = []
        tap(lambda x: captured.append(x))(10)
        assert captured == [10]

    def test_ignores_function_return_value(self) -> None:
        result = tap(lambda x: x * 100)(5)
        assert result == 5


class TestTeeFunction:
    """Tests for tee function."""

    def test_returns_input_unchanged(self) -> None:
        result = tee(lambda x: None)(42)
        assert result == 42

    def test_executes_side_effect(self) -> None:
        captured: list[int] = []
        tee(lambda x: captured.append(x))(10)
        assert captured == [10]

    def test_behaves_like_tap(self) -> None:
        result = tee(lambda x: x * 100)(5)
        assert result == 5


class TestGetAccessor:
    """Tests for get accessor function."""

    def test_gets_attribute_from_object(self) -> None:
        class Person:
            def __init__(self, name: str) -> None:
                self.name = name

        person = Person("Alice")
        assert get("name")(person) == "Alice"

    def test_raises_on_missing_attribute(self) -> None:
        class Empty:
            pass

        with pytest.raises(AttributeError):
            get("missing")(Empty())


class TestAtAccessor:
    """Tests for at accessor function."""

    def test_gets_dict_value_by_key(self) -> None:
        data = {"id": 123, "name": "test"}
        assert at("id")(data) == 123

    def test_gets_list_item_by_index(self) -> None:
        items = ["a", "b", "c"]
        assert at(0)(items) == "a"
        assert at(-1)(items) == "c"

    def test_raises_on_missing_key(self) -> None:
        data = {"a": 1}
        with pytest.raises(KeyError):
            at("missing")(data)

    def test_raises_on_out_of_range_index(self) -> None:
        items = [1, 2]
        with pytest.raises(IndexError):
            at(10)(items)


class TestCallAccessor:
    """Tests for call accessor function."""

    def test_calls_method_without_args(self) -> None:
        result = call("upper")("hello")
        assert result == "HELLO"

    def test_calls_method_with_args(self) -> None:
        result = call("replace", "a", "b")("banana")
        assert result == "bbnbnb"

    def test_calls_method_with_kwargs(self) -> None:
        result = call("split", sep=",")("a,b,c")
        assert result == ["a", "b", "c"]

    def test_raises_on_missing_method(self) -> None:
        with pytest.raises(AttributeError):
            call("nonexistent")("string")


class TestCheckFunction:
    """Tests for check validation function."""

    def test_returns_ok_when_predicate_passes(self) -> None:
        result = check(lambda x: x > 0, "Must be positive")(10)
        assert isinstance(result, Ok)
        assert result.unwrap() == 10

    def test_returns_error_when_predicate_fails(self) -> None:
        result = check(lambda x: x > 0, "Must be positive")(-5)
        assert isinstance(result, Error)
        assert result.unwrap_err() == "Must be positive"

    def test_works_with_complex_predicate(self) -> None:
        def is_even(x: int) -> bool:
            return x % 2 == 0

        assert isinstance(check(is_even, "Not even")(4), Ok)
        assert isinstance(check(is_even, "Not even")(3), Error)


class TestStrictFunction:
    """Tests for strict type validation function."""

    def test_returns_ok_for_correct_type(self) -> None:
        result = strict(int)(42)
        assert isinstance(result, Ok)
        assert result.unwrap() == 42

    def test_returns_error_for_wrong_type(self) -> None:
        result = strict(int)("not an int")
        assert isinstance(result, Error)
        err = result.unwrap_err()
        assert isinstance(err, TypeError)
        assert "Expected int" in str(err)

    def test_validates_string_type(self) -> None:
        assert isinstance(strict(str)("hello"), Ok)
        assert isinstance(strict(str)(123), Error)

    def test_validates_list_type(self) -> None:
        assert isinstance(strict(list)([1, 2, 3]), Ok)
        assert isinstance(strict(list)((1, 2, 3)), Error)


class TestChainFunction:
    """Tests for chain (flatmap) function."""

    def test_flattens_many_results(self) -> None:
        m = Many([1, 2, 3])
        result = chain(lambda x: Many([x, x * 10]))(m)
        assert result.items == (1, 10, 2, 20, 3, 30)

    def test_handles_empty_many(self) -> None:
        m = Many([])
        result = chain(lambda x: Many([x, x]))(m)
        assert result.items == ()

    def test_handles_list_return(self) -> None:
        m = Many([1, 2])
        result = chain(lambda x: [x, x + 1])(m)
        assert result.items == (1, 2, 2, 3)

    def test_raises_type_error_for_non_iterable(self) -> None:
        def bad_func(x: int) -> int:
            return x * 2  # Returns int, not Iterable

        wrapper = chain(bad_func)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Expected Iterable or Many"):
            wrapper(Many([1, 2, 3]))


class TestWhereFunction:
    """Tests for where (filter) function."""

    def test_filters_by_predicate(self) -> None:
        m = Many([1, 2, 3, 4, 5])
        result = where(lambda x: x > 2)(m)
        assert result.items == (3, 4, 5)

    def test_returns_empty_when_none_match(self) -> None:
        m = Many([1, 2, 3])
        result = where(lambda x: x > 10)(m)
        assert result.items == ()

    def test_returns_all_when_all_match(self) -> None:
        m = Many([2, 4, 6])
        result = where(lambda x: x % 2 == 0)(m)
        assert result.items == (2, 4, 6)


class TestApplyFunction:
    """Tests for apply (map) function."""

    def test_maps_function_over_items(self) -> None:
        m = Many([1, 2, 3])
        result = apply(lambda x: x * 2)(m)
        assert result.items == (2, 4, 6)

    def test_handles_empty_many(self) -> None:
        m = Many([])
        result = apply(lambda x: x * 2)(m)
        assert result.items == ()

    def test_works_with_string_methods(self) -> None:
        m = Many(["a", "b", "c"])
        result = apply(str.upper)(m)
        assert result.items == ("A", "B", "C")


class TestCountFunction:
    """Tests for count function."""

    def test_returns_count_as_some(self) -> None:
        m = Many([1, 2, 3])
        result = count()(m)
        assert isinstance(result, Some)
        assert result.value == 3

    def test_returns_zero_for_empty(self) -> None:
        m = Many([])
        result = count()(m)
        assert result.value == 0


class TestFirstFunction:
    """Tests for first function."""

    def test_returns_some_first_item(self) -> None:
        m = Many([1, 2, 3])
        result = first()(m)
        assert isinstance(result, Some)
        assert result.value == 1

    def test_returns_nothing_for_empty(self) -> None:
        m = Many([])
        result = first()(m)
        assert result is Nothing


class TestLastFunction:
    """Tests for last function."""

    def test_returns_some_last_item(self) -> None:
        m = Many([1, 2, 3])
        result = last()(m)
        assert isinstance(result, Some)
        assert result.value == 3

    def test_returns_nothing_for_empty(self) -> None:
        m = Many([])
        result = last()(m)
        assert result is Nothing


class TestPairFunction:
    """Tests for pair (zip) function."""

    def test_zips_two_manys(self) -> None:
        m1 = Many([1, 2, 3])
        m2 = Many(["a", "b", "c"])
        result = pair(m2)(m1)
        assert result.items == ((1, "a"), (2, "b"), (3, "c"))

    def test_truncates_to_shorter(self) -> None:
        m1 = Many([1, 2, 3, 4])
        m2 = Many(["a", "b"])
        result = pair(m2)(m1)
        assert result.items == ((1, "a"), (2, "b"))


class TestFindFunction:
    """Tests for find function."""

    def test_returns_some_when_found(self) -> None:
        m = Many([1, 2, 3, 4, 5])
        result = find(lambda x: x == 3)(m)
        assert isinstance(result, Some)
        assert result.value == 3

    def test_returns_first_match(self) -> None:
        m = Many([1, 2, 3, 4, 5])
        result = find(lambda x: x > 2)(m)
        assert isinstance(result, Some)
        assert result.value == 3

    def test_returns_nothing_when_not_found(self) -> None:
        m = Many([1, 2, 3])
        result = find(lambda x: x > 10)(m)
        assert result is Nothing

    def test_returns_nothing_for_empty(self) -> None:
        m = Many([])
        result = find(lambda x: x == 1)(m)
        assert result is Nothing


class TestSortFunction:
    """Tests for sort function."""

    def test_sorts_ascending_by_default(self) -> None:
        m = Many([3, 1, 4, 1, 5, 9, 2, 6])
        result = sort()(m)
        assert result.items == (1, 1, 2, 3, 4, 5, 6, 9)

    def test_sorts_descending_with_reverse(self) -> None:
        m = Many([3, 1, 4, 1, 5])
        result = sort(reverse=True)(m)
        assert result.items == (5, 4, 3, 1, 1)

    def test_sorts_with_key_function(self) -> None:
        m = Many(["bb", "aaa", "c"])
        result = sort(key=len)(m)
        assert result.items == ("c", "bb", "aaa")

    def test_sorts_with_key_and_reverse(self) -> None:
        m = Many(["bb", "aaa", "c"])
        result = sort(key=len, reverse=True)(m)
        assert result.items == ("aaa", "bb", "c")

    def test_handles_empty_many(self) -> None:
        m = Many([])
        result = sort()(m)
        assert result.items == ()


class TestWrapFunction:
    """Tests for wrap function."""

    def test_wraps_in_class(self) -> None:
        result = wrap(Some)(42)
        assert isinstance(result, Some)
        assert result.value == 42

    def test_wraps_in_list(self) -> None:
        result = wrap(list)("abc")
        assert result == ["a", "b", "c"]


class TestWhenFunction:
    """Tests for when (conditional) function."""

    def test_executes_then_when_true(self) -> None:
        result = when(
            lambda x: x > 0,
            lambda x: x * 2,
            lambda x: x * -1,
        )(5)
        assert result == 10

    def test_executes_otherwise_when_false(self) -> None:
        result = when(
            lambda x: x > 0,
            lambda x: x * 2,
            lambda x: x * -1,
        )(-5)
        assert result == 5


class TestComposeFunction:
    """Tests for compose function."""

    def test_composes_left_to_right(self) -> None:
        def add_one(x: int) -> int:
            return x + 1

        def double(x: int) -> int:
            return x * 2

        result = compose(add_one, double)(5)
        assert result == 12  # (5 + 1) * 2

    def test_single_function(self) -> None:
        def double(x: int) -> int:
            return x * 2

        result = compose(double)(5)
        assert result == 10

    def test_three_functions(self) -> None:
        result = compose(
            lambda x: x + 1,
            lambda x: x * 2,
            lambda x: x - 3,
        )(5)
        assert result == 9  # ((5 + 1) * 2) - 3


class TestAltFunction:
    """Tests for alt (unwrap with default) function."""

    def test_returns_value_for_some(self) -> None:
        result = alt(0)(Some(42))
        assert result == 42

    def test_returns_default_for_nothing(self) -> None:
        result = alt(0)(Nothing)
        assert result == 0


class TestContainsFunction:
    """Tests for contains predicate function."""

    def test_returns_true_when_item_in_string(self) -> None:
        assert contains("@")("alice@test.com") is True

    def test_returns_false_when_item_not_in_string(self) -> None:
        assert contains("@")("invalid") is False

    def test_returns_true_when_item_in_list(self) -> None:
        assert contains(3)([1, 2, 3, 4]) is True

    def test_returns_false_when_item_not_in_list(self) -> None:
        assert contains(5)([1, 2, 3, 4]) is False

    def test_works_with_dict_keys(self) -> None:
        assert contains("a")({"a": 1, "b": 2}) is True
        assert contains("c")({"a": 1, "b": 2}) is False

    def test_works_with_tuple(self) -> None:
        assert contains(2)((1, 2, 3)) is True

    def test_works_with_set(self) -> None:
        assert contains("x")({"x", "y", "z"}) is True
        assert contains("w")({"x", "y", "z"}) is False


class TestNegateFunction:
    """Tests for negate predicate combinator."""

    def test_negates_true_to_false(self) -> None:
        def always_true(x):
            return True

        assert negate(always_true)(42) is False

    def test_negates_false_to_true(self) -> None:
        def always_false(x):
            return False

        assert negate(always_false)(42) is True

    def test_negates_comparison(self) -> None:
        def is_positive(x):
            return x > 0

        is_not_positive = negate(is_positive)
        assert is_not_positive(-5) is True
        assert is_not_positive(5) is False
        assert is_not_positive(0) is True

    def test_negates_contains(self) -> None:
        has_at = contains("@")
        missing_at = negate(has_at)
        assert missing_at("alice@test.com") is False
        assert missing_at("invalid") is True

    def test_negates_truthy_values(self) -> None:
        assert negate(lambda x: x)(0) is True
        assert negate(lambda x: x)(1) is False
        assert negate(lambda x: x)("") is True
        assert negate(lambda x: x)("hello") is False


class TestBothFunction:
    """Tests for both predicate combinator."""

    def test_true_when_all_pass(self) -> None:
        def is_positive(x):
            return x > 0

        def is_even(x):
            return x % 2 == 0

        assert both(is_positive, is_even)(4) is True

    def test_false_when_first_fails(self) -> None:
        def is_positive(x):
            return x > 0

        def is_even(x):
            return x % 2 == 0

        assert both(is_positive, is_even)(-2) is False

    def test_false_when_second_fails(self) -> None:
        def is_positive(x):
            return x > 0

        def is_even(x):
            return x % 2 == 0

        assert both(is_positive, is_even)(3) is False

    def test_false_when_all_fail(self) -> None:
        def is_positive(x):
            return x > 0

        def is_even(x):
            return x % 2 == 0

        assert both(is_positive, is_even)(-3) is False

    def test_works_with_single_predicate(self) -> None:
        assert both(lambda x: x > 0)(5) is True
        assert both(lambda x: x > 0)(-5) is False

    def test_works_with_three_predicates(self) -> None:
        result = both(
            lambda x: x > 0,
            lambda x: x < 100,
            lambda x: x % 2 == 0,
        )(50)
        assert result is True
        assert (
            both(
                lambda x: x > 0,
                lambda x: x < 100,
                lambda x: x % 2 == 0,
            )(51)
            is False
        )

    def test_short_circuits(self) -> None:
        call_count = 0

        def counting_pred(x: int) -> bool:
            nonlocal call_count
            call_count += 1
            return x > 0

        both(lambda x: False, counting_pred)(5)
        assert call_count == 0


class TestEitherFunction:
    """Tests for either predicate combinator."""

    def test_true_when_first_passes(self) -> None:
        assert either(lambda x: x > 10, lambda x: x < 0)(15) is True

    def test_true_when_second_passes(self) -> None:
        assert either(lambda x: x > 10, lambda x: x < 0)(-5) is True

    def test_true_when_all_pass(self) -> None:
        assert either(lambda x: x > 0, lambda x: x < 10)(5) is True

    def test_false_when_none_pass(self) -> None:
        assert either(lambda x: x > 10, lambda x: x < 0)(5) is False

    def test_works_with_single_predicate(self) -> None:
        assert either(lambda x: x > 0)(5) is True
        assert either(lambda x: x > 0)(-5) is False

    def test_works_with_three_predicates(self) -> None:
        is_extreme = either(
            lambda x: x > 100,
            lambda x: x < -100,
            lambda x: x == 0,
        )
        assert is_extreme(150) is True
        assert is_extreme(-150) is True
        assert is_extreme(0) is True
        assert is_extreme(50) is False

    def test_short_circuits(self) -> None:
        call_count = 0

        def counting_pred(x: int) -> bool:
            nonlocal call_count
            call_count += 1
            return x > 0

        either(lambda x: True, counting_pred)(5)
        assert call_count == 0


class TestFmtFunction:
    """Tests for fmt string formatting helper."""

    def test_basic_formatting(self) -> None:
        assert fmt("Hello, {}!")("World") == "Hello, World!"

    def test_number_formatting(self) -> None:
        assert fmt("Value: {}")(42) == "Value: 42"

    def test_empty_template(self) -> None:
        assert fmt("{}")("test") == "test"

    def test_with_prefix_and_suffix(self) -> None:
        assert fmt("[{}]")("item") == "[item]"

    def test_returns_callable(self) -> None:
        formatter = fmt("x={}")
        assert callable(formatter)
        assert formatter(1) == "x=1"
        assert formatter(2) == "x=2"


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
        TestIdentityFunction,
        TestConstFunction,
        TestTapFunction,
        TestTeeFunction,
        TestGetAccessor,
        TestAtAccessor,
        TestCallAccessor,
        TestCheckFunction,
        TestStrictFunction,
        TestChainFunction,
        TestWhereFunction,
        TestApplyFunction,
        TestCountFunction,
        TestFirstFunction,
        TestLastFunction,
        TestPairFunction,
        TestFindFunction,
        TestSortFunction,
        TestWrapFunction,
        TestWhenFunction,
        TestComposeFunction,
        TestAltFunction,
        TestContainsFunction,
        TestNegateFunction,
        TestBothFunction,
        TestEitherFunction,
        TestFmtFunction,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
