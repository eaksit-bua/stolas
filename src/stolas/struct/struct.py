"""@struct: C/Rust-like immutable struct with fixed memory layout."""

import types as _types
from typing import (
    Any,
    Callable,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from stolas.struct.replace import replace as _replace_fn
from stolas.types.validated import Invalid

T = TypeVar("T")


def _get_field_value(key: str, kwargs: dict[str, Any], defaults: dict[str, Any]) -> Any:
    """Get field value from kwargs or defaults."""
    if key in kwargs:
        return kwargs[key]
    if key in defaults:
        return defaults[key]
    raise TypeError(f"Missing required field: {key}")


def _type_name(expected_type: Any) -> str:
    """Best-effort human name for a type or typing construct."""
    return getattr(expected_type, "__name__", None) or str(expected_type)


def _validate_type(key: str, value: Any, expected_type: Any) -> None:
    """Validate that value matches expected type.

    Handles plain classes, parameterized generics (shallow, e.g. ``list[int]``),
    unions/optionals, and ``@cases`` union annotations (a value is valid if its
    runtime type is a registered variant of the union).
    """
    if expected_type is Any:
        return

    # @cases union annotation: accept any registered variant instance.
    variant_names = getattr(expected_type, "_variant_names", None)
    if variant_names is not None:
        if type(value) in variant_names:
            return
        raise TypeError(
            f"Field '{key}' expects a {_type_name(expected_type)} variant, "
            f"got {type(value).__name__}"
        )

    origin = get_origin(expected_type)

    if origin is None:
        if not isinstance(value, expected_type):
            raise TypeError(
                f"Field '{key}' expects {_type_name(expected_type)}, "
                f"got {type(value).__name__}"
            )
        return

    if origin is Union or origin is _types.UnionType:
        for member in get_args(expected_type):
            if member is type(None):
                if value is None:
                    return
                continue
            member_origin = get_origin(member)
            check = member_origin if member_origin is not None else member
            try:
                if isinstance(value, check):
                    return
            except TypeError:  # pragma: no cover - members normalize to classes
                continue
        member_names = ", ".join(_type_name(m) for m in get_args(expected_type))
        raise TypeError(
            f"Field '{key}' expects {member_names}, got {type(value).__name__}"
        )

    # Parameterized generic (list[int], dict[str, int], tuple[int, ...], ...):
    # shallow-check the container origin only.
    if not isinstance(value, origin):
        raise TypeError(
            f"Field '{key}' expects {_type_name(origin)}, got {type(value).__name__}"
        )


def _validate_fields(
    kwargs: dict[str, Any], slots: tuple[str, ...], defaults: dict[str, Any]
) -> None:
    """Validate that no unknown fields are passed."""
    extra = set(kwargs) - set(slots)
    if extra:
        raise TypeError(f"Unknown fields: {extra}")

    missing = set(slots) - set(kwargs) - set(defaults)
    if missing:
        raise TypeError(f"Missing required fields: {missing}")


def _validate_values(
    self: Any,
    slots: tuple[str, ...],
    validators: dict[str, Callable[[Any], Any]],
) -> None:
    """Run opt-in field validators, aggregating every failure into one error.

    Each validator returns a ``Validated``; ``Invalid`` results contribute their
    messages. If any field fails, a single ``ValueError`` lists all messages
    (decision D6: value-validation failure is distinct from the type ``TypeError``).
    """
    errors: list[str] = []
    for key in slots:
        validator = validators.get(key)
        if validator is None:
            continue
        result = validator(getattr(self, key))
        if isinstance(result, Invalid):
            errors.extend(f"{key}: {message}" for message in result.errors)
    if errors:
        raise ValueError("; ".join(errors))


def _make_init(
    slots: tuple[str, ...],
    defaults: dict[str, Any],
    annotations: dict[str, type],
    validators: dict[str, Callable[[Any], Any]],
) -> Any:
    """Create __init__ method for struct."""

    def __init__(self: Any, **kwargs: Any) -> None:
        _validate_fields(kwargs, slots, defaults)
        for key in slots:
            value = _get_field_value(key, kwargs, defaults)
            _validate_type(key, value, annotations[key])
            object.__setattr__(self, key, value)
        if validators:
            _validate_values(self, slots, validators)

    return __init__


def _make_setattr() -> Any:
    """Create __setattr__ that blocks mutation."""

    def __setattr__(self: Any, name: str, value: Any) -> None:
        raise AttributeError("Struct is immutable")

    return __setattr__


def _make_delattr() -> Any:
    """Create __delattr__ that blocks deletion."""

    def __delattr__(self: Any, name: str) -> None:
        raise AttributeError("Struct is immutable")

    return __delattr__


def _make_repr(cls_name: str, slots: tuple[str, ...]) -> Any:
    """Create __repr__ method."""

    def __repr__(self: Any) -> str:
        fields = ", ".join(f"{k}={getattr(self, k)!r}" for k in slots)
        return f"{cls_name}({fields})"

    return __repr__


def _make_eq(slots: tuple[str, ...]) -> Any:
    """Create __eq__ method."""

    def __eq__(self: Any, other: Any) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in slots)

    return __eq__


