"""Common functional combinators: identity, const, tap, tee, fmt."""

from typing import Any, Callable, TypeVar

T = TypeVar("T")


def identity(x: T) -> T:
    """Return the input unchanged (pass-through).

    Usage: stream >> identity
    """
    return x


def const(value: T) -> Callable[[Any], T]:
    """Return a function that always returns the given value.

    Usage: input >> const(10)  # returns 10
    """

    def wrapper(_: Any) -> T:
        return value

    return wrapper


def tap(func: Callable[[T], Any]) -> Callable[[T], T]:
    """Execute func(x) for side effect and return x unchanged.

    Usage: Ok(x) >> tap(print)
    """

    def wrapper(x: T) -> T:
        func(x)
        return x

    return wrapper


def tee(func: Callable[[T], Any]) -> Callable[[T], T]:
    """Execute func(x) and return x. Alias for tap.

    Usage: Ok(x) >> tee(log_to_db)
    """

    def wrapper(x: T) -> T:
        func(x)
        return x

    return wrapper


def fmt(template: str) -> Callable[[Any], str]:
    """Format a value into a template string.

    Returns a function that calls template.format(x).

    Usage: Ok("Alice") >> fmt("Hello, {}!")  # Ok("Hello, Alice!")
           compose(_.name, fmt("{}: adult"))
    """

    def wrapper(x: Any) -> str:
        return template.format(x)

    return wrapper
