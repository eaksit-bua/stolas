# Monadic Types

Stolas provides five core monadic containers for safe, composable programming.

---

## Result[T, E]

Represents success (`Ok[T]`) or failure (`Error[E]`). Replaces exceptions for expected errors.

### Import

```python
from stolas.types import Result, Ok, Error
```

### Creating Results

```python
success: Result[int, str] = Ok(42)
failure: Result[int, str] = Error("Something went wrong")
```

### Ok[T] Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `value` | `@property -> T` | Access the contained value |
| `map(func)` | `Callable[[T], U] -> Ok[U]` | Transform value: `Ok(2).map(lambda x: x * 2) -> Ok(4)` |
| `map_err(func)` | `Callable[[E], F] -> Ok[T]` | No-op, returns self |
| `bind(func)` | `Callable[[T], Result[U, E]] -> Result[U, E]` | Chain with Result-returning function |
| `unwrap()` | `-> T` | Get value or raise if Error |
| `unwrap_or(default)` | `T -> T` | Get value or return default |
| `unwrap_err()` | `-> Never` | Always raises `ValueError` |
| `is_ok()` | `-> bool` | Returns `True` |
| `is_error()` | `-> bool` | Returns `False` |

### Error[E] Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `error` | `@property -> E` | Access the contained error |
| `map(func)` | `Callable[[Any], Any] -> Error[E]` | No-op, returns self |
| `map_err(func)` | `Callable[[E], F] -> Error[F]` | Transform error: `Error("x").map_err(str.upper) -> Error("X")` |
| `bind(func)` | `Callable[[Any], Any] -> Error[E]` | No-op, returns self |
| `unwrap()` | `-> Never` | Always raises `ValueError` |
| `unwrap_or(default)` | `T -> T` | Returns the default |
| `unwrap_err()` | `-> E` | Get the error value |
| `is_ok()` | `-> bool` | Returns `False` |
| `is_error()` | `-> bool` | Returns `True` |

### Pipeline Operator `>>`

The `>>` operator chains operations. On `Ok`, it unwraps, calls the function, and re-wraps:

```python
Ok(10) >> (lambda x: x * 2)  # Ok(20)
Ok(10) >> (lambda x: Error("fail"))  # Error("fail")
Error("bad") >> (lambda x: x * 2)  # Error("bad") - skipped
```

### Pattern Matching

```python
match result:
    case Ok(value):
        print(f"Success: {value}")
    case Error(error):
        print(f"Failed: {error}")
```

---

## Option[T]

Represents presence (`Some[T]`) or absence (`Nothing`). Replaces `None` checks.

### Import

```python
from stolas.types import Option, Some, Nothing
```

### Creating Options

```python
present: Option[int] = Some(42)
absent: Option[int] = Nothing  # Singleton
```

### Some[T] Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `value` | `@property -> T` | Access the contained value |
| `map(func)` | `Callable[[T], U] -> Some[U]` | Transform: `Some(2).map(str) -> Some("2")` |
| `bind(func)` | `Callable[[T], Option[U]] -> Option[U]` | Chain with Option-returning function |
| `unwrap()` | `-> T` | Get value |
| `unwrap_or(default)` | `T -> T` | Get value (default ignored) |
| `is_some()` | `-> bool` | Returns `True` |
| `is_nothing()` | `-> bool` | Returns `False` |

### Nothing Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `map(func)` | `-> Nothing` | No-op, returns self |
| `bind(func)` | `-> Nothing` | No-op, returns self |
| `unwrap()` | `-> Never` | Raises `ValueError` |
| `unwrap_or(default)` | `T -> T` | Returns the default |
| `is_some()` | `-> bool` | Returns `False` |
| `is_nothing()` | `-> bool` | Returns `True` |

### Pipeline Operator

```python
Some(10) >> (lambda x: x * 2)  # Some(20)
Nothing >> (lambda x: x * 2)   # Nothing - skipped
```

---

## Validated[T, E]

Like `Result`, but **accumulates all errors** instead of short-circuiting. Ideal for form validation.

### Import

```python
from stolas.types import Validated, Valid, Invalid
```

### Creating Validated

```python
valid: Validated[int, str] = Valid(42)
invalid: Validated[int, str] = Invalid("Too short")
invalid_multi: Validated[int, str] = Invalid(["Error 1", "Error 2"])
```

