"""Collection helpers: chain, where, apply, count, first, last, pair, find, sort."""

from typing import Any, Callable, Iterable, TypeVar

from stolas.types.many import Many
from stolas.types.option import Nothing, Option, Some

T = TypeVar("T")
U = TypeVar("U")


def chain(
    func: Callable[[T], Iterable[U]] | Callable[[T], Many[U]],
) -> Callable[[Many[T]], Many[U]]:
    """FlatMap helper: maps function over Many items and flattens result.

    Usage: Many(...) >> chain(_.sub_items)
    """

    def wrapper(m: Many[T]) -> Many[U]:
        results: list[U] = []
        for x in m._items:
            res = func(x)
            if isinstance(res, Many):
                results.extend(res.items)
            elif isinstance(res, Iterable):
                results.extend(res)
            else:
                raise TypeError(f"Expected Iterable or Many, got {type(res)}")
        return Many(tuple(results))

    return wrapper


def where(predicate: Callable[[T], bool]) -> Callable[[Many[T]], Many[T]]:
    """Filter helper: keeps items matching predicate.

    Usage: Many(...) >> where(_ > 10)
    """

    def wrapper(m: Many[T]) -> Many[T]:
        return Many(tuple(x for x in m._items if predicate(x)))

    return wrapper


def apply(func: Callable[[T], U]) -> Callable[[Many[T]], Many[U]]:
    """Map helper: applies function to each item.

    Usage: Many(...) >> apply(_.upper())
    """

    def wrapper(m: Many[T]) -> Many[U]:
        return Many(tuple(func(x) for x in m._items))

    return wrapper


def count() -> Callable[[Many[T]], Some[int]]:
    """Return count of items wrapped in Some.

    Usage: Many(...) >> count()  # returns Some(N)
    """

    def wrapper(m: Many[T]) -> Some[int]:
        return Some(len(m._items))

    return wrapper


def first() -> Callable[[Many[T]], Option[T]]:
    """Return first item as Some, or Nothing if empty.

    Usage: Many(...) >> first()  # returns Some(x) or Nothing
    """

    def wrapper(m: Many[T]) -> Option[T]:
        if m._items:
            return Some(m._items[0])
        return Nothing

    return wrapper


def last() -> Callable[[Many[T]], Option[T]]:
    """Return last item as Some, or Nothing if empty.

    Usage: Many(...) >> last()  # returns Some(x) or Nothing
    """

    def wrapper(m: Many[T]) -> Option[T]:
        if m._items:
            return Some(m._items[-1])
        return Nothing

    return wrapper


def pair(other: Many[U]) -> Callable[[Many[T]], Many[tuple[T, U]]]:
    """Zip with another Many collection.

    Usage: Many([1,2]) >> pair(Many(['a','b']))  # Many([(1,'a'), (2,'b')])
    """

    def wrapper(m: Many[T]) -> Many[tuple[T, U]]:
        return Many(tuple(zip(m._items, other._items)))

    return wrapper


def find(predicate: Callable[[T], bool]) -> Callable[[Many[T]], Option[T]]:
    """Find first item matching predicate.

    Usage: Many(...) >> find(_ == 5)  # returns Some(5) or Nothing
    """

    def wrapper(m: Many[T]) -> Option[T]:
        for x in m._items:
            if predicate(x):
                return Some(x)
        return Nothing

    return wrapper


def sort(
    key: Callable[[T], Any] | None = None, reverse: bool = False
) -> Callable[[Many[T]], Many[T]]:
    """Return sorted Many.

    Usage: Many(...) >> sort(key=_.age)
    """

    def wrapper(m: Many[T]) -> Many[T]:
        return Many(tuple(sorted(m._items, key=key, reverse=reverse)))  # type: ignore[arg-type,type-var]

    return wrapper
