"""Type stubs for arity decorators."""

from typing import TypeVar, Callable, Protocol, overload

_A = TypeVar("_A")
_B = TypeVar("_B")
_C = TypeVar("_C")
_D = TypeVar("_D")
_R = TypeVar("_R")
_R_co = TypeVar("_R_co", covariant=True)

# Protocol definitions matching arity.py

class UnaryCallable(Protocol[_A, _R_co]):
    """Protocol for unary curried function."""

    @property
    def __name__(self) -> str: ...
    @overload
    def __call__(self) -> "UnaryCallable[_A, _R_co]": ...
    @overload
    def __call__(self, a: _A) -> _R_co: ...

class BinaryCallable(Protocol[_A, _B, _R_co]):
    """Protocol for binary curried function.

    Supports chained partial application:
        f(a)(b) or f(a, b)
    """

    @property
    def __name__(self) -> str: ...
    @overload
    def __call__(self) -> "BinaryCallable[_A, _B, _R_co]": ...
    @overload
    def __call__(self, a: _A) -> "UnaryCallable[_B, _R_co]": ...
    @overload
    def __call__(self, a: _A, b: _B) -> _R_co: ...

class TernaryCallable(Protocol[_A, _B, _C, _R_co]):
    """Protocol for ternary curried function.

    Supports chained partial application:
        f(a)(b)(c) or f(a, b)(c) or f(a, b, c)
    """

    @property
    def __name__(self) -> str: ...
    @overload
    def __call__(self) -> "TernaryCallable[_A, _B, _C, _R_co]": ...
    @overload
    def __call__(self, a: _A) -> "BinaryCallable[_B, _C, _R_co]": ...
    @overload
    def __call__(self, a: _A, b: _B) -> "UnaryCallable[_C, _R_co]": ...
    @overload
    def __call__(self, a: _A, b: _B, c: _C) -> _R_co: ...

class QuaternaryCallable(Protocol[_A, _B, _C, _D, _R_co]):
    """Protocol for quaternary curried function.

    Supports chained partial application:
        f(a)(b)(c)(d) or f(a, b)(c, d) or f(a, b, c, d)
    """

    @property
    def __name__(self) -> str: ...
    @overload
    def __call__(self) -> "QuaternaryCallable[_A, _B, _C, _D, _R_co]": ...
    @overload
    def __call__(self, a: _A) -> "TernaryCallable[_B, _C, _D, _R_co]": ...
    @overload
    def __call__(self, a: _A, b: _B) -> "BinaryCallable[_C, _D, _R_co]": ...
    @overload
    def __call__(self, a: _A, b: _B, c: _C) -> "UnaryCallable[_D, _R_co]": ...
    @overload
    def __call__(self, a: _A, b: _B, c: _C, d: _D) -> _R_co: ...

# Decorator function signatures

def unary(func: Callable[[_A], _R]) -> UnaryCallable[_A, _R]: ...
def binary(func: Callable[[_A, _B], _R]) -> BinaryCallable[_A, _B, _R]: ...
def ternary(func: Callable[[_A, _B, _C], _R]) -> TernaryCallable[_A, _B, _C, _R]: ...
def quaternary(
    func: Callable[[_A, _B, _C, _D], _R],
) -> QuaternaryCallable[_A, _B, _C, _D, _R]: ...
