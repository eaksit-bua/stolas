"""Safe Wrappers: Convert exception-raising functions into Monadic return types."""

import functools
from typing import Any, Callable, Iterable, ParamSpec, TypeVar

from stolas.types.effect import Effect
from stolas.types.many import Many
from stolas.types.option import Nothing, Some, _Nothing
from stolas.types.result import Error, Ok
from stolas.types.validated import Invalid, Valid

P = ParamSpec("P")
T = TypeVar("T")


def as_result(
    func: Callable[P, T],
) -> Callable[P, Ok[T] | Error[Exception]]:
    """Wrap function to return Result[T, Exception].

    Success: Returns Ok(value).
    Failure: Caught exception returns Error(e).

    When applied to a Curried function, wraps the final execution result.
    """
    # Import here to avoid circular import
    from stolas.operand.arity import Curried

    # If wrapping a Curried function, wrap its underlying function
    if isinstance(func, Curried):
        original_func = func._func

        def wrapped_func(*args: Any, **kwargs: Any) -> Ok[Any] | Error[Exception]:
            try:
                return Ok(original_func(*args, **kwargs))
            except Exception as e:
                return Error(e)

        return Curried(wrapped_func, func._arity, func._accumulated)  # type: ignore[return-value]

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Ok[T] | Error[Exception]:
        try:
            return Ok(func(*args, **kwargs))
        except Exception as e:
            return Error(e)

    return wrapper


def as_option(
    func: Callable[P, T | None],
) -> Callable[P, Some[T] | _Nothing]:
    """Wrap function to return Option[T].

    If returns None -> Nothing.
    If returns value -> Some(value).
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Some[T] | _Nothing:
        result = func(*args, **kwargs)
        if result is None:
            return Nothing
        return Some(result)

    return wrapper


def as_validated(
    func: Callable[P, T],
) -> Callable[P, Valid[T] | Invalid[Exception]]:
    """Wrap function to return Validated[T, Exception].

    Success: Returns Valid(value).
    Failure: Caught exception returns Invalid([e]).
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Valid[T] | Invalid[Exception]:
        try:
            return Valid(func(*args, **kwargs))
        except Exception as e:
            return Invalid(e)

    return wrapper


def as_many(
    func: Callable[P, Iterable[T]],
) -> Callable[P, Many[T]]:
    """Wrap function to return Many[T].

    Takes function returning Iterable[T] or list[T].
    Returns Many(items).
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Many[T]:
        return Many(func(*args, **kwargs))

    return wrapper


def as_effect(
    func: Callable[P, T],
) -> Callable[P, Effect[T]]:
    """Wrap function to return Effect[T].

    Captures function call as a thunk.
    Execution deferred until .run() is called.

    When applied to a Curried function, wraps the final execution in Effect.
    """
    # Import here to avoid circular import
    from stolas.operand.arity import Curried

    # If wrapping a Curried function, wrap its underlying function
    if isinstance(func, Curried):
        original_func = func._func

        def wrapped_func(*args: Any, **kwargs: Any) -> Effect[Any]:
            return Effect(lambda: original_func(*args, **kwargs))

        return Curried(wrapped_func, func._arity, func._accumulated)  # type: ignore[return-value]

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Effect[T]:
        return Effect(lambda: func(*args, **kwargs))

    return wrapper
