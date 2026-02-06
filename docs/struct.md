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

### Inheritance Blocked

Structs cannot be subclassed:

```python
@struct
class Admin(User):  # ❌ TypeError: Cannot inherit from struct
    role: str
```

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

@show.impl(str, bytes)  # Multiple types at once
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

### Union Type Support

```python
@show.impl(int | float)  # Works with union types (Python 3.10+)
def show_number(n) -> str:
    return f"Number: {n}"
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
| Inheritance | ❌ Blocked | ✅ Subclassable | ⚠️ Limited |
| Unpacking `a, b = x` | ❌ | ❌ | ✅ |
| Index `x[0]` | ❌ | ❌ | ✅ |
| `asdict()` | ❌ (manual) | ✅ | ✅ `_asdict()` |
| `replace()` | ❌ (manual) | ✅ | ✅ `_replace()` |
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

