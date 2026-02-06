"""Type stubs for common module."""

from typing import Any, Callable, TypeVar

T = TypeVar("T")

def identity(x: T) -> T:
    """Return input unchanged."""
    ...

def const(value: T) -> Callable[[Any], T]:
    """Return function that always returns value."""
    ...

def tap(func: Callable[[T], Any]) -> Callable[[T], T]:
    """Execute side-effect and return input."""
    ...

def tee(func: Callable[[T], Any]) -> Callable[[T], T]:
    """Alias for tap."""
    ...

def fmt(template: str) -> Callable[[Any], str]:
    """Format value into template string."""
    ...
