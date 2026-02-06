"""Integration tests: all logic functions work with placeholder _ syntax."""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.logic import (
    apply,
    both,
    chain,
    check,
    compose,
    const,
    contains,
    either,
    find,
    fmt,
    negate,
    sort,
    tap,
    tee,
    when,
    where,
)
from stolas.logic.placeholder import _
from stolas.struct import struct
from stolas.types.many import Many
from stolas.types.option import Nothing, Some
from stolas.types.result import Error, Ok


@struct
class User:
    id: int
    name: str
    age: int


@struct
class Order:
    id: int
    item: str
    tags: list


USERS = Many(
    [
        User(id=1, name="Alice", age=30),
        User(id=2, name="Bob", age=17),
        User(id=3, name="Charlie", age=25),
        User(id=4, name="Diana", age=15),
        User(id=5, name="Eve", age=35),
    ]
)

NUMBERS = Many([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


class TestWherePlaceholder:
    """where() supports _ placeholder as predicate."""

    def test_comparison_gt(self) -> None:
        result = NUMBERS >> where(_ > 5)
        assert result.items == (6, 7, 8, 9, 10)

    def test_comparison_lt(self) -> None:
        result = NUMBERS >> where(_ < 4)
        assert result.items == (1, 2, 3)

    def test_comparison_ge(self) -> None:
        result = NUMBERS >> where(_ >= 10)
        assert result.items == (10,)

    def test_comparison_le(self) -> None:
        result = NUMBERS >> where(_ <= 2)
        assert result.items == (1, 2)

    def test_comparison_eq(self) -> None:
        result = NUMBERS >> where(_ == 5)
        assert result.items == (5,)

    def test_comparison_ne(self) -> None:
        result = Many([1, 2, 3]) >> where(_ != 2)
        assert result.items == (1, 3)

    def test_arithmetic_expression(self) -> None:
        result = NUMBERS >> where(_ % 2 == 0)
        assert result.items == (2, 4, 6, 8, 10)

    def test_attribute_comparison(self) -> None:
        result = USERS >> where(_.age >= 18)
        assert result.items == (
            User(id=1, name="Alice", age=30),
            User(id=3, name="Charlie", age=25),
            User(id=5, name="Eve", age=35),
        )


class TestApplyPlaceholder:
    """apply() supports _ placeholder as transform function."""

    def test_arithmetic(self) -> None:
        result = NUMBERS >> apply(_ * 2)
        assert result.items == (2, 4, 6, 8, 10, 12, 14, 16, 18, 20)

    def test_attribute_access(self) -> None:
        result = USERS >> apply(_.name)
        assert result.items == ("Alice", "Bob", "Charlie", "Diana", "Eve")

    def test_attribute_with_arithmetic(self) -> None:
        result = USERS >> apply(_.age + 1)
        assert result.items == (31, 18, 26, 16, 36)

    def test_method_call(self) -> None:
        result = USERS >> apply(_.name.upper())
        assert result.items == ("ALICE", "BOB", "CHARLIE", "DIANA", "EVE")

    def test_chained_method_on_attribute(self) -> None:
        result = USERS >> apply(_.name.lower())
        assert result.items == ("alice", "bob", "charlie", "diana", "eve")


class TestFindPlaceholder:
    """find() supports _ placeholder as predicate."""

    def test_equality(self) -> None:
        result = find(_ == 5)(NUMBERS)
        assert isinstance(result, Some)
        assert result.value == 5

    def test_comparison(self) -> None:
        result = find(_ > 8)(NUMBERS)
        assert isinstance(result, Some)
        assert result.value == 9

    def test_attribute_comparison(self) -> None:
        result = find(_.name == "Charlie")(USERS)
        assert isinstance(result, Some)
        assert result.value == User(id=3, name="Charlie", age=25)

    def test_not_found(self) -> None:
        result = find(_ > 100)(NUMBERS)
        assert result is Nothing


class TestSortPlaceholder:
    """sort() supports _ placeholder as key function."""

    def test_sort_by_attribute(self) -> None:
        result = USERS >> sort(key=_.age)
        assert result.items == (
            User(id=4, name="Diana", age=15),
            User(id=2, name="Bob", age=17),
            User(id=3, name="Charlie", age=25),
            User(id=1, name="Alice", age=30),
            User(id=5, name="Eve", age=35),
        )

    def test_sort_by_attribute_reversed(self) -> None:
        result = USERS >> sort(key=_.age, reverse=True)
        assert result.items[0] == User(id=5, name="Eve", age=35)
        assert result.items[-1] == User(id=4, name="Diana", age=15)

    def test_sort_by_name(self) -> None:
        result = USERS >> sort(key=_.name)
        names = tuple(u.name for u in result.items)
        assert names == ("Alice", "Bob", "Charlie", "Diana", "Eve")


class TestChainPlaceholder:
    """chain() supports _ placeholder as mapping function."""

    def test_attribute_returning_iterable(self) -> None:
        orders = Many(
            [
                Order(id=1, item="Book", tags=["fiction", "sale"]),
                Order(id=2, item="Pen", tags=["office"]),
            ]
        )
        result = orders >> chain(_.tags)
        assert result.items == ("fiction", "sale", "office")


class TestCheckPlaceholder:
    """check() supports _ placeholder as predicate."""

    def test_passes_validation(self) -> None:
        result = check(_ > 0, "Must be positive")(10)
        assert isinstance(result, Ok)
        assert result.value == 10

    def test_fails_validation(self) -> None:
        result = check(_ > 0, "Must be positive")(-5)
        assert isinstance(result, Error)
        assert result.error == "Must be positive"

    def test_attribute_validation(self) -> None:
        result = check(_.age >= 18, "Must be adult")(User(id=1, name="Alice", age=30))
        assert isinstance(result, Ok)

    def test_attribute_validation_fails(self) -> None:
        result = check(_.age >= 18, "Must be adult")(User(id=2, name="Bob", age=17))
        assert isinstance(result, Error)


class TestWhenPlaceholder:
    """when() supports _ placeholder for predicate, then, and otherwise."""

    def test_predicate_with_placeholder(self) -> None:
        classify = when(_ >= 18, const("adult"), const("minor"))
        assert classify(20) == "adult"
        assert classify(15) == "minor"

    def test_all_branches_with_placeholder(self) -> None:
        double_or_negate = when(_ > 0, _ * 2, _ * -1)
        assert double_or_negate(5) == 10
        assert double_or_negate(-3) == 3

    def test_attribute_predicate(self) -> None:
        label = when(
            _.age >= 18,
            compose(_.name, fmt("{}: adult")),
            compose(_.name, fmt("{}: minor")),
        )
        assert label(User(id=1, name="Alice", age=30)) == "Alice: adult"
        assert label(User(id=2, name="Bob", age=17)) == "Bob: minor"


class TestComposePlaceholder:
    """compose() supports _ placeholder as individual functions."""

    def test_compose_arithmetic(self) -> None:
        transform = compose(_ + 1, _ * 2)
        assert transform(5) == 12  # (5 + 1) * 2

    def test_compose_three_steps(self) -> None:
        transform = compose(_ * 2, _ + 10, _ // 3)
        assert transform(5) == 6  # ((5 * 2) + 10) // 3 = 20 // 3 = 6


class TestTapPlaceholder:
    """tap() supports _ placeholder as side-effect function."""

    def test_tap_with_placeholder_expression(self) -> None:
        result = tap(_ * 2)(10)
        assert result == 10  # tap returns the original value

    def test_tap_with_attribute_access(self) -> None:
        result = tap(_.name)(User(id=1, name="Alice", age=30))
        assert result.name == "Alice"  # tap returns the original value


class TestTeePlaceholder:
    """tee() supports _ placeholder as side-effect function."""

    def test_tee_with_placeholder_expression(self) -> None:
        result = tee(_ + 100)(5)
        assert result == 5  # tee returns the original value

    def test_tee_with_attribute_access(self) -> None:
        user = User(id=1, name="Bob", age=25)
        result = tee(_.age)(user)
        assert result is user  # tee returns the original value


class TestContainsWithWhere:
    """contains() works as predicate with where()."""

    def test_contains_in_pipeline(self) -> None:
        emails = Many(["alice@test.com", "bob_at_test", "eve@test.com"])
        result = emails >> where(contains("@"))
        assert result.items == ("alice@test.com", "eve@test.com")


class TestNegateWithPlaceholder:
    """negate() works with placeholder expressions."""

    def test_negate_comparison(self) -> None:
        result = NUMBERS >> where(negate(_ > 5))
        assert result.items == (1, 2, 3, 4, 5)

    def test_negate_contains(self) -> None:
        emails = Many(["alice@test.com", "bob_at_test", "eve@test.com"])
        result = emails >> where(negate(contains("@")))
        assert result.items == ("bob_at_test",)

    def test_negate_modulo(self) -> None:
        result = NUMBERS >> where(negate(_ % 2 == 0))
        assert result.items == (1, 3, 5, 7, 9)

    def test_negate_attribute(self) -> None:
        result = USERS >> where(negate(_.age >= 18))
        assert result.items == (
            User(id=2, name="Bob", age=17),
            User(id=4, name="Diana", age=15),
        )


class TestBothWithPlaceholder:
    """both() works with placeholder expressions."""

    def test_both_comparisons(self) -> None:
        result = NUMBERS >> where(both(_ > 0, _ < 10))
        assert result.items == (1, 2, 3, 4, 5, 6, 7, 8, 9)

    def test_both_narrow_range(self) -> None:
        result = NUMBERS >> where(both(_ > 3, _ < 7))
        assert result.items == (4, 5, 6)

    def test_both_with_attributes(self) -> None:
        result = USERS >> where(both(_.age >= 18, _.age < 35))
        assert result.items == (
            User(id=1, name="Alice", age=30),
            User(id=3, name="Charlie", age=25),
        )

    def test_both_three_predicates(self) -> None:
        result = NUMBERS >> where(both(_ > 1, _ < 10, _ % 2 == 0))
        assert result.items == (2, 4, 6, 8)


class TestEitherWithPlaceholder:
    """either() works with placeholder expressions."""

    def test_either_comparisons(self) -> None:
        result = NUMBERS >> where(either(_ > 8, _ < 3))
        assert result.items == (1, 2, 9, 10)

    def test_either_with_contains(self) -> None:
        data = Many(["hello", "world", "hi", "hey"])
        result = data >> where(either(contains("llo"), contains("ey")))
        assert result.items == ("hello", "hey")

    def test_either_with_attributes(self) -> None:
        result = USERS >> where(either(_.age < 16, _.age > 30))
        assert result.items == (
            User(id=4, name="Diana", age=15),
            User(id=5, name="Eve", age=35),
        )

    def test_either_three_predicates(self) -> None:
        result = NUMBERS >> where(either(_ == 1, _ == 5, _ == 10))
        assert result.items == (1, 5, 10)


class TestPipelinePlaceholderEndToEnd:
    """End-to-end pipeline tests combining multiple functions with _."""

    def test_filter_transform_pipeline(self) -> None:
        result = USERS >> where(_.age >= 18) >> apply(_.name) >> sort()
        assert result.items == ("Alice", "Charlie", "Eve")

    def test_filter_find_pipeline(self) -> None:
        result = USERS >> where(_.age >= 18)
        found = find(_.name == "Charlie")(result)
        assert isinstance(found, Some)
        assert found.value.age == 25

    def test_numbers_pipeline(self) -> None:
        result = NUMBERS >> where(_ % 2 == 0) >> apply(_**2)
        assert result.items == (4, 16, 36, 64, 100)

    def test_chained_where(self) -> None:
        result = USERS >> where(_.age >= 18) >> where(_.age < 35)
        assert result.items == (
            User(id=1, name="Alice", age=30),
            User(id=3, name="Charlie", age=25),
        )

    def test_sort_then_apply(self) -> None:
        result = USERS >> sort(key=_.age) >> apply(_.name)
        assert result.items == ("Diana", "Bob", "Charlie", "Alice", "Eve")

    def test_full_pipeline(self) -> None:
        result = (
            USERS >> where(_.age >= 18) >> sort(key=_.name) >> apply(_.name.upper())
        )
        assert result.items == ("ALICE", "CHARLIE", "EVE")

    def test_both_in_pipeline(self) -> None:
        result = (
            USERS
            >> where(both(_.age >= 18, _.age <= 30))
            >> sort(key=_.name)
            >> apply(_.name)
        )
        assert result.items == ("Alice", "Charlie")

    def test_either_in_pipeline(self) -> None:
        result = USERS >> where(either(_.age < 16, _.age > 30)) >> apply(_.name)
        assert result.items == ("Diana", "Eve")

    def test_negate_in_pipeline(self) -> None:
        result = USERS >> where(negate(_.age >= 18)) >> apply(_.name) >> sort()
        assert result.items == ("Bob", "Diana")

    def test_combined_predicates_pipeline(self) -> None:
        result = (
            NUMBERS >> where(both(negate(_ > 8), either(_ % 2 == 0, _ == 1))) >> sort()
        )
        assert result.items == (1, 2, 4, 6, 8)
