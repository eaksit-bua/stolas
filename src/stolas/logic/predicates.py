"""Predicate combinators for functional pipelines."""

from typing import Any, Callable


def contains(item: Any) -> Callable[[Any], bool]:
    """Check if item is contained in the input.

    Returns a function that checks membership using Python's 'in' operator.

    Args:
        item: The item to search for

    Returns:
        A function that takes a container and returns True if item is in it

    Example:
        >>> from stolas.logic import contains
        >>> from stolas.types import Many
        >>> emails = Many(["alice@example.com", "bob@example.com", "invalid"])
        >>> valid = emails >> where(contains("@"))
        >>> valid.items
        ('alice@example.com', 'bob@example.com')
    """

    def check(container: Any) -> bool:
        return bool(item in container)

    return check


def negate(predicate: Callable[[Any], Any]) -> Callable[[Any], bool]:
    """Negate a predicate function.

    Returns a function that returns the logical NOT of the predicate result.

    Args:
        predicate: A callable that returns a truthy/falsy value

    Returns:
        A function that returns True when predicate returns falsy, and vice versa

    Example:
        >>> from stolas.logic import negate, contains
        >>> is_missing_at = negate(contains("@"))
        >>> is_missing_at("alice@test.com")
        False
        >>> is_missing_at("invalid")
        True
    """

    def check(x: Any) -> bool:
        return not predicate(x)

    return check


def both(*predicates: Callable[[Any], Any]) -> Callable[[Any], bool]:
    """Combine predicates with logical AND.

    Returns a function that returns True only when all predicates return truthy.

    Args:
        *predicates: One or more callable predicates

    Returns:
        A function that returns True when all predicates pass

    Example:
        >>> from stolas.logic import both
        >>> in_range = both(lambda x: x > 0, lambda x: x < 10)
        >>> in_range(5)
        True
        >>> in_range(15)
        False
    """

    def check(x: Any) -> bool:
        return all(p(x) for p in predicates)

    return check


def either(*predicates: Callable[[Any], Any]) -> Callable[[Any], bool]:
    """Combine predicates with logical OR.

    Returns a function that returns True when any predicate returns truthy.

    Args:
        *predicates: One or more callable predicates

    Returns:
        A function that returns True when at least one predicate passes

    Example:
        >>> from stolas.logic import either
        >>> extreme = either(lambda x: x > 100, lambda x: x < -100)
        >>> extreme(150)
        True
        >>> extreme(50)
        False
    """

    def check(x: Any) -> bool:
        return any(p(x) for p in predicates)

    return check
