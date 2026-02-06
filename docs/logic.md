# Logic Combinators

Functional utilities for data access, transformation, filtering, and flow control.

---

## The Placeholder (`_`)

The placeholder builds **lambda-free expressions**. Instead of writing `lambda x: x.foo`, write `_.foo`.

### Import

```python
from stolas.logic import _
```

### Supported Operations

| Expression | Equivalent Lambda |
|------------|-------------------|
| `_ + 1` | `lambda x: x + 1` |
| `_ * 2` | `lambda x: x * 2` |
| `_ - 5` | `lambda x: x - 5` |
| `_ / other` | `lambda x: x / other` |
| `_ // other` | `lambda x: x // other` |
| `_ % 2` | `lambda x: x % 2` |
| `_ ** 2` | `lambda x: x ** 2` |
| `_ > 5` | `lambda x: x > 5` |
| `_ < 5` | `lambda x: x < 5` |
| `_ >= 5` | `lambda x: x >= 5` |
| `_ <= 5` | `lambda x: x <= 5` |
| `_ == val` | `lambda x: x == val` |
| `_ != val` | `lambda x: x != val` |
| `-_` | `lambda x: -x` |
| `abs(_)` | `lambda x: abs(x)` |

### Attribute Access

```python
_.name           # lambda x: x.name
_.user.email     # lambda x: x.user.email
```

### Item Access

```python
_["key"]         # lambda x: x["key"]
_[0]             # lambda x: x[0]
```

### Method Calls

```python
_.lower()                # lambda x: x.lower()
_.split(",")             # lambda x: x.split(",")
_.replace("a", "b")      # lambda x: x.replace("a", "b")
```

### Chaining

```python
_.name.upper()           # lambda x: x.name.upper()
(_["price"] * 1.1)       # lambda x: x["price"] * 1.1
```

### Reflected Operators

For `other op _`:

```python
5 + _    # lambda x: 5 + x
10 - _   # lambda x: 10 - x
2 * _    # lambda x: 2 * x
```

---

## Access Combinators

### `get(attr)`

Get attribute from object.

```python
from stolas.logic import get

class User:
    name = "Alice"

get("name")(User())  # "Alice"
```

### `at(index)`

Safe sequence access by index.

```python
from stolas.logic import at

items = [10, 20, 30]
at(0)(items)   # 10
at(-1)(items)  # 30
at(10)(items)  # IndexError
```

### `call(method, *args, **kwargs)`

Call a method on an object.

```python
from stolas.logic import call

call("upper")("hello")           # "HELLO"
call("replace", "a", "b")("aaa")  # "bbb"
```

---

## Collection Combinators

These work with `Many` via the pipeline operator.

### `where(predicate)`

Filter elements matching predicate.

```python
from stolas.logic import where, _
from stolas.types import Many

Many([1, 2, 3, 4, 5]) >> where(_ > 2)
# Many([3, 4, 5])
```

### `apply(func)`

Transform each element.

```python
from stolas.logic import apply, _

Many([1, 2, 3]) >> apply(_ * 10)
# Many([10, 20, 30])
```

### `chain(func)`

FlatMap: transform to Many and flatten.

```python
from stolas.logic import chain

Many([[1, 2], [3, 4]]) >> chain(Many)
# Many([1, 2, 3, 4])
```

### `first()`

Get first element as `Option`.

```python
from stolas.logic import first

Many([1, 2, 3]) >> first()
# Some(1)

Many([]) >> first()
# Nothing
```

### `last()`

Get last element as `Option`.

```python
from stolas.logic import last

Many([1, 2, 3]) >> last()
# Some(3)

Many([]) >> last()
# Nothing
```

### `count()`

Count elements, returns `Some[int]`.

```python
from stolas.logic import count

Many([1, 2, 3]) >> count()
# Some(3)
```

### `find(predicate)`

Find first matching element.

```python
from stolas.logic import find, _

Many([1, 2, 3, 4]) >> find(_ > 2)
# Some(3)
```

### `sort(key=None, reverse=False)`

Sort elements.

```python
from stolas.logic import sort

Many([3, 1, 2]) >> sort()
# Many([1, 2, 3])
```

### `pair(other)`

Zip with another Many collection.

```python
from stolas.logic import pair

Many([1, 2, 3]) >> pair(Many(['a', 'b', 'c']))
# Many([(1, 'a'), (2, 'b'), (3, 'c')])
```

---

## Flow Combinators

### `check(predicate, error_msg)`

Assert a condition in a pipeline. Returns `Error(error_msg)` if predicate fails.

```python
from stolas.logic import check, _
from stolas.types import Ok

Ok(10) >> check(_ > 5, "Too small")  # Ok(10)
Ok(1)  >> check(_ > 5, "Too small")  # Error("Too small")
```

### `strict(type_)`

Type validation. Returns `Ok` if type matches, `Error(TypeError)` otherwise.

```python
from stolas.logic import strict
from stolas.types import Ok

Ok(42) >> strict(int)       # Ok(42)
Ok("hi") >> strict(int)     # Error(TypeError(...))
```

---

## Utility Combinators

### `identity`

