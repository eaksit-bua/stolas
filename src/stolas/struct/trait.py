"""@trait: Multi-argument dispatch polymorphism with explicit registration."""

import types
import warnings
from typing import Any, Callable, Union, get_args, get_origin


def _unwrap_types(types_: tuple[type, ...]) -> tuple[type, ...]:
    """Unwrap Union types into individual types."""
    result: list[type] = []
    for t in types_:
        # Handle @cases ADTs which have a _union attribute
        if hasattr(t, "_union"):
            union_type = getattr(t, "_union")
            if get_origin(union_type) is Union or get_origin(union_type) is types.UnionType:
                result.extend(get_args(union_type))
                continue

        origin = get_origin(t)
        if origin is Union or origin is types.UnionType:
            result.extend(get_args(t))
        else:
            result.append(t)
    return tuple(result)


def _find_implementation_single(
    arg_type: type,
    registry: dict[type, Callable[..., Any]],
    cache: dict[type, Callable[..., Any]],
) -> Callable[..., Any] | None:
    """Find implementation via MRO lookup with caching (single dispatch)."""
    if arg_type in cache:
        return cache[arg_type]

    for mro_type in arg_type.__mro__:
        if mro_type in registry:
            cache[arg_type] = registry[mro_type]
            return cache[arg_type]

    return None


def _find_implementation_multi(
    arg_types: tuple[type, ...],
    registry: dict[tuple[type, ...], Callable[..., Any]],
    cache: dict[tuple[type, ...], Callable[..., Any]],
) -> Callable[..., Any] | None:
    """Find implementation via MRO lookup for multiple arguments with caching."""
    if arg_types in cache:
        return cache[arg_types]

    # Try exact match first
    if arg_types in registry:
        cache[arg_types] = registry[arg_types]
        return cache[arg_types]

    # Try MRO combinations: for each argument, try its MRO types
    # This is a cartesian product of MROs
    mros = [t.__mro__ for t in arg_types]

    def search_mro(idx: int, current: list[type]) -> Callable[..., Any] | None:
        if idx == len(mros):
            key = tuple(current)
            if key in registry:
                return registry[key]
            return None

        for mro_type in mros[idx]:
            result = search_mro(idx + 1, [*current, mro_type])
            if result is not None:
                return result
        return None

    impl = search_mro(0, [])
    if impl is not None:
        cache[arg_types] = impl
    return impl


class MissingImplementationWarning(UserWarning):
    """Warning issued when no implementation is found for given types."""

    pass


