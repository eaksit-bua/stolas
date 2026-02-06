"""Type stubs for safe wrapper decorators."""

from typing import TypeVar, Callable, ParamSpec
from stolas.types import Result, Option, Validated, Many, Effect

_T = TypeVar("_T")
_E = TypeVar("_E", bound=Exception)
_P = ParamSpec("_P")

# @as_result: wraps function to return Result[T, Exception]
# Works with both regular and curried functions
def as_result(func: Callable[_P, _T]) -> Callable[_P, Result[_T, Exception]]: ...

# @as_option: wraps function to return Option[T]
def as_option(func: Callable[_P, _T | None]) -> Callable[_P, Option[_T]]: ...

# @as_validated: wraps function to return Validated[T, str]
def as_validated(func: Callable[_P, _T]) -> Callable[_P, Validated[_T, str]]: ...

# @as_many: wraps function to return Many[T]
def as_many(func: Callable[_P, list[_T]]) -> Callable[_P, Many[_T]]: ...

# @as_effect: wraps function to return Effect[None]
def as_effect(func: Callable[_P, None]) -> Callable[_P, Effect[None]]: ...
