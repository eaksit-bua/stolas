"""Result[T, E]: Error handling monad with Ok and Error variants."""

from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
F = TypeVar("F")

_IMMUTABLE_ERROR = "Result is immutable"


class Ok(Generic[T]):
    """Represents a successful result containing a value."""

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
        return f"Ok({self._value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Ok):
            return False
        return bool(self._value == other._value)

    def __hash__(self) -> int:
        return hash(("Ok", self._value))

    def __rshift__(self, func: Callable[[T], Any]) -> "Ok[Any] | Error[Any]":
        result = func(self._value)
        if isinstance(result, (Ok, Error)):
            return result
        return Ok(result)

    def map(self, func: Callable[[T], U]) -> "Ok[U]":
        """Transform inner value T -> U."""
        return Ok(func(self._value))

    def map_err(self, func: Callable[[Any], Any]) -> "Ok[T]":
        """No-op for Ok, returns self."""
        return self

    def bind(self, func: Callable[[T], "Ok[U] | Error[E]"]) -> "Ok[U] | Error[E]":
        """Transform T -> Result[U, E]."""
        return func(self._value)

    def unwrap(self) -> T:
        """Return the contained value."""
        return self._value

    def unwrap_or(self, default: T) -> T:
        """Return the contained value (default ignored)."""
        return self._value

    def unwrap_err(self) -> Any:
        """Raise exception with value."""
        raise ValueError(f"Called unwrap_err on Ok: {self._value}")

    def is_ok(self) -> bool:
        return True

    def is_error(self) -> bool:
        return False


class Error(Generic[E]):
    """Represents a failed result containing an error."""

    __slots__ = ("_error",)
    __match_args__ = ("error",)
    _error: E

    def __init__(self, error: E) -> None:
        object.__setattr__(self, "_error", error)

    @property
    def error(self) -> E:
        return self._error

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(_IMMUTABLE_ERROR)

    def __delattr__(self, name: str) -> None:
        raise AttributeError(_IMMUTABLE_ERROR)

    def __repr__(self) -> str:
        return f"Error({self._error!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Error):
            return False
        return bool(self._error == other._error)

    def __hash__(self) -> int:
        return hash(("Error", self._error))

    def __rshift__(self, func: Callable[[Any], Any]) -> "Error[E]":
        return self

    def map(self, func: Callable[[Any], Any]) -> "Error[E]":
        """No-op for Error, returns self."""
        return self

    def map_err(self, func: Callable[[E], F]) -> "Error[F]":
        """Transform inner error E -> F."""
        return Error(func(self._error))

    def bind(self, func: Callable[[Any], Any]) -> "Error[E]":
        """No-op for Error, returns self."""
        return self

    def unwrap(self) -> Any:
        """Raise exception with error value."""
        raise ValueError(f"Called unwrap on Error: {self._error}")

    def unwrap_or(self, default: T) -> T:
        """Return default value."""
        return default

    def unwrap_err(self) -> E:
        """Return the contained error."""
        return self._error

    def is_ok(self) -> bool:
        return False

    def is_error(self) -> bool:
        return True


Result = Ok[T] | Error[E]
