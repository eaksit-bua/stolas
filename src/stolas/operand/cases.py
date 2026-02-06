"""@cases: Sealed variants (ADTs) comparable to Rust enums."""

from typing import Any, Union, get_type_hints


def _is_unit_variant(variant_type: type) -> bool:
    """Check if variant should be a unit (singleton) variant."""
    return variant_type is type(None)


def _is_existing_class(variant_type: type) -> bool:
    """Check if variant type is an existing class to alias."""
    return (
        isinstance(variant_type, type)
        and variant_type is not type(None)
        and not _is_any_type(variant_type)
    )


def _is_any_type(variant_type: type) -> bool:
    """Check if variant type is Any."""
    return str(variant_type) == "typing.Any"


def _create_value_variant(name: str, parent_name: str) -> type:
    """Create a value variant class (wrapper with single value)."""

    def __init__(self: Any, value: Any) -> None:
        object.__setattr__(self, "_value", value)

    def __setattr__(self: Any, attr: str, val: Any) -> None:
        raise AttributeError(f"{name} is immutable")

    def __delattr__(self: Any, attr: str) -> None:
        raise AttributeError(f"{name} is immutable")

    def __repr__(self: Any) -> str:
        return f"{parent_name}.{name}({self._value!r})"

    def __eq__(self: Any, other: Any) -> bool:
        if type(self) is not type(other):
            return False
        return bool(self._value == other._value)

    def __hash__(self: Any) -> int:
        return hash((name, self._value))

    def __rshift__(self: Any, func: Any) -> Any:
        return func(self._value)

    def _get_value(self: Any) -> Any:
        return self._value

    return type(
        name,
        (),
        {
            "__slots__": ("_value",),
            "__annotations__": {"_value": Any},
            "__match_args__": ("value",),
            "__init__": __init__,
            "__setattr__": __setattr__,
            "__delattr__": __delattr__,
            "__repr__": __repr__,
            "__eq__": __eq__,
            "__hash__": __hash__,
            "__rshift__": __rshift__,
            "value": property(_get_value),
        },
    )


def _create_unit_variant(name: str, parent_name: str) -> type:
    """Create a unit variant class (singleton)."""

    def __new__(cls: type) -> Any:
        if not hasattr(cls, "_instance"):
            cls._instance = object.__new__(cls)  # type: ignore[attr-defined]
        return cls._instance  # type: ignore[attr-defined]

    def __setattr__(self: Any, attr: str, val: Any) -> None:
        raise AttributeError(f"{name} is immutable")

    def __delattr__(self: Any, attr: str) -> None:
        raise AttributeError(f"{name} is immutable")

    def __repr__(self: Any) -> str:
        return f"{parent_name}.{name}"

    def __eq__(self: Any, other: Any) -> bool:
        return type(self) is type(other)

    def __hash__(self: Any) -> int:
        return hash(name)

    def __rshift__(self: Any, func: Any) -> Any:
        return self

    return type(
        name,
        (),
        {
            "__slots__": (),
            "__match_args__": (),
            "__new__": __new__,
            "__setattr__": __setattr__,
            "__delattr__": __delattr__,
            "__repr__": __repr__,
            "__eq__": __eq__,
            "__hash__": __hash__,
            "__rshift__": __rshift__,
        },
    )


def _create_variant(
    name: str, variant_type: type, parent_name: str
) -> tuple[type, bool]:
    """Create appropriate variant class based on type annotation."""
    if _is_unit_variant(variant_type):
        return _create_unit_variant(name, parent_name), True
    if _is_existing_class(variant_type):
        return variant_type, False
    return _create_value_variant(name, parent_name), False


def cases(cls: type) -> type:
    """Decorator to create sealed variants (ADTs)."""
    annotations = get_type_hints(cls) if hasattr(cls, "__annotations__") else {}
    variants: dict[str, type] = {}
    variant_types: list[type] = []

    for name, variant_type in annotations.items():
        variant_cls, is_singleton = _create_variant(name, variant_type, cls.__name__)
        variants[name] = variant_cls
        variant_types.append(variant_cls)

        if is_singleton:
            setattr(cls, name, variant_cls())
        else:
            setattr(cls, name, variant_cls)

    cls._variants = variants  # type: ignore[attr-defined]
    cls._union = Union[tuple(variant_types)] if variant_types else None  # type: ignore[attr-defined]

    return cls
