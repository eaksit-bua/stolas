"""Accessor helpers: get, at, call."""

from typing import Any, Callable, TypeVar

T = TypeVar("T")
K = TypeVar("K")


def get(attr: str) -> Callable[[Any], Any]:
    """Return a function that gets an attribute from an object.

    Usage: Ok(user) >> get("name")
    """

    def wrapper(x: Any) -> Any:
        return getattr(x, attr)

    return wrapper


def at(key: K) -> Callable[[Any], Any]:
    """Return a function that gets an item by key/index.

    Usage: Ok(data) >> at("id")
           Ok(items) >> at(0)
    """

    def wrapper(x: Any) -> Any:
        return x[key]

    return wrapper


def call(method: str, *args: Any, **kwargs: Any) -> Callable[[Any], Any]:
    """Return a function that calls a method on an object.

    Usage: Ok(s) >> call("upper")
           Ok(s) >> call("replace", "a", "b")
    """

    def wrapper(x: Any) -> Any:
        return getattr(x, method)(*args, **kwargs)

    return wrapper
