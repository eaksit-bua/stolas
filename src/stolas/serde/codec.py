"""Structural codec for stolas types: to_dict / from_dict / to_json / from_json.

Zero runtime dependencies. Serialization is **type-directed** (the Rust ``serde``
model): a ``@cases`` tag lives on the *union* — i.e. it is emitted when a value
occupies a position declared as the union (a struct field or an explicit target),
not injected onto the value itself.

  * A plain ``@struct`` serializes to a bare field dict: ``{'x': 1, 'y': 2}``.
  * Unit/value variant wrappers self-tag: ``{'__tag__': 'Item', 'value': 7}``.
  * A struct/builtin aliased as a variant is bare on its own, and is wrapped
    ``{'__tag__': name, 'value': <inner>}`` only inside a union-typed field.
  * Monads carry a ``__tag__`` (``Ok``/``Error``/``Some``/``Nothing``/``Valid``/
    ``Invalid``/``Many``). ``Effect`` is not serializable.

``from_dict`` is target-directed and honours parameterized targets, so e.g.
``from_dict(Many[Box], data)`` reconstructs each element as a ``Box`` variant.
"""

from __future__ import annotations

import json as _json
import types as _types
from typing import Any, TypeVar, Union, get_args, get_origin

from stolas.types import Effect, Error, Invalid, Many, Ok, Some, Valid
from stolas.types.option import Nothing, _Nothing

__all__ = ["to_dict", "from_dict", "variant_from_dict", "to_json", "from_json"]

_NO_MATCH: Any = object()


# --------------------------------------------------------------------- to_dict


