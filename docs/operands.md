# Operands

Operands are decorators and utilities for transforming functions.

---

## @cases (Algebraic Data Types)

Creates **sealed sum types** (discriminated unions), similar to Rust enums.

### Import

```python
from stolas.operand import cases
```

### Basic Usage

```python
@cases
class PaymentStatus:
    Pending: None           # Unit variant (no data)
    Authorized: float       # Value variant (carries amount)
    Failed: str             # Value variant (carries reason)
```

### Variant Types

| Annotation | Variant Type | Usage |
|------------|--------------|-------|
| `None` | Unit (singleton) | `PaymentStatus.Pending` |
| `SomeType` | Value wrapper | `PaymentStatus.Authorized(50.0)` |
| Existing class | Alias | Reuses the class directly |

### Creating Variants

```python
# Unit variant (singleton, no parentheses)
pending = PaymentStatus.Pending

# Value variants (call with value)
authorized = PaymentStatus.Authorized(100.0)
failed = PaymentStatus.Failed("Insufficient funds")
```

### Pattern Matching (Python 3.10+)

```python
match status:
    case PaymentStatus.Pending:
        print("Waiting...")
    case PaymentStatus.Authorized(amount):
        print(f"Paid ${amount}")
    case PaymentStatus.Failed(reason):
        print(f"Error: {reason}")
```

### Variant Properties

Value variants have a `.value` property:

```python
PaymentStatus.Authorized(50.0).value  # 50.0
```

### Immutability

All variants are immutable:

```python
status = PaymentStatus.Authorized(50.0)
status._value = 100.0  # ❌ AttributeError
```

### Pipeline Operator

Value variants support `>>`:

```python
PaymentStatus.Authorized(50.0) >> (lambda x: x * 2)  # 100.0
```

Unit variants return themselves:

```python
PaymentStatus.Pending >> (lambda x: x * 2)  # PaymentStatus.Pending
```

### Internal API

| Attribute | Description |
|-----------|-------------|
| `cls._variants` | Dict mapping variant names to their classes |
| `cls._union` | Union type of all variants |

---

## Safe Decorators

Convert exception-raising functions into monadic returns.

### Import

```python
from stolas.operand import as_result, as_option, as_validated, as_many, as_effect
```

### @as_result

Catches exceptions and returns `Result[T, Exception]`.

```python
@as_result
def divide(a: int, b: int) -> float:
    return a / b

divide(10, 2)   # Ok(5.0)
divide(10, 0)   # Error(ZeroDivisionError('division by zero'))
```

**With Curried functions**: Wraps the final execution.

```python
from stolas.operand import binary

@as_result
@binary
def safe_divide(a: int, b: int) -> float:
    return a / b

safe_divide(10)(0)  # Error(ZeroDivisionError(...))
```

### @as_option

Returns `Nothing` on `None` or exception.

```python
@as_option
def find_user(id: int) -> dict | None:
    return {"name": "Alice"} if id == 1 else None

find_user(1)  # Some({'name': 'Alice'})
find_user(99) # Nothing
```

### @as_validated

Returns `Valid[T]` or `Invalid[Exception]`.

```python
@as_validated
def parse_age(s: str) -> int:
    return int(s)

parse_age("25")   # Valid(25)
parse_age("abc")  # Invalid([ValueError(...)])
```

### @as_many

Wraps an iterable-returning function in `Many`.

```python
@as_many
def get_items() -> list[int]:
    return [1, 2, 3]

get_items()  # Many([1, 2, 3])
```

### @as_effect

Defers execution until `.run()`.

```python
@as_effect
def greet(name: str) -> str:
    print(f"Hello, {name}!")
    return f"Greeted {name}"

eff = greet("Alice")  # Nothing printed yet
eff.run()             # Prints "Hello, Alice!", returns "Greeted Alice"
```

---

## Arity Decorators

Control function arity (currying).

### Import

```python
from stolas.operand import unary, binary, ternary, quaternary
```

### @binary

Curries a 2-argument function:

```python
@binary
def add(a: int, b: int) -> int:
    return a + b

add(1)(2)      # 3
add(1, 2)      # 3 (also works)
add_one = add(1)
add_one(5)     # 6
```

### @unary / @ternary / @quaternary

Same pattern for 1, 3, and 4 arguments.

---

## @ops (Decorator Composition)

Compose multiple decorators.

### Import

```python
from stolas.operand import ops
```

### Usage

```python
@ops(binary, as_result)
def divide(a: int, b: int) -> float:
    return a / b

# Equivalent to:
# @binary
# @as_result
# def divide...
```

Decorators are applied **left-to-right** (outermost first).

---

## concurrent

Run async functions in parallel.

### Import

```python
from stolas.operand import concurrent
```

### Usage

```python
async def fetch_name(user_id: int) -> str:
    return f"User {user_id}"

async def fetch_email(user_id: int) -> str:
    return f"user{user_id}@example.com"

# Create parallel runner
parallel_fetch = concurrent(fetch_name, fetch_email)

# Use in pipeline
result = Ok(1) >> parallel_fetch
# Ok(Effect(<awaitable>))

# Execute
import asyncio
effect = result.unwrap()
names = asyncio.run(effect.run())
# ('User 1', 'user1@example.com')
```

### Signature

```python
def concurrent(
    *funcs: Callable[[T], Awaitable[U]]
) -> Callable[[T], Effect[Awaitable[tuple[U, ...]]]]
```

**Returns**: A function that takes a single input, runs all async functions in parallel on it, and returns an `Effect` wrapping the awaitable tuple of results.

---

## Decorator Summary

| Decorator | Input | Output |
|-----------|-------|--------|
| `@as_result` | `Callable[..., T]` | `Callable[..., Result[T, Exception]]` |
| `@as_option` | `Callable[..., T \| None]` | `Callable[..., Option[T]]` |
| `@as_validated` | `Callable[..., T]` | `Callable[..., Validated[T, Exception]]` |
| `@as_many` | `Callable[..., Iterable[T]]` | `Callable[..., Many[T]]` |
| `@as_effect` | `Callable[..., T]` | `Callable[..., Effect[T]]` |
| `@binary` | 2-arg function | Curried function |
| `@ops(d1, d2, ...)` | Function | Function with all decorators applied |
