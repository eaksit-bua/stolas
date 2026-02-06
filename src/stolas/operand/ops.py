"""Ops decorator: composer for stacking multiple decorators."""

from functools import reduce
from typing import Any, Callable, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def ops(
    *decorators: Callable[[Any], Any],
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Compose multiple decorators into a single decorator.

    Usage:
        @ops(binary, as_result)
        def my_func(a, b): ...

    This means:
        1. Apply @binary first (function becomes curried)
        2. Apply @as_result to the result (wraps in Ok/Error)

    The decorators are applied in the ORDER you read them:
    - Left = applied to the raw function first
    - Right = wraps the result of the previous decorator

    ops(d1, d2)(f) -> d2(d1(f))
    """

    def apply_decorators(func: Callable[P, R]) -> Callable[P, R]:
        # Apply decorators left-to-right (first decorator in list is innermost)
        # This matches the user's mental model: "do d1, then apply d2 to result"
        return reduce(lambda f, d: d(f), decorators, func)

    return apply_decorators
