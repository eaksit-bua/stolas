"""Type stubs for collection module."""

from typing import Any, Callable, Iterable, TypeVar, overload
from stolas.types.many import Many
from stolas.types.option import Option, Some

T = TypeVar("T")
U = TypeVar("U")

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

