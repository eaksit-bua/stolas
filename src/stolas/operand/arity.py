"""Arity decorators for strict currying with partial application."""

from typing import Any, Callable, Generic, Protocol, TypeVar, overload

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
D = TypeVar("D")
R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)


class Curried(Generic[R]):
    """Callable object that supports strict currying with preserved metadata."""

    __slots__ = (
        "_func",
        "_arity",
        "_accumulated",
        "_arg_names",
        "_doc",
        "_annotations",
        "_wrapper",
    )

    def __init__(
        self,
        func: Callable[..., R],
        arity: int,
        accumulated: tuple[Any, ...] = (),
        wrapper: Callable[[R], Any] | None = None,
    ) -> None:
        self._func = func
        self._arity = arity
        self._accumulated = accumulated
        self._arg_names = _get_arg_names(func)
        self._doc = func.__doc__
        self._annotations = getattr(func, "__annotations__", {})
        self._wrapper = wrapper

    @property
    def __name__(self) -> str:
        return self._func.__name__

    def __getattribute__(self, name: str) -> Any:
        if name == "__doc__":
            return object.__getattribute__(self, "_doc")
        if name == "__annotations__":
            return object.__getattribute__(self, "_annotations")
        return object.__getattribute__(self, name)

    def __repr__(self) -> str:
        filled = len(self._accumulated)
        parts: list[str] = []
        for i, name in enumerate(self._arg_names):
            if i < filled:
                parts.append(f"{name}={self._accumulated[i]!r}")
            else:
                parts.append("?")
        return f"{self._func.__name__}({', '.join(parts)})"

    def __call__(self, *args: Any) -> Any:
        if not args:
            return self

        total = len(self._accumulated) + len(args)

        if total > self._arity:
            raise TypeError(
                f"{self._func.__name__}() takes {self._arity} positional "
                f"arguments but {total} were given"
            )

        new_accumulated = self._accumulated + args

        if total == self._arity:
            result = self._func(*new_accumulated)
            if self._wrapper is not None:
                return self._wrapper(result)
            return result

        return Curried(self._func, self._arity, new_accumulated, self._wrapper)


def _get_arg_names(func: Callable[..., Any]) -> tuple[str, ...]:
    """Extract argument names from function."""
    code = func.__code__
    return code.co_varnames[: code.co_argcount]


def _arity_name(arity: int) -> str:
    """Get decorator name for arity."""
    names = {1: "unary", 2: "binary", 3: "ternary", 4: "quaternary"}
    return names.get(arity, f"arity_{arity}")


import inspect

def _validate_arity(func: Callable[..., Any], arity: int) -> None:
    """Validate function has correct arity."""
    try:
        sig = inspect.signature(func)
    except ValueError:
        # Cannot inspect signature (e.g. built-in), fall back to skip validation
        # or assume it's correct/let it fail at runtime.
        return

    # Count parameters that require arguments (ignoring *args, **kwargs, defaults)
    # Actually, easy way: just check total parameters if no defaults,
    # or ensuring we can bind exactly 'arity' positional args.
    
    # We want exact arity match for strict currying.
    # However, wrapped functions might have complicated signatures.
    # Stolas strictness demands exact positional args.
    
    params = list(sig.parameters.values())
    
    # Filter out *args, **kwargs
    valid_params = [
        p for p in params 
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    
    actual_arity = len(valid_params)
    
    if actual_arity != arity:
        raise TypeError(
            f"@{_arity_name(arity)} requires exactly {arity} parameters, "
            f"but {func.__name__}() has {actual_arity}"
        )


# Protocol definitions for type-safe currying


class UnaryCallable(Protocol[A, R_co]):
    """Protocol for unary curried function."""

    @property
    def __name__(self) -> str: ...

    @overload
    def __call__(self) -> "UnaryCallable[A, R_co]": ...

    @overload
    def __call__(self, a: A) -> R_co: ...

    def __call__(self, a: A = ...) -> Any: ...


class BinaryCallable(Protocol[A, B, R_co]):
    """Protocol for binary curried function."""

    @property
    def __name__(self) -> str: ...

    @overload
    def __call__(self) -> "BinaryCallable[A, B, R_co]": ...

    @overload
    def __call__(self, a: A) -> Callable[[B], R_co]: ...

    @overload
    def __call__(self, a: A, b: B) -> R_co: ...

    def __call__(self, a: A = ..., b: B = ...) -> Any: ...


class TernaryCallable(Protocol[A, B, C, R_co]):
    """Protocol for ternary curried function."""

    @property
    def __name__(self) -> str: ...

    @overload
    def __call__(self) -> "TernaryCallable[A, B, C, R_co]": ...

    @overload
    def __call__(self, a: A) -> Callable[[B, C], R_co]: ...

    @overload
    def __call__(self, a: A, b: B) -> Callable[[C], R_co]: ...

    @overload
    def __call__(self, a: A, b: B, c: C) -> R_co: ...

    def __call__(self, a: A = ..., b: B = ..., c: C = ...) -> Any: ...


class QuaternaryCallable(Protocol[A, B, C, D, R_co]):
    """Protocol for quaternary curried function."""

    @property
    def __name__(self) -> str: ...

    @overload
    def __call__(self) -> "QuaternaryCallable[A, B, C, D, R_co]": ...

    @overload
    def __call__(self, a: A) -> Callable[[B, C, D], R_co]: ...

    @overload
    def __call__(self, a: A, b: B) -> Callable[[C, D], R_co]: ...

    @overload
    def __call__(self, a: A, b: B, c: C) -> Callable[[D], R_co]: ...

    @overload
    def __call__(self, a: A, b: B, c: C, d: D) -> R_co: ...

    def __call__(self, a: A = ..., b: B = ..., c: C = ..., d: D = ...) -> Any: ...


# Decorator implementations


def unary(func: Callable[[A], R]) -> UnaryCallable[A, R]:
    """Decorator enforcing exactly 1 argument."""
    _validate_arity(func, 1)
    return Curried(func, 1)  # type: ignore[return-value]


def binary(func: Callable[[A, B], R]) -> BinaryCallable[A, B, R]:
    """Decorator enforcing exactly 2 arguments with partial application."""
    _validate_arity(func, 2)
    return Curried(func, 2)  # type: ignore[return-value]


def ternary(func: Callable[[A, B, C], R]) -> TernaryCallable[A, B, C, R]:
    """Decorator enforcing exactly 3 arguments with partial application."""
    _validate_arity(func, 3)
    return Curried(func, 3)  # type: ignore[return-value]


def quaternary(func: Callable[[A, B, C, D], R]) -> QuaternaryCallable[A, B, C, D, R]:
    """Decorator enforcing exactly 4 arguments with partial application."""
    _validate_arity(func, 4)
    return Curried(func, 4)  # type: ignore[return-value]
