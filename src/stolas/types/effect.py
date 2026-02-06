"""Effect[T]: Lazy evaluation monad for deferred side effects."""

from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


class Effect(Generic[T]):
    """Wraps a callable for lazy evaluation."""

    __slots__ = ("_thunk",)
    __match_args__ = ("thunk",)
    _thunk: Callable[[], T]

    def __init__(self, thunk: Callable[[], T]) -> None:
        object.__setattr__(self, "_thunk", thunk)

    @property
    def thunk(self) -> Callable[[], T]:
        return self._thunk

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Effect is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Effect is immutable")

    def __repr__(self) -> str:
        return "Effect(<thunk>)"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Effect):
            return NotImplemented
        return self._thunk is other._thunk

    def __hash__(self) -> int:
        return hash(id(self._thunk))

    def __rshift__(self, func: Callable[[T], U]) -> "Effect[U]":
        """Compose without executing."""

        def composed() -> U:
            result = self._thunk()
            if isinstance(result, Effect):
                return func(result.run())
            return func(result)

        return Effect(composed)

    def map(self, func: Callable[[T], U]) -> "Effect[U]":
        """Transform the eventual result T -> U."""

        def mapped() -> U:
            return func(self._thunk())

        return Effect(mapped)

    def bind(self, func: Callable[[T], "Effect[U]"]) -> "Effect[U]":
        """Transform T -> Effect[U], flattening the result."""

        def bound() -> U:
            return func(self._thunk()).run()

        return Effect(bound)

    def run(self) -> T:
        """Execute the effect and return the result."""
        return self._thunk()

    @staticmethod
    def pure(value: T) -> "Effect[T]":
        """Wrap a pure value in an Effect."""
        return Effect(lambda: value)

    @staticmethod
    def defer(func: Callable[..., T], *args: Any, **kwargs: Any) -> "Effect[T]":
        """Create an Effect from a function and its arguments."""
        return Effect(lambda: func(*args, **kwargs))