Returns input unchanged.

```python
from stolas.logic import identity

identity(42)  # 42
```

### `const(value)`

Returns a function that always returns `value`.

```python
from stolas.logic import const

always_five = const(5)
always_five("ignored")  # 5
always_five(None)       # 5
```

### `tap(func)`

Execute side effect, return original value.

```python
from stolas.logic import tap

Ok(10) >> tap(print) >> (lambda x: x * 2)
# Prints: 10
# Returns: Ok(20)
```

### `tee(func)`

Alias for `tap`. Execute side effect, return original value.

```python
from stolas.logic import tee

Ok(10) >> tee(print)
# Prints: 10
# Returns: Ok(10)
```

### `fmt(template)`

Format string with value.

```python
from stolas.logic import fmt

Ok("Alice") >> fmt("Hello, {}!")
# Ok("Hello, Alice!")
```

### `wrap(wrapper_func)`

Wrap value in container.

```python
from stolas.logic import wrap
from stolas.types import Some

42 >> wrap(Some)  # Some(42)
```

### `when(predicate, then_fn, else_fn)`

Conditional execution.

```python
from stolas.logic import when, const, _

action = when(_ > 18, const("Adult"), const("Minor"))
action(20)  # "Adult"
action(10)  # "Minor"
```

### `compose(*funcs)`

Compose functions left-to-right (pipe style).

```python
from stolas.logic import compose

f = compose(str.strip, str.upper)
f("  hello  ")  # "HELLO"
# Executes: str.upper(str.strip("  hello  "))
```

### `alt(default)`

Unwrap `Option` or return default.

```python
from stolas.logic import alt
from stolas.types import Some, Nothing

Some(42) >> alt(0)  # 42
Nothing >> alt(0)   # 0
```

---

## Predicate Combinators

### `contains(item)`

Check if collection contains item.

```python
from stolas.logic import contains

has_3 = contains(3)
has_3([1, 2, 3])  # True
has_3([1, 2])     # False
```

### `negate(predicate)`

Invert a predicate.

```python
from stolas.logic import negate, _

is_even = _ % 2 == 0
is_odd = negate(is_even)

is_odd(3)  # True
is_odd(4)  # False
```

### `both(pred1, pred2)`

Combine predicates with AND.

```python
from stolas.logic import both, _

is_positive_even = both(_ > 0, _ % 2 == 0)
is_positive_even(4)   # True
is_positive_even(-2)  # False
```

### `either(pred1, pred2)`

Combine predicates with OR.

```python
from stolas.logic import either, _

is_zero_or_ten = either(_ == 0, _ == 10)
is_zero_or_ten(0)   # True
is_zero_or_ten(5)   # False
```

---

## Quick Reference

| Category | Functions |
|----------|-----------|
| **Access** | `get`, `at`, `call` |
| **Collection** | `where`, `apply`, `chain`, `first`, `last`, `count`, `find`, `sort`, `pair` |
| **Flow** | `check`, `strict` |
| **Utilities** | `identity`, `const`, `tap`, `tee`, `fmt`, `wrap`, `when`, `compose`, `alt` |
| **Predicates** | `contains`, `negate`, `both`, `either` |
| **Placeholder** | `_` |

---

## Python vs Stolas

| Python | Stolas | Category |
|--------|--------|----------|
| `lambda x: x.name` | `_.name` | Placeholder |
| `lambda x: x["key"]` | `_["key"]` | Placeholder |
| `lambda x: x > 5` | `_ > 5` | Placeholder |
| `lambda x: x.upper()` | `_.upper()` | Placeholder |
| `lambda x: getattr(x, "name")` | `get("name")` | Access |
| `lambda x: x["id"]` | `at("id")` | Access |
| `lambda x: x[0]` | `at(0)` | Access |
| `lambda x: x.method()` | `call("method")` | Access |
| `lambda x: pred(x)` (filter) | `where(pred)` | Collection |
| `lambda x: f(x)` (map) | `apply(f)` | Collection |
| `lambda xs: xs[0] if xs else None` | `first()` | Collection |
| `lambda xs: xs[-1] if xs else None` | `last()` | Collection |
| `lambda xs: len(xs)` | `count()` | Collection |
| `lambda xs: next((x for x in xs if p(x)), None)` | `find(p)` | Collection |
| `lambda xs: sorted(xs)` | `sort()` | Collection |
| `lambda xs, ys: zip(xs, ys)` | `pair(other)` | Collection |
| `lambda x: item in x` | `contains(item)` | Predicate |
| `lambda x: not pred(x)` | `negate(pred)` | Predicate |
| `lambda x: p1(x) and p2(x)` | `both(p1, p2)` | Predicate |
| `lambda x: p1(x) or p2(x)` | `either(p1, p2)` | Predicate |
| `lambda x: x` | `identity` | Utility |
| `lambda _: value` | `const(value)` | Utility |
| `lambda x: template.format(x)` | `fmt(template)` | Utility |
| `lambda x: cls(x)` | `wrap(cls)` | Utility |
| `lambda opt: opt.unwrap_or(default)` | `alt(default)` | Utility |

