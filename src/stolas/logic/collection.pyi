"""Type stubs for collection module."""

from typing import Any, Callable, Iterable, Literal, TypeVar, overload
from stolas.types.effect import Effect
from stolas.types.many import Many
from stolas.types.option import Option, Some
from stolas.types.result import Error, Ok
from stolas.types.validated import Invalid, Valid

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")

def chain(func: Callable[[Any], Iterable[U]]) -> Callable[[Many[Any]], Many[U]]:
    """FlatMap over Many items.

    Works with any function returning Iterable (including Many).
    """
    ...

def where(predicate: Callable[[T], bool]) -> Callable[[Many[T]], Many[T]]:
    """Filter items by predicate."""
    ...

def apply(func: Callable[[T], U]) -> Callable[[Many[T]], Many[U]]:
    """Map function over items."""
    ...

def count() -> Callable[[Many[Any]], Some[int]]:
    """Count items."""
    ...

def first() -> Callable[[Many[T]], Option[T]]:
    """Get first item."""
    ...

def last() -> Callable[[Many[T]], Option[T]]:
    """Get last item."""
    ...

def pair(other: Many[U]) -> Callable[[Many[T]], Many[tuple[T, U]]]:
    """Zip with another Many."""
    ...

def find(predicate: Callable[[T], bool]) -> Callable[[Many[T]], Option[T]]:
    """Find first matching item."""
    ...

@overload
def sort(*, reverse: bool = ...) -> Callable[[Many[Any]], Many[Any]]:
    """Sort items with default key."""
    ...

@overload
def sort(key: Callable[[T], Any], reverse: bool = ...) -> Callable[[Many[T]], Many[T]]:
    """Sort items with custom key."""
    ...

def combine_all(*vs: Any) -> Valid[tuple[Any, ...]] | Invalid[Any]:
    """Combine Validated values into one flat Validated.

    All Valid -> Valid(tuple(values)); any Invalid -> Invalid with all errors
    concatenated flat. Non-Validated -> ValueError.
    """
    ...

@overload
def sequence(
    kind: Literal["result"],
) -> Callable[[Many[Ok[T] | Error[E]]], Ok[Many[T]] | Error[E]]: ...
@overload
def sequence(
    kind: Literal["option"],
) -> Callable[[Many[Option[T]]], Option[Many[T]]]: ...
@overload
def sequence(
    kind: Literal["validated"],
) -> Callable[[Many[Valid[T] | Invalid[E]]], Valid[Many[T]] | Invalid[E]]: ...
@overload
def sequence(
    kind: Literal["effect"],
) -> Callable[[Many[Effect[T]]], Effect[Many[T]]]: ...
@overload
def sequence(kind: None = ...) -> Callable[[Many[Any]], Any]: ...
@overload
def traverse(
    func: Callable[[T], Ok[U] | Error[E]], kind: str | None = ...
) -> Callable[[Many[T]], Ok[Many[U]] | Error[E]]: ...
@overload
def traverse(
    func: Callable[[T], Option[U]], kind: str | None = ...
) -> Callable[[Many[T]], Option[Many[U]]]: ...
@overload
def traverse(
    func: Callable[[T], Valid[U] | Invalid[E]], kind: str | None = ...
) -> Callable[[Many[T]], Valid[Many[U]] | Invalid[E]]: ...
@overload
def traverse(
    func: Callable[[T], Effect[U]], kind: str | None = ...
) -> Callable[[Many[T]], Effect[Many[U]]]: ...
@overload
def traverse(
    func: Callable[[T], Any], kind: str | None = ...
) -> Callable[[Many[T]], Any]: ...
def partition() -> Callable[[Many[Ok[T] | Error[E]]], tuple[Many[T], Many[E]]]:
    """Split Many[Result] into (Many[oks], Many[errors]); non-Result -> ValueError."""
    ...