class TraitDispatcher:
    """Dispatcher for multi-argument dispatch polymorphism.

    Supports both single-dispatch (first argument only) and multi-dispatch
    (multiple arguments). The dispatch mode is auto-detected based on the
    implementation function's parameter count.

    Example - Single dispatch (same impl for multiple types):
        @my_trait.impl(Dog, Cat)  # func takes 1 arg -> same impl for Dog OR Cat
        def handle_animal(animal) -> str: ...

    Example - Multi dispatch (dispatch on type tuple):
        @my_trait.impl(Dog, Cat)  # func takes 2 args -> dispatch on (Dog, Cat)
        def handle_dog_cat(dog, cat) -> str: ...
    """

    def __init__(self, default_func: Callable[..., Any]):
        self._default = default_func
        self._name = getattr(default_func, "__name__", "<trait>")
        # Single dispatch registry: type -> impl
        self._registry_single: dict[type, Callable[..., Any]] = {}
        self._cache_single: dict[type, Callable[..., Any]] = {}
        # Multi dispatch registry: (type, type, ...) -> impl
        self._registry_multi: dict[tuple[type, ...], Callable[..., Any]] = {}
        self._cache_multi: dict[tuple[type, ...], Callable[..., Any]] = {}

    def impl(
        self, *types_: type
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register implementation for specific types.

        Single dispatch (use union for multiple types):
            @my_trait.impl(Dog | Cat | Mouse)
            def handle_pet(pet) -> str:
                return pet.name

        Multi dispatch (use separate args for type signature):
            @my_trait.impl(Dog, Cat)
            def handle_dog_cat(dog, cat) -> str:
                return f"{dog.name} chases {cat.name}"

            @my_trait.impl(Cat, Dog)
            def handle_cat_dog(cat, dog) -> str:
                return f"{cat.name} hisses at {dog.name}"
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            num_types = len(types_)

            if num_types > 1:
                # Multi-dispatch: (Type1, Type2, ...) signature
                unwrapped = tuple(_unwrap_types((t,))[0] for t in types_)
                self._registry_multi[unwrapped] = func
                self._cache_multi.clear()
            else:
                # Single-dispatch: impl(Type) or impl(Type1 | Type2 | ...)
                unwrapped = _unwrap_types(types_)
                for t in unwrapped:
                    self._registry_single[t] = func
                self._cache_single.clear()
            return func

        return decorator

    @property
    def _is_multi_dispatch(self) -> bool:
        """Check if any multi-dispatch signatures are registered."""
        return bool(self._registry_multi)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Dispatch to implementation based on argument types."""
        if not args:
            raise TypeError(f"{self._name}() requires at least one argument")

        if self._is_multi_dispatch and len(args) >= 2:
            # Try multi-dispatch first
            arg_types = tuple(type(arg) for arg in args)
            impl = _find_implementation_multi(
                arg_types, self._registry_multi, self._cache_multi
            )
            if impl is not None:
                return impl(*args, **kwargs)
            # Fall back to single-dispatch on first argument

        # Single-dispatch mode
        arg = args[0]
        impl = _find_implementation_single(
            type(arg), self._registry_single, self._cache_single
        )
        if impl is None:
            if self._is_multi_dispatch and len(args) >= 2:
                type_names = ", ".join(type(a).__name__ for a in args)
                warnings.warn(
                    f"No implementation of '{self._name}' for types: ({type_names})",
                    MissingImplementationWarning,
                    stacklevel=2,
                )
                raise NotImplementedError(
                    f"No implementation of '{self._name}' for types: ({type_names})"
                )
            else:
                warnings.warn(
                    f"No implementation of '{self._name}' for type: {type(arg).__name__}",
                    MissingImplementationWarning,
                    stacklevel=2,
                )
                raise NotImplementedError(
                    f"No implementation of '{self._name}' for type: {type(arg).__name__}"
                )
        return impl(*args, **kwargs)

    def require(self, *objs: Any) -> bool:
        """Check if types have an implementation."""
        if self._is_multi_dispatch and len(objs) >= 2:
            arg_types = tuple(type(obj) for obj in objs)
            impl = _find_implementation_multi(
                arg_types, self._registry_multi, self._cache_multi
            )
            if impl is not None:
                return True
            # Fall back to single dispatch check

        return (
            _find_implementation_single(
                type(objs[0]), self._registry_single, self._cache_single
            )
            is not None
        )

    def check(self, *objs: Any) -> None:
        """Raise TypeError if types have no implementation."""
        if not self.require(*objs):
            if self._is_multi_dispatch and len(objs) >= 2:
                type_names = ", ".join(type(obj).__name__ for obj in objs)
                raise TypeError(
                    f"No implementation of '{self._name}' for types: ({type_names})"
                )
            else:
                raise TypeError(
                    f"No implementation of '{self._name}' for type: {type(objs[0]).__name__}"
                )

    @property
    def types(self) -> tuple[type, ...]:
        """Return registered types (single-dispatch only)."""
        return tuple(self._registry_single.keys())

    @property
    def signatures(self) -> tuple[tuple[type, ...], ...]:
        """Return registered type signatures (multi-dispatch)."""
        return tuple(self._registry_multi.keys())


def trait(func: Callable[..., Any]) -> TraitDispatcher:
    """Decorator to create a trait with multi-argument dispatch.

    Single-dispatch (use union for same impl across types):
        @trait
        def describe(x) -> str:
            raise NotImplementedError

        @describe.impl(Dog | Cat)  # Union -> same impl for Dog OR Cat
        def _(animal) -> str:
            return f"Animal: {animal.name}"

    Multi-dispatch (use separate args for type signature):
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
    return TraitDispatcher(func)
