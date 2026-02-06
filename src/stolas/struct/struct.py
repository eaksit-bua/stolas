"""@struct: C/Rust-like immutable struct with fixed memory layout."""

from typing import Any, TypeVar, cast, get_type_hints

T = TypeVar("T")


def _get_field_value(key: str, kwargs: dict[str, Any], defaults: dict[str, Any]) -> Any:
    """Get field value from kwargs or defaults."""
    if key in kwargs:
        return kwargs[key]
    if key in defaults:
        return defaults[key]
    raise TypeError(f"Missing required field: {key}")


def _validate_type(key: str, value: Any, expected_type: type) -> None:
    """Validate that value matches expected type."""
    if expected_type is Any:
        return
    if not isinstance(value, expected_type):
        raise TypeError(
            f"Field '{key}' expects {expected_type.__name__}, got {type(value).__name__}"
        )


def _validate_fields(
    kwargs: dict[str, Any], slots: tuple[str, ...], defaults: dict[str, Any]
) -> None:
    """Validate that no unknown fields are passed."""
    extra = set(kwargs) - set(slots)
    if extra:
        raise TypeError(f"Unknown fields: {extra}")

    missing = set(slots) - set(kwargs) - set(defaults)
    if missing:
        raise TypeError(f"Missing required fields: {missing}")


def _make_init(
    slots: tuple[str, ...], defaults: dict[str, Any], annotations: dict[str, type]
) -> Any:
    """Create __init__ method for struct."""

    def __init__(self: Any, **kwargs: Any) -> None:
        _validate_fields(kwargs, slots, defaults)
        for key in slots:
            value = _get_field_value(key, kwargs, defaults)
            _validate_type(key, value, annotations[key])
            object.__setattr__(self, key, value)

    return __init__


def _make_setattr() -> Any:
    """Create __setattr__ that blocks mutation."""

    def __setattr__(self: Any, name: str, value: Any) -> None:
        raise AttributeError("Struct is immutable")

    return __setattr__


def _make_delattr() -> Any:
    """Create __delattr__ that blocks deletion."""

    def __delattr__(self: Any, name: str) -> None:
        raise AttributeError("Struct is immutable")

    return __delattr__


def _make_repr(cls_name: str, slots: tuple[str, ...]) -> Any:
    """Create __repr__ method."""

    def __repr__(self: Any) -> str:
        fields = ", ".join(f"{k}={getattr(self, k)!r}" for k in slots)
        return f"{cls_name}({fields})"

    return __repr__


def _make_eq(slots: tuple[str, ...]) -> Any:
    """Create __eq__ method."""

    def __eq__(self: Any, other: Any) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in slots)

    return __eq__


def _make_hash(slots: tuple[str, ...]) -> Any:
    """Create __hash__ method."""

    def __hash__(self: Any) -> int:
        return hash(tuple(getattr(self, k) for k in slots))

    return __hash__


def _make_rshift() -> Any:
    """Create __rshift__ for pipeline operator."""

    def __rshift__(self: Any, other: Any) -> Any:
        return other(self)

    return __rshift__


def _make_init_subclass() -> Any:
    """Create __init_subclass__ that blocks inheritance."""

    def __init_subclass__(cls: type, /, **kwargs: Any) -> None:
        raise TypeError("Cannot inherit from struct")

    return classmethod(__init_subclass__)


def struct(cls: type[T]) -> type[T]:
    """Decorator that creates an immutable struct with fixed memory layout."""
    annotations = get_type_hints(cls) if hasattr(cls, "__annotations__") else {}
    slots = tuple(annotations.keys())
    defaults = {k: getattr(cls, k) for k in slots if hasattr(cls, k)}

    new_cls = cast(
        type[T],
        type(
            cls.__name__,
            (),
            {
                "__slots__": slots,
                "__annotations__": annotations,
                "__match_args__": slots,
                "__init__": _make_init(slots, defaults, annotations),
                "__setattr__": _make_setattr(),
                "__delattr__": _make_delattr(),
                "__repr__": _make_repr(cls.__name__, slots),
                "__eq__": _make_eq(slots),
                "__hash__": _make_hash(slots),
                "__rshift__": _make_rshift(),
                "__init_subclass__": _make_init_subclass(),
                "__module__": cls.__module__,
            },
        ),
    )

    return new_cls
