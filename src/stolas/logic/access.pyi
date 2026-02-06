"""Type stubs for access module."""

from typing import Any, Callable, TypeVar

K = TypeVar("K")

def get(attr: str) -> Callable[[Any], Any]:
    """Get attribute from object."""
    ...

def at(key: K) -> Callable[[Any], Any]:
    """Get item by key or index."""
    ...

def call(method: str, *args: Any, **kwargs: Any) -> Callable[[Any], Any]:
    """Call method on object."""
    ...
