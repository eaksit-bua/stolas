"""replace(): immutable copy-with-changes for @struct instances.

Rebuilding a frozen struct by hand to change one field is the daily pain of
immutable data. ``replace`` returns a new instance with the given fields
overridden and every other field copied across, re-running ``__init__`` so the
result is fully re-validated (type checks, and value validators once added).
"""

from typing import Any, TypeVar

T = TypeVar("T")


def replace(instance: T, **changes: Any) -> T:
    """Return a copy of a @struct ``instance`` with ``changes`` applied.

    The original is never mutated. Unknown field names raise ``TypeError``;
    the new instance is re-validated by the struct's ``__init__``.
    """
    cls = type(instance)
    if not getattr(cls, "__stolas_struct__", False):
        raise TypeError(f"replace() expects a @struct instance, got {cls.__name__}")

    slots: tuple[str, ...] = cls.__slots__  # type: ignore[assignment]
    extra = set(changes) - set(slots)
    if extra:
        raise TypeError(f"Unknown fields: {extra}")

    kwargs = {name: changes.get(name, getattr(instance, name)) for name in slots}
    return cls(**kwargs)  # type: ignore[return-value]
