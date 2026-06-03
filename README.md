# 🦉 Stolas

**The strict, multi-paradigm framework enabling pure functional patterns in Python.**

*Wisdom through pure functional patterns* — Safe separation of data and behavior with monadic safety, immutability, and type-safe composition.

## 🦉 The S-T-O-L-A-S Framework

### **S**truct
Fast, immutable data classes with `@struct` and polymorphic `@trait` for behavior dispatch.

### **T**ypes  
Safe monadic containers: `Result`, `Option`, `Validated`, `Effect`, `Many`

### **O**perands
Powerful decorators: `@ops`, `@cases`, `@binary`, `@as_result`, `concurrent()`

### **L**ogic
Ergonomic functional combinators: `get`, `at`, `where`, `apply`, `_` placeholder, and 20+ utilities

### **A-S**
*(Reserved for future expansion)*

## 🦉 Key Features

- ✅ **Strictness**: Runtime type checking + `__slots__` for memory efficiency
- ✅ **Sealed ADTs**: `@cases` decorator with pattern matching and monadic compatibility
- ✅ **Functional Composition**: Pipeline chaining with `>>`
- ✅ **Async Concurrency**: Parallel workflows with `concurrent()`
- ✅ **Polymorphism**: Trait-based dispatch for decoupled behavior
- ✅ **Type Safety**: Full `mypy --strict` compatibility

## 🦉 Installation

```bash
pip install stolas
```

## 🦉 Quick Example

```python
from stolas.struct import struct
from stolas.types import Many
from stolas.operand import binary, as_result, ops
from stolas.logic import where, apply, _

# Immutable data
@struct
class User:
    id: int
    name: str
    email: str

# Safe, curried operations
@ops(binary, as_result)
def divide(a: int, b: int) -> float:
    return a / b

# Functional pipelines with placeholder
users = Many([
    User(id=1, name="Alice", email="alice@example.com"),
    User(id=2, name="Bob", email="bob@example.com"),
])

result = users >> where(_.id > 1) >> apply(_.name)  # Many(["Bob"])

# Monadic safety
divide(10)(2)  # Ok(5.0)
divide(10)(0)  # Error(ZeroDivisionError(...))
```

## 🦉 Documentation

For detailed documentation, see the **[docs/](docs/)** directory:

- **[Struct & Trait](docs/struct.md)** - Polymorphism (`@trait`) and immutable data (`@struct`)
- **[Monadic Types](docs/types.md)** - `Result`, `Option`, `Validated`, `Effect`, `Many`
- **[Operands](docs/operands.md)** - Decorators `@cases`, the `as_*` safe combinators (`as_result`/`as_option`/`as_validated`/`as_many`/`as_effect`), and Concurrency
- **[Logic Reference](docs/logic.md)** - Combinators and Placeholder (`_`)
- **[Validation](docs/validation.md)** - Generic field validators (`rule`, `matches`, `all_of`, ...) and `@struct __validators__`

## 🦉 Testing

```bash
# Run tests
python -m pytest tests/

# Type checking
mypy src/stolas --strict
```

**Status:** 🦉 892 tests passing • 100% coverage • 100% mypy strict compliance

## 🦉 License

MIT License
