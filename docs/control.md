# Control

`stolas.control` provides **effectful flow combinators** — `bracket`, `retry`,
and `timeout` — that wrap [`Effect`](types.md#effectt) and
[`AsyncEffect`](types.md#asynceffectt) rather than retrofitting them. They keep
the framework's errors-as-values stance: the failure-capturing helpers catch
**`Exception` only**, so `KeyboardInterrupt`, `SystemExit`, and
`asyncio.CancelledError` always propagate.

### Import

```python
from stolas.control import (
    bracket, bracket_async,
    RetryPolicy, retry, retry_async,
    timeout,
)
```

---

## `bracket` — acquire / use / release

`bracket(acquire, use, release)` is the functional analogue of a `with`
statement: it calls `acquire()` to obtain a resource, runs `use(resource)`, and
**always** runs `release(resource)` afterwards — even if `use` raises. The result
of `use` is returned; an exception from `use` propagates *after* release.

```python
from stolas.control import bracket

events = []

bracket(
    acquire=lambda: events.append("open") or "conn",
    use=lambda r: events.append("query") or 42,
    release=lambda r: events.append("close"),
)
# returns 42
# events == ['open', 'query', 'close']
```

Release runs even when `use` fails — the exception surfaces only after cleanup:

```python
from stolas.control import bracket

events = []

def query(_resource):
    raise RuntimeError("query failed")

try:
    bracket(
        acquire=lambda: events.append("open") or "conn",
        use=query,
        release=lambda r: events.append("close"),
    )
except RuntimeError as exc:
    print(exc)          # query failed
    print(events)       # ['open', 'close']  (release still ran)
```

### `bracket_async`

`bracket_async` is the async analogue: `acquire`, `use`, and `release` are
**awaitable** (coroutine functions). `release(resource)` is awaited in a `finally`
block, so it runs even if `use` raises — including on cancellation.

```python
import asyncio
from stolas.control import bracket_async

events = []

async def acquire():
    events.append("open")
    return "conn"

async def use(resource):
    events.append("query")
    return 7 * 2

async def release(resource):
    events.append("close")

asyncio.run(bracket_async(acquire, use, release))
# returns 14
# events == ['open', 'query', 'close']
```

---

## `RetryPolicy` + `retry`

`retry(policy, effect)` returns a **new** `Effect` whose `.run()` re-runs the
underlying effect on failure, up to the configured number of attempts. The retry
behavior is configured by an immutable `RetryPolicy`.

### `RetryPolicy`

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `attempts` | `int` (>= 1) | — | Total number of tries (not *extra* retries) |
| `delay` | `float` | `0.0` | Seconds to pause before the next attempt |
| `backoff` | `float` | `1.0` | Multiplier applied to `delay` after each failed attempt |
| `retry_on_error` | `bool` | `False` | Also retry when the effect *returns* an `Error` value |

`RetryPolicy` is immutable (`__slots__`, blocked `__setattr__`/`__delattr__`,
value `__eq__`/`__hash__`) and validates its input — `attempts < 1` raises
`ValueError`:

```python
from stolas.control import RetryPolicy

RetryPolicy(attempts=3)
# RetryPolicy(attempts=3, delay=0.0, backoff=1.0, retry_on_error=False)

RetryPolicy(attempts=0)   # ValueError: attempts must be >= 1
```

### Retrying on a raised exception (the default)

By default a **failure is a raised `Exception`**. `retry` re-runs until the effect
succeeds or `attempts` is exhausted, in which case the last exception is
re-raised:

```python
from stolas.control import RetryPolicy, retry
from stolas.types import Effect

calls = {"n": 0}

def flaky():
    calls["n"] += 1
    if calls["n"] < 3:
        raise ValueError(f"transient failure {calls['n']}")
    return "ok"

retry(RetryPolicy(attempts=3), Effect(flaky)).run()   # 'ok'  (after 3 calls)
```

```python
from stolas.control import RetryPolicy, retry
from stolas.types import Effect

def always_fail():
    raise RuntimeError("persistent")

retry(RetryPolicy(attempts=2), Effect(always_fail)).run()
# RuntimeError: persistent  (re-raised after the last attempt)
```

`BaseException` is never caught, so `KeyboardInterrupt` interrupts a retry loop
immediately rather than being treated as a retryable failure.

### `retry_on_error` — error-as-value retries (default off)

`retry` distinguishes a *raised* exception from an effect that *returns* an
[`Error`](types.md#resultt-e) value. By default (`retry_on_error=False`) a
returned `Error` is a perfectly good result and is **not** retried:

```python
from stolas.control import RetryPolicy, retry
from stolas.types import Effect, Error

calls = {"n": 0}

def returns_error():
    calls["n"] += 1
    return Error("bad")

retry(RetryPolicy(attempts=3), Effect(returns_error)).run()
# Error('bad')   (calls['n'] == 1 — the Error value was accepted, not retried)
```

Set `retry_on_error=True` to opt into the error-as-value idiom: an `Error` value
then counts as a failure and triggers a retry, just like a raised exception:

```python
from stolas.control import RetryPolicy, retry
from stolas.types import Effect, Ok, Error

calls = {"n": 0}

def err_then_ok():
    calls["n"] += 1
    return Error("bad") if calls["n"] < 2 else Ok("good")

retry(RetryPolicy(attempts=3, retry_on_error=True), Effect(err_then_ok)).run()
# Ok('good')   (calls['n'] == 2)
```

### `delay` and `backoff`

`delay` pauses (via `time.sleep`) **between** attempts, and `backoff` multiplies
that delay after each failed attempt. With `delay=0.05, backoff=2.0` the pauses
are `0.05s` then `0.10s`; there is no pause after the final attempt.

```python
from stolas.control import RetryPolicy, retry
from stolas.types import Effect

policy = RetryPolicy(attempts=3, delay=0.05, backoff=2.0)
# attempt 1 -> sleep 0.05 -> attempt 2 -> sleep 0.10 -> attempt 3
```

### `retry_async`

`retry_async(policy, effect)` is the analogue for an `AsyncEffect`. It uses the
same `RetryPolicy`, but delays use `asyncio.sleep` (cooperative, non-blocking).
`asyncio.CancelledError` is a `BaseException` and is never caught, so cancelling
the task always wins over the retry loop:

```python
import asyncio
from stolas.control import RetryPolicy, retry_async
from stolas.types import AsyncEffect

calls = {"n": 0}

async def flaky():
    calls["n"] += 1
    if calls["n"] < 2:
        raise ValueError("transient")
    return "ok"

asyncio.run(retry_async(RetryPolicy(attempts=3), AsyncEffect(flaky)).run())
# 'ok'   (after 2 calls)
```

---

## `timeout` — async only

`timeout(seconds, ae)` wraps an `AsyncEffect` so its `.run()` raises
`TimeoutError` once `seconds` elapse. Cancellation of the inner awaitable is
driven by `asyncio.wait_for`.

`timeout` is **async-only by design** — there is deliberately no synchronous
variant. A wall-clock timeout on arbitrary blocking code cannot be enforced
cooperatively, so it lives only in the `async` world where cancellation is
well-defined.

```python
import asyncio
from stolas.control import timeout
from stolas.types import AsyncEffect

async def quick():
    await asyncio.sleep(0.01)
    return "done"

asyncio.run(timeout(1.0, AsyncEffect(quick)).run())   # 'done'
```

```python
import asyncio
from stolas.control import timeout
from stolas.types import AsyncEffect

async def slow():
    await asyncio.sleep(5)
    return "never"

async def main():
    try:
        await timeout(0.05, AsyncEffect(slow)).run()
    except TimeoutError:
        return "timed out"

asyncio.run(main())   # 'timed out'
```

Since `timeout` returns an `AsyncEffect`, it composes with the rest of the async
API — wrap it in `retry_async`, feed it through `map` / `bind` / `>>`, or run it
inside `bracket_async`.

---

See **[Monadic Types](types.md)** for the `Effect` / `AsyncEffect` API these
combinators build on, including `attempt` / `as_result` and the
sync↔async bridges (`to_async` / `from_effect` / `to_effect`).
