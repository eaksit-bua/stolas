"""Integration tests: Many Collection Operations.

Tests for `Many` working with all logic functions in complex chains.
Covers Section 7 of the integration test plan.
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types.many import Many
from stolas.types.option import Some, Nothing
from stolas.logic import where, apply, find, sort, chain, both, compose, contains
from stolas.logic.placeholder import _
from stolas.struct import struct


# ── Test domain models ──────────────────────────────────────────────────────


@struct
class User:
    id: int
    name: str
    age: int
    tags: list  # Use unparameterized list for runtime type checking


@struct
class Order:
    id: int
    user_id: int
    items: list  # Use unparameterized list for runtime type checking
    total: float


USERS = Many(
    [
        User(id=1, name="Alice", age=30, tags=["admin", "active"]),
        User(id=2, name="Bob", age=17, tags=["guest"]),
        User(id=3, name="Charlie", age=25, tags=["member", "active"]),
        User(id=4, name="Diana", age=15, tags=["guest"]),
        User(id=5, name="Eve", age=35, tags=["admin", "member"]),
    ]
)

ORDERS = Many(
    [
        Order(id=1, user_id=1, items=["book", "pen"], total=25.0),
        Order(id=2, user_id=1, items=["laptop"], total=999.0),
        Order(id=3, user_id=3, items=["phone", "case"], total=450.0),
    ]
)

NUMBERS = Many([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


# ── Test Classes ────────────────────────────────────────────────────────────


class TestChainedLogicFunctions:
    """Many >> where >> apply >> sort in single pipeline."""

    def test_where_apply_sort_chain(self) -> None:
        """Filter, transform, then sort."""
        result = USERS >> where(_.age >= 18) >> apply(_.name) >> sort()

        assert isinstance(result, Many)
        names = list(result)
        assert names == ["Alice", "Charlie", "Eve"]

    def test_where_apply_chain(self) -> None:
        """Filter then transform."""
        result = USERS >> where(_.age > 20) >> apply(_.age)

        ages = list(result)
        assert ages == [30, 25, 35]

    def test_where_sort_apply(self) -> None:
        """Filter, sort, then transform."""
        result = USERS >> where(_.age >= 18) >> sort(_.age) >> apply(_.name)

        names = list(result)
        assert names == ["Charlie", "Alice", "Eve"]

    def test_multiple_wheres(self) -> None:
        """Multiple where filters chain together."""
        result = USERS >> where(_.age >= 18) >> where(_.age <= 30) >> apply(_.name)

        names = list(result)
        assert set(names) == {"Alice", "Charlie"}

    def test_complex_pipeline_with_numbers(self) -> None:
        """Complex pipeline with integers."""
        result = NUMBERS >> where(_ > 3) >> where(_ < 8) >> apply(_ * 2) >> sort()

        assert list(result) == [8, 10, 12, 14]


class TestChainFlatMap:
    """Many >> chain(_.items) flattens nested iterables."""

    def test_chain_flattens_lists(self) -> None:
        """Chain flattens nested list attributes."""
        result = ORDERS >> chain(_.items)

        items = list(result)
        assert items == ["book", "pen", "laptop", "phone", "case"]

    def test_chain_with_tags(self) -> None:
        """Chain flattens user tags."""
        result = USERS >> chain(_.tags)

        tags = list(result)
        assert "admin" in tags
        assert "guest" in tags
        assert "active" in tags

    def test_chain_then_where(self) -> None:
        """Chain then filter."""
        result = USERS >> chain(_.tags) >> where(_ != "guest")

        tags = list(result)
        assert "guest" not in tags
        assert "admin" in tags

    def test_empty_chain(self) -> None:
        """Chain on empty Many returns empty."""
        empty: Many[User] = Many([])
        result = empty >> chain(_.tags)

        assert list(result) == []


class TestFindReturnsOption:
    """Many >> find(predicate) returns Some/Nothing."""

    def test_find_existing(self) -> None:
        """Find returns Some when element exists."""
        result = USERS >> find(_.name == "Alice")

        assert isinstance(result, Some)
        assert result.value.name == "Alice"

    def test_find_not_existing(self) -> None:
        """Find returns Nothing when element doesn't exist."""
        result = USERS >> find(_.name == "Nobody")

        assert result is Nothing

    def test_find_with_comparison(self) -> None:
        """Find with comparison predicate."""
        result = NUMBERS >> find(_ > 5)

        assert isinstance(result, Some)
        assert result.value == 6  # First > 5

    def test_find_first_match(self) -> None:
        """Find returns first matching element."""
        result = USERS >> find(_.age >= 18)

        assert isinstance(result, Some)
        assert result.value.name == "Alice"  # First adult


