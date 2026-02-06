"""Flow control helpers: check, strict."""

from typing import Any, Callable, TypeVar

from stolas.types.result import Error, Ok

T = TypeVar("T")


def check(
    predicate: Callable[[T], bool], error_msg: str
) -> Callable[[T], Ok[T] | Error[str]]:
    """Validate value with predicate, return Ok or Error.

    Usage: Ok(val) >> check(_ > 0, "must be positive")
    """

    def wrapper(x: T) -> Ok[T] | Error[str]:
        if predicate(x):
            return Ok(x)
        return Error(error_msg)

    return wrapper


def strict(type_: type[T]) -> Callable[[Any], Ok[T] | Error[TypeError]]:
    """Validate that value is instance of type, return Ok or Error.

    Usage: Ok(val) >> strict(int)
    """

    def wrapper(x: Any) -> Ok[T] | Error[TypeError]:
        if isinstance(x, type_):
            return Ok(x)
        return Error(TypeError(f"Expected {type_.__name__}, got {type(x).__name__}"))

    return wrapper
