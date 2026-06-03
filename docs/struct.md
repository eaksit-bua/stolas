# Struct & Trait

Stolas provides a high-performance system for immutable data and decoupled behavior.

---

## @struct

The `@struct` decorator creates **strict, immutable** data classes optimized for performance.

### Import

```python
from stolas.struct import struct
```

### Basic Usage

```python
@struct
class User:
    id: int
    name: str
    active: bool = True  # Default value

# Create instance (keyword-only!)
u = User(id=1, name="Alice")

# Access fields
print(u.id)      # 1
print(u.name)    # "Alice"
print(u.active)  # True
```

### Immutability

Structs are **frozen** after creation. Any attempt to mutate raises `AttributeError`:

```python
u.name = "Bob"   # ❌ AttributeError: Struct is immutable
del u.id         # ❌ AttributeError: Struct is immutable
```

### Runtime Type Validation

Field types are **validated at construction time**:

```python
User(id="wrong", name="Alice")
# ❌ TypeError: Field 'id' expects int, got str
```

### Required vs Optional Fields

Fields without defaults are **required**:

```python
User(name="Alice")  
# ❌ TypeError: Missing required fields: {'id'}

User(id=1, name="Alice", unknown=True)  
# ❌ TypeError: Unknown fields: {'unknown'}
```

### Value Validation — `__validators__`

Type checks confirm a field has the right *type*; to enforce a field's *value*
(non-empty, in range, matching a pattern, ...), declare an opt-in class attribute
`__validators__: dict[str, Validator]`. Type errors are still raised first; value
failures are then aggregated into a single `ValueError`. A struct without
`__validators__` is byte-identical to before (zero overhead):

```python
from stolas.validation import all_of, non_empty, between

@struct
class User:
    id: int
    name: str
    __validators__ = {
        "name": all_of(non_empty()),
        "id": between(1, 9999),
    }

User(id=0, name="")   # ❌ ValueError: id: must be between 1 and 9999; name: must not be empty
```

See **[Validation](validation.md)** for the full validator library, the
TypeError-then-ValueError ordering, and the email-via-`matches()` recipe.

### Auto-Generated Methods

Every `@struct` automatically provides:

| Method | Behavior |
|--------|----------|
| `__init__` | Keyword-only constructor with validation |
| `__repr__` | `User(id=1, name='Alice', active=True)` |
| `__eq__` | Value-based equality (`u1 == u2` if all fields match) |
| `__hash__` | Hash based on field values (usable in sets/dicts) |
| `__rshift__` | Pipeline operator `u >> func` calls `func(u)` |
| `__match_args__` | Pattern matching support |
| `__slots__` | Memory-optimized storage |

### Pipeline Operator

```python
def greet(user: User) -> str:
    return f"Hello, {user.name}!"

User(id=1, name="Alice") >> greet  # "Hello, Alice!"
```

### Pattern Matching (Python 3.10+)

```python
match User(id=1, name="Alice"):
    case User(id=id, name=name):
        print(f"User #{id}: {name}")
```

### Copy with Changes — `replace()`

Frozen data needs an ergonomic way to produce a modified copy. `replace()` returns a **new** instance with the given fields overridden and all others copied across, re-running validation. The original is never mutated:

```python
from stolas.struct import struct, replace

@struct
class User:
    id: int
    name: str
    active: bool = True

u = User(id=1, name="Alice")

replace(u, name="Bob")     # User(id=1, name='Bob', active=True)
u.replace(name="Bob")      # method form — identical
u                          # unchanged: User(id=1, name='Alice', active=True)

replace(u, id="x")         # ❌ TypeError: re-validated, 'id' expects int
replace(u, role="admin")   # ❌ TypeError: Unknown fields: {'role'}
```

> The free function `replace(instance, **changes)` is the fully type-checked entry point. The `.replace()` method is a convenience and is not installed when a field is literally named `replace`.

### Serialization — `to_dict` / `from_dict` / JSON

Structs convert to and from plain JSON-native data via `stolas.serde`. Conversion is **recursive** (nested structs, monads, `@cases` variants, containers) and **type-directed** on the way back:

```python
from stolas.serde import to_dict, from_dict, to_json, from_json

@struct
class User:
    id: int
    name: str

u = User(id=1, name="Alice")

to_dict(u)                                     # {'id': 1, 'name': 'Alice'}
from_dict(User, {'id': 1, 'name': 'Alice'})    # User(id=1, name='Alice')

to_json(u, indent=2)                           # JSON string (stdlib json)
from_json(User, '{"id": 1, "name": "Alice"}')  # User(id=1, name='Alice')
```