### Valid[T] Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `value` | `@property -> T` | Access the contained value |
| `map(func)` | `Callable[[T], U] -> Valid[U]` | Transform value |
| `is_valid()` | `-> bool` | Returns `True` |
| `is_invalid()` | `-> bool` | Returns `False` |
| `combine(other)` | `Validated[U, E] -> Validated[tuple[T, U], E]` | Combine two Valids into tuple |

### Invalid[E] Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `errors` | `@property -> tuple[E, ...]` | Access error tuple |
| `map(func)` | `-> Invalid[E]` | No-op, returns self |
| `is_valid()` | `-> bool` | Returns `False` |
| `is_invalid()` | `-> bool` | Returns `True` |
| `combine(other)` | `Validated[Any, E] -> Invalid[E]` | Accumulate errors from both |

### Error Accumulation

```python
v1 = Invalid("Name required")
v2 = Invalid("Email invalid")
v3 = Valid(18)

combined = v1.combine(v2).combine(v3)
# Invalid(['Name required', 'Email invalid'])
```

---

## Many[T]

Collection monad for **functional list processing**.

### Import

```python
from stolas.types import Many
```

### Creating Many

```python
items = Many([1, 2, 3, 4, 5])
single = Many.pure(42)      # Many([42])
empty = Many.empty()        # Many([])
```

### Many[T] Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `items` | `@property -> tuple[T, ...]` | Access underlying tuple |
| `map(func)` | `Callable[[T], U] -> Many[U]` | Transform each element |
| `bind(func)` | `Callable[[T], Many[U]] -> Many[U]` | FlatMap: transform and flatten |
| `filter(pred)` | `Callable[[T], bool] -> Many[T]` | Keep matching elements |
| `first()` | `-> Option[T]` | First element as `Some`, or `Nothing` if empty |
| `last()` | `-> Option[T]` | Last element as `Some`, or `Nothing` if empty |
| `count()` | `-> Some[int]` | Count wrapped in `Some` |
| `is_empty()` | `-> bool` | Check if empty |

### Class Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `Many.pure(value)` | `T -> Many[T]` | Wrap single value |
| `Many.empty()` | `-> Many[T]` | Create empty Many |

### Pipeline with Logic Combinators

```python
from stolas.logic import where, apply, _

Many([1, 2, 3, 4, 5]) >> where(_ > 2) >> apply(_ * 10)
# Many([30, 40, 50])
```

### Iteration Support

```python
for item in Many([1, 2, 3]):
    print(item)

len(Many([1, 2, 3]))  # 3
```

---

## Effect[T]

Lazy evaluation monad for **deferred side effects**.

### Import

```python
from stolas.types import Effect
```

### Creating Effects

```python
# Wrap a thunk (zero-argument callable)
eff = Effect(lambda: print("Hello"))

# Defer a function call
eff = Effect.defer(print, "Hello", "World")

# Wrap a pure value
eff = Effect.pure(42)
```

### Effect[T] Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `thunk` | `@property -> Callable[[], T]` | Access the wrapped callable |
| `run()` | `-> T` | Execute the effect and return result |
| `map(func)` | `Callable[[T], U] -> Effect[U]` | Transform eventual result (lazy) |
| `bind(func)` | `Callable[[T], Effect[U]] -> Effect[U]` | Chain effects (lazy, flattening) |

### Static Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `Effect.pure(value)` | `T -> Effect[T]` | Wrap pure value in Effect |
| `Effect.defer(func, *args, **kwargs)` | `-> Effect[T]` | Create Effect from function call |

### Lazy Execution

Nothing happens until `.run()`:

```python
eff = Effect.defer(print, "Side effect!")
# No output yet

eff.run()  
# "Side effect!" printed now
```

### Composing Effects

```python
read_file = Effect.defer(open, "data.txt")
parse_json = lambda f: Effect.defer(json.load, f)

pipeline = read_file.bind(parse_json)
# Nothing executed yet

data = pipeline.run()  # Now reads and parses
```

### Pipeline Operator

```python
Effect.pure(10) >> (lambda x: x * 2)
# Effect that will return 20 when run
```

---

## Type Aliases

```python
from stolas.types import Result, Option, Validated

# These are Union type aliases:
Result = Ok[T] | Error[E]
Option = Some[T] | _Nothing
Validated = Valid[T] | Invalid[E]
```