def _make_hash(slots: tuple[str, ...]) -> Any:
    """Create __hash__ method."""

    def __hash__(self: Any) -> int:
        return hash(tuple(getattr(self, k) for k in slots))

    return __hash__


def _make_rshift() -> Any:
    """Create __rshift__ for pipeline operator."""

    def __rshift__(self: Any, other: Any) -> Any:
        return other(self)

    return __rshift__


def _make_init_subclass() -> Any:
    """Create __init_subclass__ that blocks inheritance."""

    def __init_subclass__(cls: type, /, **kwargs: Any) -> None:
        raise TypeError("Cannot inherit from struct")

    return classmethod(__init_subclass__)


def _make_replace_method() -> Any:
    """Create a `.replace(**changes)` method returning a modified copy."""

    def replace(self: Any, **changes: Any) -> Any:
        return _replace_fn(self, **changes)

    return replace


def _build_struct(cls: type[T], *, open: bool) -> type[T]:
    """Build the immutable struct class from ``cls``.

    ``open`` controls only one thing: whether the inheritance-blocking
    ``__init_subclass__`` is installed. With ``open=False`` (the default) the
    generated namespace is byte-identical to the historical ``@struct`` output;
    with ``open=True`` the block is omitted so subclasses may be declared while
    the base struct itself stays frozen and ``__slots__``-only.
    """
    annotations = get_type_hints(cls) if hasattr(cls, "__annotations__") else {}
    slots = tuple(annotations.keys())
    defaults = {k: getattr(cls, k) for k in slots if hasattr(cls, k)}
    validators: dict[str, Callable[[Any], Any]] = getattr(cls, "__validators__", {})

    namespace: dict[str, Any] = {
        "__slots__": slots,
        "__annotations__": annotations,
        "__match_args__": slots,
        "__stolas_struct__": True,
        "__stolas_fields__": tuple(annotations.items()),
        "__init__": _make_init(slots, defaults, annotations, validators),
        "__setattr__": _make_setattr(),
        "__delattr__": _make_delattr(),
        "__repr__": _make_repr(cls.__name__, slots),
        "__eq__": _make_eq(slots),
        "__hash__": _make_hash(slots),
        "__rshift__": _make_rshift(),
        "__init_subclass__": _make_init_subclass(),
        "__module__": cls.__module__,
    }
    # open=True opts in to subclassing: drop the inheritance guard. The default
    # (open=False) keeps the guard so the namespace stays byte-identical.
    if open:
        del namespace["__init_subclass__"]
    # Only install the `.replace()` method when it would not shadow a field
    # literally named ``replace``; the free function always works regardless.
    if "replace" not in slots:
        namespace["replace"] = _make_replace_method()

    # Carry opt-in field validators onto the generated class for inspection.
    # Absent ``__validators__`` adds nothing, keeping the class byte-identical.
    if validators:
        namespace["__validators__"] = validators

    new_cls = cast(type[T], type(cls.__name__, (), namespace))

    return new_cls


def struct(cls: type[T] | None = None, *, open: bool = False) -> Any:
    """Decorator that creates an immutable struct with fixed memory layout.

    Dual-form: use bare as ``@struct`` (the default, ``open=False``) or called
    as ``@struct(open=True)``. ``open=False`` is byte-identical to the historical
    behavior -- frozen, ``__slots__``-only, and not subclassable. ``open=True``
    opts in to allowing subclasses (the inheritance guard is not installed) while
    the base struct itself stays immutable.
    """
    if cls is None:
        # Call form: @struct(open=...) -> return a decorator.
        def decorator(inner: type[T]) -> type[T]:
            return _build_struct(inner, open=open)

        return decorator
    # Bare form: @struct.
    return _build_struct(cls, open=open)
