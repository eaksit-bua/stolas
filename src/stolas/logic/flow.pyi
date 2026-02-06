"""Type stubs for flow module."""

from typing import Any, Callable, TypeVar
from stolas.types.result import Ok, Error

T = TypeVar("T")

def check(
    predicate: Callable[[T], bool], error_msg: str
) -> Callable[[T], Ok[T] | Error[str]]:
    """Validate with predicate, return Ok or Error."""
    ...

def strict(type_: type[T]) -> Callable[[Any], Ok[T] | Error[TypeError]]:
    """Type validation returning Ok or Error."""
    ...
