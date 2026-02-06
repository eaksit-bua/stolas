"""Option[T]: Null safety monad with Some and Nothing variants."""

from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")

_IMMUTABLE_ERROR = "Option is immutable"


class Some(Generic[T]):
    """Represents presence of a value."""

    __slots__ = ("_value",)
    __match_args__ = ("value",)
    _value: T

    def __init__(self, value: T) -> None:
        object.__setattr__(self, "_value", value)

    @property
    def value(self) -> T:
        return self._value

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(_IMMUTABLE_ERROR)

    def __delattr__(self, name: str) -> None:
        raise AttributeError(_IMMUTABLE_ERROR)

    def __repr__(self) -> str:
        return f"Some({self._value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Some):
            return False
        return bool(self._value == other._value)

    def __hash__(self) -> int:
        return hash(("Some", self._value))

    def __rshift__(self, func: Callable[[T], Any]) -> "Some[Any] | _Nothing":
        result = func(self._value)
        if isinstance(result, (Some, _Nothing)):
            return result
        return Some(result)

    def map(self, func: Callable[[T], U]) -> "Some[U]":
        """Transform inner value T -> U."""
        return Some(func(self._value))

    def bind(self, func: Callable[[T], "Some[U] | _Nothing"]) -> "Some[U] | _Nothing":
        """Transform T -> Option[U]."""
        return func(self._value)

    def unwrap(self) -> T:
        """Return the contained value."""
        return self._value

    def unwrap_or(self, default: T) -> T:
        """Return the contained value (default ignored)."""
        return self._value

    def is_some(self) -> bool:
        return True

    def is_nothing(self) -> bool:
        return False


class _Nothing:
    """Represents absence of a value (singleton)."""

    __slots__ = ()
    __match_args__ = ()

    _instance: "_Nothing | None" = None

    def __new__(cls) -> "_Nothing":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(_IMMUTABLE_ERROR)

    def __delattr__(self, name: str) -> None:
        raise AttributeError(_IMMUTABLE_ERROR)

    def __repr__(self) -> str:
        return "Nothing"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, _Nothing)

    def __hash__(self) -> int:
        return hash("Nothing")

    def __rshift__(self, _func: Callable[[Any], Any]) -> "_Nothing":
        return self

    def map(self, _func: Callable[[Any], Any]) -> "_Nothing":
        """No-op for Nothing, returns self."""
        return self

    def bind(self, _func: Callable[[Any], Any]) -> "_Nothing":
        """No-op for Nothing, returns self."""
        return self

    def unwrap(self) -> Any:
        """Raise exception."""
        raise ValueError("Called unwrap on Nothing")

    def unwrap_or(self, default: T) -> T:
        """Return default value."""
        return default

    def is_some(self) -> bool:
        return False

    def is_nothing(self) -> bool:
        return True


Nothing: _Nothing = _Nothing()

Option = Some[T] | _Nothing
