"""General utility logic: wrap, when, compose, alt."""

from typing import Any, Callable, TypeVar

from stolas.types.option import Option

T = TypeVar("T")
U = TypeVar("U")


def wrap(cls: type[U]) -> Callable[[Any], U]:
    """Wrap value in class constructor.

    Usage: "data" >> wrap(Box)
    """

    def wrapper(x: Any) -> U:
        return cls(x)  # type: ignore[call-arg]

    return wrapper


def when(
    predicate: Callable[[T], bool],
    then: Callable[[T], U],
    otherwise: Callable[[T], U],
) -> Callable[[T], U]:
    """Conditional execution based on predicate.

    Usage: x >> when(_ > 0, double, half)
    """

    def wrapper(x: T) -> U:
        if predicate(x):
            return then(x)
        return otherwise(x)

    return wrapper


def compose(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose multiple functions left-to-right.

    Usage: f = compose(g, h); f(x) == h(g(x))
    """

    def wrapper(x: Any) -> Any:
        result = x
        for f in funcs:
            result = f(result)
        return result

    return wrapper


def alt(default: T) -> Callable[[Option[T]], T]:
    """Unwrap Option or return default.

    Usage: Nothing >> alt(10)  # 10
           Some(5) >> alt(0)   # 5
    """

    def wrapper(m: Option[T]) -> T:
        return m.unwrap_or(default)

    return wrapper