def to_dict(value: Any) -> Any:
    """Convert a stolas value to JSON-native data (dict/list/str/int/float/bool/None)."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    tagged = _self_tag(value)
    if tagged is not None:
        return tagged

    if getattr(type(value), "__stolas_struct__", False):
        return _struct_to_dict(value)

    monad = _monad_to_dict(value)
    if monad is not _NO_MATCH:
        return monad

    if isinstance(value, Effect):
        raise TypeError(
            "Effect is not serializable; run it and serialize the result instead"
        )

    if isinstance(value, (list, tuple, set)):
        return [to_dict(item) for item in value]

    if isinstance(value, dict):
        return {_str_key(k): to_dict(v) for k, v in value.items()}

    raise TypeError(f"Cannot serialize value of type {type(value).__name__!r}")


def _self_tag(value: Any) -> Any:
    """Tag a standalone unit/value @cases wrapper variant; None if not one."""
    tag = getattr(type(value), "__tag__", None)
    if tag is None:
        return None
    if hasattr(value, "_value"):
        return {"__tag__": tag, "value": to_dict(value._value)}
    return {"__tag__": tag}


def _struct_to_dict(value: Any) -> dict[str, Any]:
    return {
        name: _encode_field(getattr(value, name), ftype)
        for name, ftype in _struct_fields(type(value))
    }


def _encode_field(value: Any, declared: Any) -> Any:
    if _is_cases_union(declared):
        return _encode_cases(value, declared)
    return to_dict(value)


def _encode_cases(value: Any, union: Any) -> Any:
    name = union._variant_names.get(type(value))
    if (
        name is None
    ):  # pragma: no cover - defensive; validated field values are registered
        return to_dict(value)
    kind = union._variant_kinds[name]
    if kind == "unit":
        return {"__tag__": name}
    if kind == "value":
        return {"__tag__": name, "value": to_dict(value._value)}
    return {"__tag__": name, "value": to_dict(value)}


def _monad_to_dict(value: Any) -> Any:
    if isinstance(value, Ok):
        return {"__tag__": "Ok", "value": to_dict(value.value)}
    if isinstance(value, Error):
        return {"__tag__": "Error", "error": to_dict(value.error)}
    if isinstance(value, Some):
        return {"__tag__": "Some", "value": to_dict(value.value)}
    if isinstance(value, _Nothing):
        return {"__tag__": "Nothing"}
    if isinstance(value, Valid):
        return {"__tag__": "Valid", "value": to_dict(value.value)}
    if isinstance(value, Invalid):
        return {"__tag__": "Invalid", "errors": [to_dict(e) for e in value.errors]}
    if isinstance(value, Many):
        return {"__tag__": "Many", "items": [to_dict(item) for item in value.items]}
    return _NO_MATCH


def _str_key(key: Any) -> str:
    if not isinstance(key, str):
        raise TypeError(
            f"dict keys must be str to serialize, got {type(key).__name__!r}"
        )
    return key


# ------------------------------------------------------------------- from_dict


def from_dict(target: Any, data: Any) -> Any:
    """Reconstruct a value of type ``target`` from JSON-native ``data``."""
    if target is Any:
        return data

    if _is_cases_union(target):
        return _from_cases(target, data)

    if isinstance(target, type) and getattr(target, "__stolas_struct__", False):
        return _from_struct(target, data)

    monad = _from_monad(target, data)
    if monad is not _NO_MATCH:
        return monad

    origin = get_origin(target)
    if origin is not None:
        return _from_generic(target, data, origin)

    return data


def _from_struct(target: Any, data: Any) -> Any:
    if not isinstance(data, dict):
        raise TypeError(
            f"Expected dict to build {target.__name__}, got {type(data).__name__}"
        )
    fields = _struct_fields(target)
    names = {name for name, _ in fields}
    extra = set(data) - names
    if extra:
        raise TypeError(f"Unknown fields for {target.__name__}: {sorted(extra)}")
    kwargs = {
        name: from_dict(ftype, data[name]) for name, ftype in fields if name in data
    }
    return target(**kwargs)


def _from_cases(union: Any, data: Any) -> Any:
    if not (isinstance(data, dict) and "__tag__" in data):
        raise ValueError(f"Expected a tagged dict with '__tag__' for {union.__name__}")
    name = data["__tag__"]
    kinds = union._variant_kinds
    if name not in kinds:
        raise ValueError(
            f"Unknown variant {name!r} for {union.__name__}; "
            f"expected one of {sorted(kinds)}"
        )
    kind = kinds[name]
    if kind == "unit":
        return getattr(union, name)
    if "value" not in data:
        raise ValueError(
            f"Variant {name!r} of {union.__name__} requires a 'value' field"
        )
    if kind == "value":
        return union._variants[name](from_dict(Any, data["value"]))
    return from_dict(union._variants[name], data["value"])


def variant_from_dict(cls: Any, data: Any) -> Any:
    """Reconstruct a single ``@cases`` variant instance from ``data``.

    Complements :func:`from_dict`: use it when you already hold the concrete
    variant class (e.g. ``Box.Item``) rather than the union. ``cls`` may be a
    value-variant class, a unit variant (its class or its singleton instance),
    or an existing-class variant (a ``@struct`` or builtin aliased as a variant).

    The payload matches what :func:`to_dict` emits for a standalone variant:
    ``{'__tag__': name, 'value': ...}`` for a value variant, ``{'__tag__': name}``
    for a unit variant, and the bare encoding for an existing-class variant. A
    present ``__tag__`` that names a different variant raises ``ValueError``.
    """
    variant = cls if isinstance(cls, type) else type(cls)
    tag = getattr(variant, "__tag__", None)

    if tag is None:
        # Existing-class variant (a @struct/builtin aliased as a variant): the
        # payload is the bare encoding, so reconstruct it directly.
        return from_dict(variant, data)

    if isinstance(data, dict) and "__tag__" in data and data["__tag__"] != tag:
        raise ValueError(f"Tag {data['__tag__']!r} does not match variant {tag!r}")

    if "_value" in getattr(variant, "__slots__", ()):
        # Value variant: unwrap the tagged ``value`` payload.
        if not (isinstance(data, dict) and "value" in data):
            raise ValueError(f"Variant {tag!r} requires a 'value' field")
        return variant(from_dict(Any, data["value"]))

    # Unit variant: the singleton carries no payload.
    return variant()


def _from_monad(target: Any, data: Any) -> Any:
    kinds = _monad_kinds(target)
    if kinds is None:
        return _NO_MATCH
    if not (isinstance(data, dict) and "__tag__" in data):
        raise TypeError(
            f"Expected a tagged dict for monad target, got {type(data).__name__}"
        )
    tag = data["__tag__"]
    if tag not in kinds:
        raise ValueError(
            f"Tag {tag!r} invalid for target; expected one of {sorted(kinds)}"
        )
    return _build_monad(tag, data, _monad_inner_target(target, tag))


def _build_monad(tag: str, data: Any, inner: Any) -> Any:
    if tag == "Ok":
        return Ok(from_dict(inner, data["value"]))
    if tag == "Error":
        return Error(from_dict(inner, data["error"]))
    if tag == "Some":
        return Some(from_dict(inner, data["value"]))
    if tag == "Nothing":
        return Nothing
    if tag == "Valid":
        return Valid(from_dict(inner, data["value"]))
    if tag == "Invalid":
        return Invalid([from_dict(Any, e) for e in data["errors"]])
    return Many([from_dict(inner, item) for item in data["items"]])


def _from_generic(target: Any, data: Any, origin: Any) -> Any:
    args = get_args(target)
    if origin is Union or origin is _types.UnionType:
        if data is None:
            return None
        members = [a for a in args if a is not type(None)]
        if len(members) == 1:
            return from_dict(members[0], data)
        return data
    if origin in (list, set):
        elem = args[0] if args else Any
        return origin(from_dict(elem, item) for item in data)
    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(from_dict(args[0], item) for item in data)
        if args:
            return tuple(from_dict(a, item) for a, item in zip(args, data))
        return tuple(data)  # pragma: no cover - arg-less tuple origin
    if origin is dict:
        vt = args[1] if len(args) == 2 else Any
        return {k: from_dict(vt, v) for k, v in data.items()}
    return data  # pragma: no cover - unsupported generic origin falls through


# ---------------------------------------------------------------------- helpers


def _struct_fields(cls: Any) -> tuple[tuple[str, Any], ...]:
    fields = getattr(cls, "__stolas_fields__", None)
    if fields is not None:
        return fields  # type: ignore[no-any-return]
    return tuple(  # pragma: no cover - every @struct sets __stolas_fields__
        (name, Any) for name in cls.__slots__
    )


def _is_cases_union(target: Any) -> bool:
    return hasattr(target, "_variant_names") and hasattr(target, "_variant_kinds")


_MONAD_TAG_BY_TYPE: dict[type, str] = {
    Ok: "Ok",
    Error: "Error",
    Some: "Some",
    _Nothing: "Nothing",
    Valid: "Valid",
    Invalid: "Invalid",
    Many: "Many",
}


def _concrete_monad_tag(t: Any) -> str | None:
    origin = get_origin(t)
    base = origin if origin is not None else t
    if isinstance(base, type):
        return _MONAD_TAG_BY_TYPE.get(base)
    return None


def _monad_kinds(target: Any) -> set[str] | None:
    direct = _concrete_monad_tag(target)
    if direct is not None:
        return {direct}
    origin = get_origin(target)
    if origin is Union or origin is _types.UnionType:
        kinds = {k for k in (_concrete_monad_tag(m) for m in get_args(target)) if k}
        return kinds or None
    return None


def _monad_inner_target(target: Any, tag: str) -> Any:
    candidates = [target]
    origin = get_origin(target)
    if origin is Union or origin is _types.UnionType:
        candidates = list(get_args(target))
    for candidate in candidates:
        if _concrete_monad_tag(candidate) == tag:
            args = get_args(candidate)
            if args and not isinstance(args[0], TypeVar):
                return args[0]
            return Any
    return Any  # pragma: no cover - tag is verified against kinds upstream


# ------------------------------------------------------------------------- json


def to_json(value: Any, **kwargs: Any) -> str:
    """Serialize a stolas value to a JSON string (stdlib ``json``)."""
    return _json.dumps(to_dict(value), **kwargs)


def from_json(target: Any, text: str | bytes | bytearray, **kwargs: Any) -> Any:
    """Deserialize a JSON string into a value of type ``target``."""
    return from_dict(target, _json.loads(text, **kwargs))
