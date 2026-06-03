"""Generic, composable field validators returning ``Validated`` (errors-as-values).

A *validator* is ``Callable[[T], Validated[T, str]]``: given a value it returns
``Valid(value)`` on success or ``Invalid([message])`` on failure. Validators
**never raise** -- inapplicable input (e.g. ``length()`` on a value with no
``len``) yields ``Invalid([msg])`` rather than letting an exception escape.

The primitives here are deliberately domain-agnostic: there are no
``email``/``url``/``phone`` built-ins. ``rule`` is the base hook and ``matches``
is the documented regex hook for building such recipes.

``all_of`` reuses :func:`stolas.logic.collection.combine_all` to accumulate
results, so the flat-error behavior matches the rest of the framework.
"""

import re
from typing import Any, Callable, Sized

from stolas.logic.collection import combine_all
from stolas.types.validated import Invalid, Valid, Validated

Validator = Callable[[Any], Validated[Any, str]]

__all__ = [
    "Validator",
    "rule",
    "matches",
    "length",
    "between",
    "min_val",
    "max_val",
    "non_empty",
    "one_of",
    "all_of",
    "any_of",
]


def rule(predicate: Callable[[Any], bool], message: str) -> Validator:
    """Build a validator from a ``predicate`` and a failure ``message``.

    The base hook every other primitive is built on. ``predicate`` is called
    inside a guard, so a predicate that raises still yields ``Invalid([message])``
    rather than propagating.

    Usage: ``rule(lambda v: v > 0, "must be positive")``
    """

    def validate(value: Any) -> Validated[Any, str]:
        try:
            ok = predicate(value)
        except Exception:
            ok = False
        if ok:
            return Valid(value)
        return Invalid([message])

    return validate


def matches(pattern: str, message: str | None = None) -> Validator:
    """Validate that a ``str`` value matches ``pattern`` (via :func:`re.search`).

    Non-``str`` values are ``Invalid``. This is the documented hook for
    domain recipes such as email/url validation.

    Usage: ``matches(r"^[^@]+@[^@]+$", "must be an email")``
    """
    default = f"must match pattern {pattern!r}"
    msg = message if message is not None else default

    def validate(value: Any) -> Validated[Any, str]:
        if not isinstance(value, str):
            return Invalid([msg])
        if re.search(pattern, value) is None:
            return Invalid([msg])
        return Valid(value)

    return validate


def length(min: int | None = None, max: int | None = None) -> Validator:
    """Validate ``len(value)`` against inclusive ``min``/``max`` bounds.

    A value with no ``len`` is ``Invalid``. Bounds default to unbounded.

    Usage: ``length(min=1, max=10)``
    """

    def validate(value: Any) -> Validated[Any, str]:
        if not isinstance(value, Sized):
            return Invalid([f"must have a length, got {type(value).__name__}"])
        n = len(value)
        if min is not None and n < min:
            return Invalid([f"length must be at least {min}, got {n}"])
        if max is not None and n > max:
            return Invalid([f"length must be at most {max}, got {n}"])
        return Valid(value)

    return validate


def between(lo: Any, hi: Any) -> Validator:
    """Validate ``lo <= value <= hi`` (inclusive).

    Values that cannot be compared are ``Invalid``.

    Usage: ``between(0, 100)``
    """
    return rule(lambda v: lo <= v <= hi, f"must be between {lo!r} and {hi!r}")


def min_val(n: Any) -> Validator:
    """Validate ``value >= n``.

    Usage: ``min_val(0)``
    """
    return rule(lambda v: v >= n, f"must be at least {n!r}")


def max_val(n: Any) -> Validator:
    """Validate ``value <= n``.

    Usage: ``max_val(100)``
    """
    return rule(lambda v: v <= n, f"must be at most {n!r}")


def non_empty() -> Validator:
    """Validate that ``len(value) > 0``.

    A value with no ``len`` is ``Invalid``.

    Usage: ``non_empty()``
    """

    def validate(value: Any) -> Validated[Any, str]:
        if not isinstance(value, Sized):
            return Invalid([f"must have a length, got {type(value).__name__}"])
        if len(value) == 0:
            return Invalid(["must not be empty"])
        return Valid(value)

    return validate


def one_of(*choices: Any) -> Validator:
    """Validate that ``value`` is one of ``choices``.

    Usage: ``one_of("red", "green", "blue")``
    """
    return rule(lambda v: v in choices, f"must be one of {list(choices)!r}")


def all_of(*validators: Validator) -> Validator:
    """Combine ``validators`` so all must pass (errors accumulate).

    Runs every validator on the value and combines the results via
    :func:`stolas.logic.collection.combine_all`. On success returns
    ``Valid(value)`` (the original value, not the throwaway tuple);
    otherwise ``Invalid`` with every message concatenated flat.

    Usage: ``all_of(non_empty(), length(max=10))``
    """

    def validate(value: Any) -> Validated[Any, str]:
        combined = combine_all(*(v(value) for v in validators))
        if isinstance(combined, Invalid):
            return combined
        return Valid(value)

    return validate


def any_of(*validators: Validator) -> Validator:
    """Combine ``validators`` so at least one must pass.

    Returns ``Valid(value)`` if any validator passes; otherwise ``Invalid``
    with every message concatenated flat.

    Usage: ``any_of(one_of("y", "n"), matches(r"^\\d+$"))``
    """

    def validate(value: Any) -> Validated[Any, str]:
        errors: list[str] = []
        for v in validators:
            result = v(value)
            if isinstance(result, Valid):
                return Valid(value)
            errors.extend(result.errors)
        return Invalid(errors)

    return validate
