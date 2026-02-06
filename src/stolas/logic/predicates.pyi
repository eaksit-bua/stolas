"""Type stubs for predicates module."""

from typing import Any, Callable

def contains(item: Any) -> Callable[[Any], bool]:
    """Check if item is in container."""
    ...

def negate(predicate: Callable[[Any], Any]) -> Callable[[Any], bool]:
    """Negate a predicate function."""
    ...

def both(*predicates: Callable[[Any], Any]) -> Callable[[Any], bool]:
    """Combine predicates with logical AND."""
    ...

def either(*predicates: Callable[[Any], Any]) -> Callable[[Any], bool]:
    """Combine predicates with logical OR."""
    ...
