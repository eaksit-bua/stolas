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
| `as_result()` | `-> Effect[Result[T, Exception]]` | Wrap so `.run()` yields `Ok`/`Error` (errors-as-values) |
| `to_async()` | `-> AsyncEffect[T]` | Lift into an `AsyncEffect` (see [Bridges](#bridging-effect-and-asynceffect)) |

### Static Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `Effect.pure(value)` | `T -> Effect[T]` | Wrap pure value in Effect |
| `Effect.defer(func, *args, **kwargs)` | `-> Effect[T]` | Create Effect from function call |
| `Effect.attempt(thunk)` | `Callable[[], T] -> Effect[Result[T, Exception]]` | Run `thunk`, capturing failure as a value |

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

### Capturing Failure as a Value: `attempt` / `as_result`

An `Effect` normally lets exceptions escape from `.run()`. To stay in the
errors-as-values world, wrap it so a raised `Exception` becomes an `Error` and a
return value becomes an `Ok`:

```python
from stolas.types import Effect

# Effect.attempt(thunk): run a fresh thunk, capturing failure.
Effect.attempt(lambda: 21 * 2).run()    # Ok(42)
Effect.attempt(lambda: 10 // 0).run()   # Error(ZeroDivisionError('integer division or modulo by zero'))

# .as_result(): wrap an existing Effect the same way.
Effect.defer(int, "42").as_result().run()    # Ok(42)
Effect.defer(int, "nope").as_result().run()
# Error(ValueError("invalid literal for int() with base 10: 'nope'"))
```

`Effect.attempt(thunk)` is exactly `Effect(thunk).as_result()`. Both catch
**`Exception` only** — `BaseException` (e.g. `KeyboardInterrupt`, `SystemExit`)
propagates, so a deliberate interrupt is never swallowed.

---

## AsyncEffect[T]

`AsyncEffect` is the **async sibling** of `Effect` — for deferred work driven by
native `async`/`await`. It is a separate class, not a mode of `Effect`: there is
no free-monad interpreter, just `await`. Instead of a synchronous thunk it wraps a
**factory** that returns a *fresh awaitable on every run*, so the same
`AsyncEffect` can be `.run()` more than once.

### Import

```python
from stolas.types import AsyncEffect
```

### Creating AsyncEffects

```python
import asyncio

async def fetch() -> int:
    return 5

# Wrap a factory (a zero-arg callable returning an awaitable):
eff = AsyncEffect(fetch)

# Defer a coroutine function call:
eff = AsyncEffect.defer(fetch)

# Wrap a pure value:
eff = AsyncEffect.pure(42)
```

### AsyncEffect[T] Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `factory` | `@property -> Callable[[], Awaitable[T]]` | Access the wrapped factory |
| `run()` | `async -> T` | Await a **fresh** awaitable from the factory |
| `map(func)` | `Callable[[T], U] -> AsyncEffect[U]` | Transform eventual result (lazy) |
| `bind(func)` | `Callable[[T], AsyncEffect[U]] -> AsyncEffect[U]` | Chain async effects (lazy, flattening) |
| `as_result()` | `-> AsyncEffect[Result[T, Exception]]` | Wrap so `.run()` yields `Ok`/`Error` |

### Static Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `AsyncEffect.pure(value)` | `T -> AsyncEffect[T]` | Wrap a pure value |
| `AsyncEffect.defer(coro_fn, *args, **kwargs)` | `-> AsyncEffect[T]` | Create from a coroutine function call |
| `AsyncEffect.attempt(coro_fn, *args, **kwargs)` | `-> AsyncEffect[Result[T, Exception]]` | Await `coro_fn(...)`, capturing failure as a value |

### Running and Composing

`.run()` is a coroutine — `await` it (or drive it with `asyncio.run`). Nothing
executes until then, and `map` / `bind` / `>>` compose **without running**:

```python
import asyncio
from stolas.types import AsyncEffect

async def fetch() -> int:
    return 5

eff = AsyncEffect(fetch)

asyncio.run(eff.run())                                  # 5
asyncio.run(eff.map(lambda x: x + 1).run())             # 6
asyncio.run(eff.bind(lambda x: AsyncEffect.pure(x * 10)).run())  # 50
asyncio.run((eff >> (lambda x: x * 100)).run())         # 500
```

### Fresh Awaitable Per Run

A bare coroutine can only be awaited once, so `AsyncEffect` stores a **factory**
and asks it for a new awaitable on each `.run()`. The same effect is therefore
re-runnable:

```python
import asyncio
from stolas.types import AsyncEffect

async def gen() -> int:
    return 1

eff = AsyncEffect(gen)
asyncio.run(eff.run())   # 1
asyncio.run(eff.run())   # 1 (a fresh awaitable, not a reused, exhausted one)
```

### Capturing Failure as a Value

`attempt` / `as_result` mirror their `Effect` counterparts:

```python
import asyncio
from stolas.types import AsyncEffect

async def add(a: int, b: int) -> int:
    return a + b

async def boom() -> int:
    raise ValueError("nope")

asyncio.run(AsyncEffect.attempt(add, 1, 2).run())   # Ok(3)
asyncio.run(AsyncEffect.attempt(boom).run())        # Error(ValueError('nope'))
asyncio.run(AsyncEffect.defer(boom).as_result().run())  # Error(ValueError('nope'))
```

These catch **`Exception` only**. In particular `asyncio.CancelledError` is a
`BaseException` and is **never** captured — it always propagates, so cancellation
still tears the task down as expected:

```python
import asyncio
from stolas.types import AsyncEffect

async def cancelled() -> int:
    raise asyncio.CancelledError()

async def main() -> str:
    try:
        await AsyncEffect.defer(cancelled).as_result().run()
    except asyncio.CancelledError:
        return "propagated"
    return "swallowed"

asyncio.run(main())   # 'propagated'
```

---

## Bridging `Effect` and `AsyncEffect`

Three bridges connect the synchronous and asynchronous worlds.

### Import

```python
from stolas.types import from_effect, to_effect
# plus the Effect.to_async() method
```

### `Effect.to_async()` / `from_effect(effect)` — sync → async

Both lift a synchronous `Effect` into an `AsyncEffect` (running the original thunk
inside an `async` factory). `from_effect(effect)` is the module-level form of
`effect.to_async()`:

```python
import asyncio
from stolas.types import Effect, from_effect

ae = Effect.pure(7).to_async()
asyncio.run(ae.run())             # 7

ae = from_effect(Effect.pure(42))
asyncio.run(ae.run())             # 42
```

### `to_effect(ae)` — async → sync

`to_effect(ae)` returns an `Effect` whose `.run()` drives the awaitable to
completion via `asyncio.run`:

```python
from stolas.types import AsyncEffect, to_effect

eff = to_effect(AsyncEffect.pure(8))
eff.run()   # 8
```

> [!CAUTION]
> **`to_effect` cannot run inside an already-running event loop.** Because it calls
> `asyncio.run` internally, invoking the returned effect's `.run()` from within a
> running loop raises a clear `RuntimeError`. When you are already inside `async`
> code, `await` the `AsyncEffect` directly (`await ae.run()`) instead of bridging
> back to a sync `Effect`.
>
> ```python
> import asyncio
> from stolas.types import AsyncEffect, to_effect
>
> async def main() -> str:
>     try:
>         to_effect(AsyncEffect.pure(1)).run()   # inside a running loop
>     except RuntimeError as exc:
>         return str(exc)
>     return "ran"
>
> asyncio.run(main())
> # 'to_effect cannot run inside a running event loop; await the AsyncEffect
> #  directly (e.g. `await ae.run()`) instead.'
> ```

See **[Control](control.md)** for `bracket` / `retry` / `timeout` built on these
two effect types.

---

## Type Aliases

```python
from stolas.types import Result, Option, Validated

# These are Union type aliases:
Result = Ok[T] | Error[E]
Option = Some[T] | _Nothing
Validated = Valid[T] | Invalid[E]
```

---

## Serialization

Every monad converts to JSON-native data via `stolas.serde`, carrying a `__tag__`
discriminator so the variant round-trips. Reconstruction is **target-directed** —
you pass the type alias (or a parameterized one) to `from_dict`:

```python
from stolas.serde import to_dict, from_dict

to_dict(Ok(5))            # {'__tag__': 'Ok', 'value': 5}
to_dict(Error("boom"))    # {'__tag__': 'Error', 'error': 'boom'}
to_dict(Some(7))          # {'__tag__': 'Some', 'value': 7}
to_dict(Nothing)          # {'__tag__': 'Nothing'}
to_dict(Valid(1))         # {'__tag__': 'Valid', 'value': 1}
to_dict(Invalid(["e"]))   # {'__tag__': 'Invalid', 'errors': ['e']}
to_dict(Many([1, 2]))     # {'__tag__': 'Many', 'items': [1, 2]}

from_dict(Result, {'__tag__': 'Ok', 'value': 5})   # Ok(5)
```

**Parameterized targets** reconstruct inner elements — bare `Many` leaves items as
raw data, so pass the element type when a collection holds structs or variants:

```python
from_dict(Many[User], to_dict(Many([User(id=1, name="A")])))  # Many([User(...)])
```

> **`Effect` is not serializable** — it wraps a deferred computation, so `to_dict`
> raises `TypeError`. Run the effect and serialize its result instead.

`@cases` variants serialize the same way: unit/value variants self-tag, while a
struct/builtin aliased as a variant is tagged only inside a field declared as the
union (the tag lives on the union, not the value). See **[Struct & Trait](struct.md)**
and **[Operands](operands.md)**.
