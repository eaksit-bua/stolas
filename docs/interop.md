# Interop

Stolas keeps a **zero runtime dependency** promise, so it ships no built-in
adapters for pydantic, SQLAlchemy, msgspec, or any other library. It does not
need them: interop happens entirely through the free functions already in
`stolas.serde`. A `@struct` (or a `@cases` variant) becomes JSON-native data with
`to_dict` / `to_json`, and any external library that speaks `dict` / JSON can take
it from there. Coming back is the mirror image — feed the external library's
output to `from_dict` / `from_json`.

> [!NOTE]
> **There is deliberately no `stolas[pydantic]` (or `[sqlalchemy]`, `[msgspec]`)
> extra, and no optional-dependency group.** Each adapter is a few lines over
> `to_dict` / `from_dict`, shown below — small enough to keep in your own code
> rather than version against someone else's release cadence. Decision **D11**.

---

## The interop path: `stolas.serde`

The contract is a handful of **free functions** — not methods on `@struct`. This
keeps serialization out of the data type (data stays data) and means the same
four functions cover every stolas value: structs, the monads
(`Result`/`Option`/`Validated`/`Many`), `@cases` variants, and nested containers.

```python
from stolas.serde import to_dict, from_dict, to_json, from_json
```

| Function | Direction | Notes |
|----------|-----------|-------|
| `to_dict(value)` | stolas → JSON-native data | Recursive; `Effect` is not serializable. |
| `from_dict(target, data)` | JSON-native data → stolas | Target-directed; honours parameterized targets. |
| `to_json(value, **kwargs)` | stolas → JSON string | stdlib `json`; passes `**kwargs` through. |
| `from_json(target, text, **kwargs)` | JSON string → stolas | stdlib `json`. |
| `variant_from_dict(cls, data)` | JSON-native data → one `@cases` variant | When you hold the concrete variant, not the union. |