Unknown keys are rejected (`TypeError`); missing keys fall back to field defaults. Nested fields recurse automatically. See **[Monadic Types](types.md)** for how monads and `@cases` variants serialize (the `__tag__` discriminator).

### Inheritance Blocked

Structs cannot be subclassed:

```python
@struct
class Admin(User):  # ❌ TypeError: Cannot inherit from struct
    role: str
```

This is the **default** (`open=False`). The generated class installs an
`__init_subclass__` guard that raises on any subclass. To opt out, see
`@struct(open=True)` below.

### `@struct(open=True)` — opting in to subclassing

`@struct` is a **dual-form** decorator: use it bare as `@struct` (the default,
`open=False`) or called as `@struct(open=True)`. The call form relaxes **exactly
one thing** — the inheritance guard — so subclasses are permitted:

```python
from stolas.struct import struct

@struct(open=True)
class Base:
    id: int

class Tagged(Base):     # ✅ permitted — no "Cannot inherit from struct"
    pass
```

What `open=True` does **not** change: the base struct stays frozen,
`__slots__`-only, runtime-type-checked at construction, and keeps every
auto-generated method (`__repr__`, `__eq__`, `__hash__`, `>>`, `.replace()`,
`__match_args__`). The base itself is still immutable:

```python
b = Base(id=1)
b.id = 2     # ❌ AttributeError: Struct is immutable
```

`open=False` (bare `@struct`) is **byte-identical** to the historical behavior —
same generated namespace, same repr / eq / hash / slots, same inheritance block.
You pay nothing for the feature unless you opt in.