class TestEmptyManyHandling:
    """All operations handle empty Many([]) gracefully."""

    def test_empty_where(self) -> None:
        """Where on empty Many returns empty."""
        empty: Many[int] = Many([])
        result = empty >> where(_ > 0)

        assert list(result) == []

    def test_empty_apply(self) -> None:
        """Apply on empty Many returns empty."""
        empty: Many[int] = Many([])
        result = empty >> apply(_ * 2)

        assert list(result) == []

    def test_empty_sort(self) -> None:
        """Sort on empty Many returns empty."""
        empty: Many[int] = Many([])
        result = empty >> sort()

        assert list(result) == []

    def test_empty_find(self) -> None:
        """Find on empty Many returns Nothing."""
        empty: Many[int] = Many([])
        result = empty >> find(_ > 0)

        assert result is Nothing

    def test_empty_chain(self) -> None:
        """Chain on empty Many returns empty."""
        empty: Many[list[int]] = Many([])
        result = empty >> chain(_)

        assert list(result) == []

    def test_where_to_empty(self) -> None:
        """Where that filters everything returns empty."""
        result = NUMBERS >> where(_ > 100)

        assert list(result) == []


class TestManyWithStructs:
    """Many of @struct objects with complex attribute access."""

    def test_nested_attribute_access(self) -> None:
        """Access nested/complex attributes."""
        result = USERS >> where(_.age >= 18) >> apply(_.id)

        ids = list(result)
        assert ids == [1, 3, 5]

    def test_struct_in_pipeline(self) -> None:
        """Full pipeline with struct transformations."""
        # Get names of users with "admin" tag
        result = USERS >> where(compose(_.tags, contains("admin"))) >> apply(_.name)

        names = list(result)
        assert set(names) == {"Alice", "Eve"}

    def test_sort_by_struct_attribute(self) -> None:
        """Sort by struct attribute."""
        result = USERS >> sort(_.age) >> apply(_.name)

        names = list(result)
        assert names[0] == "Diana"  # Youngest
        assert names[-1] == "Eve"  # Oldest

    def test_sort_reverse_by_attribute(self) -> None:
        """Sort in reverse order."""
        result = USERS >> sort(_.age, reverse=True) >> apply(_.name)

        names = list(result)
        assert names[0] == "Eve"  # Oldest first


class TestManyWithBoth:
    """Test Many with both() for parallel predicates."""

    def test_both_predicates(self) -> None:
        """Both predicates must be true."""
        result = USERS >> where(both(_.age >= 18, _.age <= 30))

        users = list(result)
        names = [u.name for u in users]
        assert set(names) == {"Alice", "Charlie"}

    def test_both_with_negative_result(self) -> None:
        """Both predicates impossible to satisfy."""
        result = USERS >> where(both(_.age < 10, _.age > 50))

        assert list(result) == []


class TestManyComplexPipelines:
    """Complex real-world pipeline scenarios."""

    def test_aggregation_pattern(self) -> None:
        """Filter, transform, collect pattern."""
        # Get total of orders for users over 18
        adult_user_ids = set(list(USERS >> where(_.age >= 18) >> apply(_.id)))

        adult_orders = (
            ORDERS
            >> where(compose(_.user_id, adult_user_ids.__contains__))
            >> apply(_.total)
        )

        totals = list(adult_orders)
        assert sum(totals) == 25.0 + 999.0 + 450.0

    def test_join_like_operation(self) -> None:
        """Join-like operation between two Many collections."""
        # Find users who have orders
        user_ids_with_orders = set(list(ORDERS >> apply(_.user_id)))

        users_with_orders = (
            USERS
            >> where(compose(_.id, user_ids_with_orders.__contains__))
            >> apply(_.name)
        )

        names = list(users_with_orders)
        assert set(names) == {"Alice", "Charlie"}

    def test_group_by_pattern(self) -> None:
        """Group-by like pattern (manual)."""
        adults = USERS >> where(_.age >= 18)
        minors = USERS >> where(_.age < 18)

        adult_names = list(adults >> apply(_.name))
        minor_names = list(minors >> apply(_.name))

        assert set(adult_names) == {"Alice", "Charlie", "Eve"}
        assert set(minor_names) == {"Bob", "Diana"}
