"""Placeholder logic for lambda-free expressions (syntax sugar)."""

from typing import Any, Callable, TypeVar

T = TypeVar("T")


class Placeholder:
    """Lazy expression builder.

    Captures operators and attribute access to build callables dynamically.
    Usage:
        _ > 5       -> lambda x: x > 5
        _.name      -> lambda x: x.name
        _ * 2       -> lambda x: x * 2
    """

    def __getattr__(self, name: str) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return getattr(x, name)

        return PlaceholderExpression(expr)

    def __getitem__(self, key: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return x[key]

        return PlaceholderExpression(expr)

    # Comparison operators
    def __eq__(self, other: Any) -> "PlaceholderExpression":  # type: ignore[override]
        def expr(x: Any) -> bool:
            return bool(x == other)

        return PlaceholderExpression(expr)

    def __ne__(self, other: Any) -> "PlaceholderExpression":  # type: ignore[override]
        def expr(x: Any) -> bool:
            return bool(x != other)

        return PlaceholderExpression(expr)

    def __lt__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> bool:
            return bool(x < other)

        return PlaceholderExpression(expr)

    def __le__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> bool:
            return bool(x <= other)

        return PlaceholderExpression(expr)

    def __gt__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> bool:
            return bool(x > other)

        return PlaceholderExpression(expr)

    def __ge__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> bool:
            return bool(x >= other)

        return PlaceholderExpression(expr)

    # Arithmetic operators
    def __add__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return x + other

        return PlaceholderExpression(expr)

    def __sub__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return x - other

        return PlaceholderExpression(expr)

    def __mul__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return x * other

        return PlaceholderExpression(expr)

    def __truediv__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return x / other

        return PlaceholderExpression(expr)

    def __floordiv__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return x // other

        return PlaceholderExpression(expr)

    def __mod__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return x % other

        return PlaceholderExpression(expr)

    def __pow__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return x**other

        return PlaceholderExpression(expr)

    # Reflected arithmetic operators (other + self)
    def __radd__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return other + x

        return PlaceholderExpression(expr)

    def __rsub__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return other - x

        return PlaceholderExpression(expr)

    def __rmul__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return other * x

        return PlaceholderExpression(expr)

    def __rtruediv__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return other / x

        return PlaceholderExpression(expr)

    def __rfloordiv__(self, other: Any) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return other // x

        return PlaceholderExpression(expr)

    # Unary operators
    def __neg__(self) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return -x

        return PlaceholderExpression(expr)

    def __pos__(self) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return +x

        return PlaceholderExpression(expr)

    def __abs__(self) -> "PlaceholderExpression":
        def expr(x: Any) -> Any:
            return abs(x)

        return PlaceholderExpression(expr)


class PlaceholderExpression:
    """A compiled expression ready to be called."""

    __slots__ = ("_func",)

    def __init__(self, func: Callable[[Any], Any]) -> None:
        self._func = func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._func(*args, **kwargs)

    def __getattr__(self, name: str) -> "PlaceholderMethodProxy":
        return PlaceholderMethodProxy(self, name)

    # Comparison operators for chaining
    def __eq__(self, other: Any) -> "PlaceholderExpression":  # type: ignore[override]
        parent_func = self._func

        def expr(x: Any) -> bool:
            return bool(parent_func(x) == other)

        return PlaceholderExpression(expr)

    def __ne__(self, other: Any) -> "PlaceholderExpression":  # type: ignore[override]
        parent_func = self._func

        def expr(x: Any) -> bool:
            return bool(parent_func(x) != other)

        return PlaceholderExpression(expr)

    def __gt__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> bool:
            return bool(parent_func(x) > other)

        return PlaceholderExpression(expr)

    def __ge__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> bool:
            return bool(parent_func(x) >= other)

        return PlaceholderExpression(expr)

    def __lt__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> bool:
            return bool(parent_func(x) < other)

        return PlaceholderExpression(expr)

    def __le__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> bool:
            return bool(parent_func(x) <= other)

        return PlaceholderExpression(expr)

    # Arithmetic operators for chaining
    def __add__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> Any:
            return parent_func(x) + other

        return PlaceholderExpression(expr)

    def __sub__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> Any:
            return parent_func(x) - other

        return PlaceholderExpression(expr)

    def __mul__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> Any:
            return parent_func(x) * other

        return PlaceholderExpression(expr)

    def __truediv__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> Any:
            return parent_func(x) / other

        return PlaceholderExpression(expr)

    def __floordiv__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> Any:
            return parent_func(x) // other

        return PlaceholderExpression(expr)

    def __mod__(self, other: Any) -> "PlaceholderExpression":
        parent_func = self._func

        def expr(x: Any) -> Any:
            return parent_func(x) % other

        return PlaceholderExpression(expr)


class PlaceholderMethodProxy:
    """Helper to capture method calls on an expression result."""

    __slots__ = ("_parent", "_method_name")

    def __init__(self, parent: PlaceholderExpression, method_name: str) -> None:
        self._parent = parent
        self._method_name = method_name

    def __call__(self, *args: Any, **kwargs: Any) -> PlaceholderExpression:
        parent = self._parent
        method_name = self._method_name

        def compiled(x: Any) -> Any:
            obj = parent(x)
            method = getattr(obj, method_name)
            return method(*args, **kwargs)

        return PlaceholderExpression(compiled)


# Global instance
_ = Placeholder()
