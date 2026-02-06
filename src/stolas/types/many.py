"""Many[T]: Collection monad for iterable operations."""

from typing import TYPE_CHECKING, Any, Callable, Generic, Iterable, Iterator, TypeVar

if TYPE_CHECKING:
    from stolas.types.option import Option, Some

T = TypeVar("T")
U = TypeVar("U")


class Many(Generic[T]):
    """Wraps an iterable collection for chainable operations."""

    __slots__ = ("_items",)
    __match_args__ = ("items",)
    _items: tuple[T, ...]

    def __init__(self, items: Iterable[T]) -> None:
        object.__setattr__(self, "_items", tuple(items))

    @property
    def items(self) -> tuple[T, ...]:
        return self._items

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Many is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Many is immutable")

    def __repr__(self) -> str:
        return f"Many({list(self._items)!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Many):
            return NotImplemented
        return self._items == other._items

    def __hash__(self) -> int:
        return hash(("Many", self._items))

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __rshift__(self, func: Callable[[T], U]) -> "Many[U]":
        """Bind operator for chaining operations.

        Supports two modes:
        1. Collection functions: Many([1,2,3]) >> where(_ > 1)  # func takes Many
        2. Map functions: Many([1,2,3]) >> (lambda x: x * 2)     # func takes items
        """
        # Try calling with self first (for collection functions like where, apply)
        try:
            result = func(self)  # type: ignore[arg-type]
            # If it returns a Many, we're done
            if isinstance(result, Many):
                return result
            # If it returns something else, it might be a collection function
            # that doesn't return Many (like count, first, etc.)
            # In that case, just return it wrapped
            return result  # type: ignore[return-value]
        except (TypeError, AttributeError):
            # If that fails, treat it as a map function (operates on each item)
            results: list[U] = []
            for item in self._items:
                result = func(item)
                if isinstance(result, Many):
                    results.extend(result._items)
                else:
                    results.append(result)
            return Many(results)

    def map(self, func: Callable[[T], U]) -> "Many[U]":
        """Transform each element T -> U."""
        return Many(func(item) for item in self._items)

    def bind(self, func: Callable[[T], "Many[U]"]) -> "Many[U]":
        """Transform T -> Many[U] and flatten."""
        results: list[U] = []
        for item in self._items:
            results.extend(func(item)._items)
        return Many(results)

    def filter(self, predicate: Callable[[T], bool]) -> "Many[T]":
        """Keep only elements matching predicate."""
        return Many(item for item in self._items if predicate(item))

    def first(self) -> "Option[T]":
        """Return first element as Some, or Nothing if empty."""
        from stolas.types.option import Nothing, Some

        if self._items:
            return Some(self._items[0])
        return Nothing

    def last(self) -> "Option[T]":
        """Return last element as Some, or Nothing if empty."""
        from stolas.types.option import Nothing, Some

        if self._items:
            return Some(self._items[-1])
        return Nothing

    def count(self) -> "Some[int]":
        """Return count of elements wrapped in Some."""
        from stolas.types.option import Some

        return Some(len(self._items))

    def is_empty(self) -> bool:
        """Check if the collection is empty."""
        return len(self._items) == 0

    @classmethod
    def pure(cls, value: T) -> "Many[T]":
        """Wrap a single value in Many."""
        return cls([value])

    @classmethod
    def empty(cls) -> "Many[T]":
        """Create an empty Many."""
        return cls([])