For the full tag scheme (the `__tag__` discriminator, how monads and `@cases`
variants encode), see **[Monadic Types](types.md#serialization)** and
**[Struct & Trait](struct.md#serialization--to_dict--from_dict--json)**. This page
is about crossing the boundary to other libraries.

---

## `variant_from_dict` — reconstruct a single `@cases` variant

`from_dict(Union, data)` reconstructs a variant by reading the `__tag__` to pick
the right one. When you already hold the **concrete variant class** (e.g.
`Box.Item`) rather than the union, use `variant_from_dict(cls, data)`:

```python
from typing import Any
from stolas.operand import cases
from stolas.serde import to_dict, variant_from_dict

@cases
class Box:
    Item: Any      # value variant
    Empty: None    # unit variant

# Round-trip a value variant via its own class:
variant_from_dict(Box.Item, to_dict(Box.Item(7)))   # Box.Item(7)

# The tag is optional when you already named the variant by passing its class:
variant_from_dict(Box.Item, {"value": 9})            # Box.Item(9)

# A unit variant returns its singleton, however you reference it:
variant_from_dict(Box.Empty, to_dict(Box.Empty)) is Box.Empty   # True
```

`cls` may be a **value-variant class**, a **unit variant** (its class or its
singleton instance), or an **existing-class variant** (a `@struct` or builtin
aliased as a variant) — in which case the payload is the bare encoding and is
reconstructed directly:

```python
@cases
class Shape:
    point: Point    # existing-class (struct-backed) variant
    nothing: None

variant_from_dict(Shape.point, {"x": 3, "y": 4})     # Point(x=3, y=4)
```

If the payload carries a `__tag__` that names a *different* variant, that is an
error — the explicit class and the data disagree:

```python
variant_from_dict(Box.Item, {"__tag__": "Empty", "value": 1})
# ❌ ValueError: Tag 'Empty' does not match variant 'Item'
```

Use `from_dict(Box, data)` when the discriminator should *drive* the choice of
variant; use `variant_from_dict(Box.Item, data)` when you already know which one
you want and just need it rebuilt.

---

## Recipes

Every recipe below is the same shape: `to_dict` on the way out, `from_dict` on the
way back, with the third-party library only ever seeing plain `dict` / JSON. None
of them require anything from stolas beyond `stolas.serde`.

### pydantic

A `@struct` round-trips through a `BaseModel` by handing the dict to the model and
reading it back out:

```python
import pydantic
from stolas.serde import to_dict, from_dict
from stolas.struct import struct

@struct
class Point:
    x: int
    y: int

class PointModel(pydantic.BaseModel):
    x: int
    y: int

original = Point(x=1, y=2)
model = PointModel(**to_dict(original))        # validate/coerce in pydantic
restored = from_dict(Point, model.model_dump())  # back to a @struct
assert restored == original
```

`@cases` value variants carry a `__tag__`; map it to a model field with an alias:

```python
class Tagged(pydantic.BaseModel):
    tag: str = pydantic.Field(alias="__tag__")
    value: int

original = Box.Item(7)
model = Tagged(**to_dict(original))                  # {'__tag__': 'Item', 'value': 7}
restored = from_dict(Box, model.model_dump(by_alias=True))
assert restored == original
```

### SQLAlchemy

`to_dict` produces a flat field mapping, which is exactly what a row insert wants;
a returned row mapping goes straight back through `from_dict`:

```python
import sqlalchemy as sa
from stolas.serde import to_dict, from_dict

engine = sa.create_engine("sqlite:///:memory:")
metadata = sa.MetaData()
points = sa.Table(
    "points", metadata,
    sa.Column("x", sa.Integer),
    sa.Column("y", sa.Integer),
)
metadata.create_all(engine)

original = Point(x=3, y=4)
with engine.begin() as conn:
    conn.execute(sa.insert(points).values(**to_dict(original)))
with engine.connect() as conn:
    row = conn.execute(sa.select(points)).mappings().one()

restored = from_dict(Point, dict(row))
assert restored == original
```

### msgspec

`to_dict` / `from_dict` slot on either side of msgspec's fast JSON codec:

```python
import msgspec
from stolas.serde import to_dict, from_dict

original = Point(x=5, y=6)
encoded = msgspec.json.encode(to_dict(original))     # bytes
restored = from_dict(Point, msgspec.json.decode(encoded))
assert restored == original
```

> [!TIP]
> These exact recipes are exercised as integration tests under
> `tests/integration/test_interop_adapters.py`. They `pytest.importorskip` each
> library, so the suite **skips cleanly** when the dependency is not installed —
> no stolas code path depends on any of them.

---

## `@struct(open=True)` — opting in to subclassing

By default `@struct` is **closed**: the generated class installs an
`__init_subclass__` guard that rejects any attempt to inherit from it (see
**[Struct & Trait — Inheritance Blocked](struct.md#inheritance-blocked)**). That is
usually what you want for a value type, but interop sometimes hands you a base
class you cannot avoid subclassing (an ORM declarative base, a framework mixin).
For those cases `@struct` is a **dual-form** decorator: call it as
`@struct(open=True)` to relax *only* the inheritance block.

```python
from stolas.struct import struct

@struct(open=True)
class Base:
    id: int

class Tagged(Base):     # ✅ permitted under open=True
    pass
```

`@struct(open=True)` is documented in full — including the soundness caveat — in
**[Struct & Trait — `@struct(open=True)`](struct.md#structopentrue--opting-in-to-subclassing)**.
The short version:

- `open=True` relaxes **subclassing only**. The base struct itself stays frozen,
  `__slots__`-only, runtime-type-checked, and keeps `>>` / `.replace()`.
- `open=False` (the default) is byte-identical to bare `@struct`.
- The bundled **mypy plugin still fires** for the call form, so `>>` and
  `.replace()` stay typed on `@struct(open=True)` classes.
- There is a **soundness gap**: a subclass can reintroduce mutability while the
  type checker still treats it as frozen. Subclass open structs as data carriers,
  not as a license to mutate.
