"""Type stubs for trait decorator."""

from typing import Any, Callable, Generic, TypeVar, overload

_R = TypeVar("_R")

class MissingImplementationWarning(UserWarning):
    """Warning issued when no implementation is found for given types."""

    pass

class TraitDispatcher(Generic[_R]):
    """A trait dispatcher that handles polymorphic function calls."""

    @overload
    def __call__(self, obj: Any) -> _R: ...
    @overload
    def __call__(self, obj1: Any, obj2: Any, *args: Any, **kwargs: Any) -> _R: ...
    @overload
    def impl(self, type_: type) -> Callable[[Callable[..., _R]], Callable[..., _R]]:
        """Single dispatch: impl(Type) or impl(Type1 | Type2 | ...)."""
        ...
    @overload
    def impl(
        self, type1: type, type2: type, *types: type
    ) -> Callable[[Callable[..., _R]], Callable[..., _R]]:
        """Multi dispatch: impl(Type1, Type2, ...) for type signature."""
        ...
    @overload
    def require(self, obj: Any) -> bool: ...
    @overload
    def require(self, obj1: Any, obj2: Any, *objs: Any) -> bool: ...
    @overload
    def check(self, obj: Any) -> None: ...
    @overload
    def check(self, obj1: Any, obj2: Any, *objs: Any) -> None: ...
    @property
    def types(self) -> tuple[type, ...]:
        """Registered types for single-dispatch."""
        ...
    @property
    def signatures(self) -> tuple[tuple[type, ...], ...]:
        """Registered type signatures for multi-dispatch."""
        ...

def trait(func: Callable[..., _R]) -> TraitDispatcher[_R]:
    """Create a trait dispatcher with single or multi-argument dispatch.

    Single dispatch (use union for same impl across types):
        @trait
        def describe(x) -> str:
            raise NotImplementedError

        @describe.impl(Dog | Cat)  # Union -> same impl for Dog OR Cat
        def _(animal) -> str:
            return animal.name

    Multi dispatch (use separate args for type signature):
        @trait
        def interact(a, b) -> str:
            raise NotImplementedError

        @interact.impl(Dog, Cat)  # Separate args -> dispatch on (Dog, Cat)
        def _(dog, cat) -> str:
            return f"{dog.name} chases {cat.name}"

        @interact.impl(Cat, Dog)  # Different impl for (Cat, Dog)
        def _(cat, dog) -> str:
            return f"{cat.name} hisses at {dog.name}"
    """
    ...
