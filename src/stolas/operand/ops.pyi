"""Type stubs for @ops decorator."""

from typing import Callable, Any, overload

# ops() composes decorators - the return type depends on which decorators are composed
# Since we can't track the full decorator chain statically, we use Any return type
# This allows curried + Result wrapped functions to work correctly
@overload
def ops() -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
@overload
def ops(__d1: Callable[[Any], Any]) -> Callable[[Callable[..., Any]], Any]: ...
@overload
def ops(
    __d1: Callable[[Any], Any], __d2: Callable[[Any], Any]
) -> Callable[[Callable[..., Any]], Any]: ...
@overload
def ops(
    __d1: Callable[[Any], Any], __d2: Callable[[Any], Any], __d3: Callable[[Any], Any]
) -> Callable[[Callable[..., Any]], Any]: ...
@overload
def ops(*decorators: Callable[[Any], Any]) -> Callable[[Callable[..., Any]], Any]: ...
