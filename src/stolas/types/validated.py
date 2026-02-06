"""Validated[T, E]: Error accumulation monad with Valid and Invalid variants."""

from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")

_IMMUTABLE_ERROR = "Validated is immutable"


class Valid(Generic[T]):
    """Represents valid data containing a value."""

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
        return f"Valid({self._value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Valid):
            return False
        return bool(self._value == other._value)

    def __hash__(self) -> int:
        return hash(("Valid", self._value))

    def __rshift__(self, func: Callable[[T], Any]) -> "Valid[Any] | Invalid[Any]":
        result = func(self._value)
        if isinstance(result, (Valid, Invalid)):
            return result
        return Valid(result)

    def map(self, func: Callable[[T], U]) -> "Valid[U]":
        """Transform inner value T -> U."""
        return Valid(func(self._value))

    def is_valid(self) -> bool:
        return True

    def is_invalid(self) -> bool:
        return False

    def combine(
        self, other: "Valid[U] | Invalid[E]"
    ) -> "Valid[tuple[T, U]] | Invalid[E]":
        """Combine with another Validated."""
        if isinstance(other, Invalid):
            return other
        return Valid((self._value, other._value))


class Invalid(Generic[E]):
    """Represents invalid data containing accumulated errors."""

    __slots__ = ("_errors",)
    __match_args__ = ("errors",)
    _errors: tuple[E, ...]

    def __init__(self, errors: list[E] | E) -> None:
        if isinstance(errors, list):
            object.__setattr__(self, "_errors", tuple(errors))
        else:
            object.__setattr__(self, "_errors", (errors,))

    @property
    def errors(self) -> tuple[E, ...]:
        return self._errors

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(_IMMUTABLE_ERROR)

    def __delattr__(self, name: str) -> None:
        raise AttributeError(_IMMUTABLE_ERROR)

    def __repr__(self) -> str:
        return f"Invalid({list(self._errors)!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Invalid):
            return False
        return self._errors == other._errors

    def __hash__(self) -> int:
        return hash(("Invalid", self._errors))

    def __rshift__(self, func: Callable[[Any], Any]) -> "Invalid[E]":
        return self

    def map(self, func: Callable[[Any], Any]) -> "Invalid[E]":
        """No-op for Invalid, returns self."""
        return self

    def is_valid(self) -> bool:
        return False

    def is_invalid(self) -> bool:
        return True

    def combine(self, other: "Valid[Any] | Invalid[E]") -> "Invalid[E]":
        """Combine errors with another Validated."""
        if isinstance(other, Invalid):
            return Invalid(list(self._errors) + list(other._errors))
        return self


Validated = Valid[T] | Invalid[E]