The bundled **mypy plugin still fires** for the call form: `@struct(open=True)`
resolves to the same callee the plugin already matches, so `instance >> func` and
`.replace()` stay precisely typed on open structs too, and a positional argument to
an open struct's constructor is still a mypy error. See
**[Typing Model](typing.md#the-mypy-plugin)**.

> [!CAUTION]
> **Soundness gap: a mutable subclass vs. the frozen stub.** `open=True` only
> *permits* subclassing — it cannot police what a subclass does. A subclass can
> override `__setattr__` (or otherwise reintroduce state) and become mutable, even
> though the `dataclass_transform(frozen_default=True)` stub still types the whole
> hierarchy as frozen:
>
> ```python
> @struct(open=True)
> class Base:
>     id: int
>
> class Mutable(Base):
>     def __setattr__(self, k, v):       # subclass re-opens mutation
>         object.__setattr__(self, k, v)
>
> m = Mutable(id=1)
> m.id = 99      # mutates — but the type checker still believes it is frozen
> ```
>
> Stolas does **not** close this gap (it is documented, not solved): the frozen
> guarantee is enforced on the base, not inherited-and-checked on subclasses.
> Treat open structs as data carriers for interop, not as a license to make
> mutable subclasses. If you need a truly frozen type, keep the default closed
> `@struct`.

For why you might need an open struct (subclassing a framework/ORM base) and the
full interop story, see **[Interop](interop.md#structopentrue--opting-in-to-subclassing)**.

---

## @trait

Traits enable **polymorphic dispatch** by separating behavior from data.

### Import

```python
from stolas.struct import trait
```

### Defining a Trait

Define a trait as a function with `@trait`:

```python
@trait
def show(obj) -> str:
    """Convert object to display string."""
    raise NotImplementedError  # Default: no implementation
```

### Registering Implementations

Use `.impl(*types)` to register type-specific implementations:

```python
@show.impl(User)
def show_user(user: User) -> str:
    return f"User({user.name})"

@show.impl(int)
def show_int(n: int) -> str:
    return f"Integer: {n}"

@show.impl(str | bytes)  # Multiple types at once
def show_text(text) -> str:
    return f"Text: {text}"
```

> [!TIP]
> **Avoid using `_` as a parameter name** in trait implementations. The `_` symbol is reserved for the **Placeholder** in `stolas.logic`. Use descriptive names like `user`, `n`, `text`, or `obj` instead.

### Calling a Trait

Call the trait function directly; it dispatches based on the argument's type:

```python
show(User(id=1, name="Alice"))  # "User(Alice)"
show(42)                         # "Integer: 42"
show("hello")                    # "Text: hello"
```

### TraitDispatcher API

| Method | Description |
|--------|-------------|
| `impl(*types)` | Decorator to register an implementation for given types |
| `require(obj)` | Returns `True` if type has implementation, `False` otherwise |
| `check(obj)` | Raises `TypeError` if type has no implementation |
| `types` | Property returning tuple of all registered types |

### Checking Implementation Existence

```python
show.require(User(id=1, name="Alice"))  # True
show.require([1, 2, 3])                  # False (list not registered)

show.check([1, 2, 3])  
# ❌ TypeError: No implementation for type: list
```

### Listing Registered Types

```python
show.types  # (User, int, str, bytes)
```

### MRO-Based Resolution

Trait dispatch respects Python's Method Resolution Order (MRO):

```python
class Animal: pass
class Dog(Animal): pass

@show.impl(Animal)
def show_animal(a) -> str:
    return "Some animal"

show(Dog())  # "Some animal" (Dog inherits from Animal)
```

### Multi-Argument Dispatch

Traits can dispatch on **multiple arguments** by registering implementations with multiple types:

```python
@trait
def interact(a, b) -> str:
    raise NotImplementedError

@interact.impl(Dog, Cat)  # Dispatch on (Dog, Cat)
def dog_chases_cat(d: Dog, c: Cat) -> str:
    return f"{d.name} chases {c.name}"

@interact.impl(Cat, Dog)  # Dispatch on (Cat, Dog)
def cat_hisses_dog(c: Cat, d: Dog) -> str:
    return f"{c.name} hisses at {d.name}"

# Usage
interact(dog, cat)  # "Rex chases Whiskers"
interact(cat, dog)  # "Whiskers hisses at Rex"
```


---

## Comparison with Alternatives

| Feature | `@struct` | `@dataclass(frozen=True)` | `NamedTuple` |
|---------|-----------|---------------------------|--------------|
| Storage | `__slots__` only | `__dict__` or `__slots__` | `__slots__` |
| Memory overhead | ~56 bytes | ~100+ bytes (dict) | ~56 bytes |
| Immutable | ✅ Always | ✅ Frozen | ✅ Always |
| Runtime type check | ✅ | ❌ | ❌ |
| Extra fields blocked | ✅ | ❌ | ✅ |
| Inheritance | ❌ Blocked (opt in via `open=True`) | ✅ Subclassable | ⚠️ Limited |
| Unpacking `a, b = x` | ❌ | ❌ | ✅ |
| Index `x[0]` | ❌ | ❌ | ✅ |
| `asdict()` / `to_dict()` | ✅ `stolas.serde` | ✅ | ✅ `_asdict()` |
| `replace()` | ✅ | ✅ | ✅ `_replace()` |
| IDE support | ⚠️ Partial | ✅ | ✅ |
| Mypy support | ⚠️ Needs plugin | ✅ | ✅ |
| Weakref | ❌ | ✅ | ❌ |
| Pipeline `>>` | ✅ | ❌ | ❌ |

---

## Trait Comparison

| Feature | `@trait` | `@singledispatch` | `Protocol` |
|---------|----------|-------------------|------------|
| Dispatch mechanism | Runtime (type lookup) | Runtime (type lookup) | Static (duck typing) |
| Registration | `@trait.impl(Type)` | `@func.register(Type)` | Implicit (structural) |
| Multi-argument dispatch | ✅ `@impl(A, B)` dispatches on `(A, B)` | ❌ First arg only | N/A |
| Multiple types per impl | ✅ `@impl(A, B, C)` | ❌ One per register | N/A |
| Dispatch on Union | ✅ `int \| float` | ❌ | ✅ |
| MRO resolution | ✅ | ✅ | N/A |
| List registered types | ✅ `.types` | ✅ `.registry` | ❌ |
| Check implementation | ✅ `.require()` / `.check()` | ❌ | `isinstance()` |
| Validate all impls exist | ✅ `.check()` | ❌ | ❌ |
| Missing impl warning | ✅ `MissingImplementationWarning` | ❌ Runtime error | ✅ Mypy |
| Cache dispatch lookup | ✅ | ✅ | N/A |
| External impl | ✅ (add to any type) | ✅ (add to any type) | ❌ (must define on class) |
| Default fallback | ✅ NotImplementedError | ✅ Base function | N/A |
| Mypy support | ⚠️ Needs plugin | ✅ | ✅ |
| Performance | ⚠️ Dict + MRO | ⚠️ Dict + MRO | ✅ No overhead |

