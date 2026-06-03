# Validation

Stolas ships a small library of **generic, composable field validators** and an
opt-in hook for validating `@struct` fields at construction time. Validators are
errors-as-values: they return a `Validated` and **never raise**.

---

## The Validator Contract

```python
from stolas.validation import Validator
```

A *validator* is the type alias:

```python
Validator = Callable[[T], Validated[T, str]]
```

Given a value, a validator returns:

- `Valid(value)` on success, or
- `Invalid([message])` on failure.

The contract has one ironclad rule: **a validator never raises**. Inapplicable
input — `length()` on a value with no `len`, `between()` on something that can't
be compared — yields `Invalid([message])` rather than letting an exception
escape. This keeps validation total: every value maps to a `Valid` or an
`Invalid`, never a traceback.

See **[Monadic Types](types.md)** for the full `Validated` / `Valid` / `Invalid`
API (including error accumulation via `combine`).

---

## Primitives

Every primitive is a **factory**: you call it to configure a validator, then call
the returned validator on a value.

### `rule(predicate, message)`

The base hook every other primitive is built on. Returns `Valid(value)` if
`predicate(value)` is truthy, otherwise `Invalid([message])`. The predicate runs
inside a guard, so a predicate that itself raises still yields
`Invalid([message])` — never an exception.

```python
from stolas.validation import rule

positive = rule(lambda v: v > 0, "must be positive")

positive(5)    # Valid(5)
positive(-1)   # Invalid(['must be positive'])

# A predicate that raises is caught -> Invalid, not a traceback:
rule(lambda v: v.nope(), "boom")(5)   # Invalid(['boom'])
```

### `matches(pattern, message=None)`

Validate that a **`str`** value matches `pattern` via `re.search`. Non-`str`
values are `Invalid`. When `message` is omitted, a default mentioning the pattern
is used. This is the documented hook for domain recipes such as
email/url/phone (see **[The "email" recipe](#recipe-email-via-matches)** below).

```python
from stolas.validation import matches

lower = matches(r"^[a-z]+$", "lowercase only")

lower("abc")   # Valid('abc')
lower("ABC")   # Invalid(['lowercase only'])
lower(123)     # Invalid(['lowercase only'])  (non-str)

# Default message mentions the pattern (built with repr(pattern)):
matches(r"\d+")("abc")   # Invalid(["must match pattern '\\\\d+'"])
```

### `length(min=None, max=None)`

`len()`-based validation with **inclusive** bounds; either bound may be omitted.
A value with no `len` is `Invalid`.

```python
from stolas.validation import length

length(min=1, max=5)("abc")   # Valid('abc')
length(min=2)("a")            # Invalid(['length must be at least 2, got 1'])
length(max=2)("abcd")         # Invalid(['length must be at most 2, got 4'])
length(min=1)(42)             # Invalid(['must have a length, got int'])
```

### `between(lo, hi)`

`lo <= value <= hi`, inclusive. Values that cannot be compared are `Invalid`.

```python
from stolas.validation import between

between(0, 100)(50)    # Valid(50)
between(0, 100)(150)   # Invalid(['must be between 0 and 100'])
between(0, 100)("x")   # Invalid(['must be between 0 and 100'])  (incomparable)
```

### `min_val(n)` / `max_val(n)`

Lower / upper inclusive bounds: `value >= n` and `value <= n`.

```python
from stolas.validation import min_val, max_val

min_val(0)(5)      # Valid(5)
min_val(0)(-1)     # Invalid(['must be at least 0'])
max_val(100)(50)   # Valid(50)
max_val(100)(150)  # Invalid(['must be at most 100'])
```

### `non_empty()`

Zero-argument factory: `len(value) > 0`. A value with no `len` is `Invalid`.

```python
from stolas.validation import non_empty

non_empty()("hi")   # Valid('hi')
non_empty()("")     # Invalid(['must not be empty'])
non_empty()(5)      # Invalid(['must have a length, got int'])
```

### `one_of(*choices)`

Membership check: `value in choices`.

```python
from stolas.validation import one_of

colour = one_of("red", "green", "blue")

colour("green")    # Valid('green')
colour("purple")   # Invalid(["must be one of ['red', 'green', 'blue']"])
```

---

## Combining Validators

### `all_of(*validators)`

All must pass. `all_of` runs **every** validator and **aggregates every failure
message** (it reuses `combine_all` from `stolas.logic`, so the flat-error
behavior matches the rest of the framework). On success it returns
`Valid(value)` — the **original value**, not the throwaway tuple `combine_all`
builds internally.

```python
from stolas.validation import all_of, non_empty, length, matches

# All pass -> Valid carrying the original value:
all_of(non_empty(), length(max=10))("hi")        # Valid('hi')

# Every failure is collected, not just the first:
all_of(length(min=5), matches(r"^[a-z]+$", "lowercase"))("AB")
# Invalid(['length must be at least 5, got 2', 'lowercase'])
```

### `any_of(*validators)`

At least one must pass. Returns `Valid(value)` as soon as a validator succeeds;
if none do, returns `Invalid` with **every** message concatenated flat.

```python
from stolas.validation import any_of, one_of, matches

flag = any_of(one_of("y", "n"), matches(r"^\d+$", "digits"))

flag("42")      # Valid('42')
flag("maybe")   # Invalid(["must be one of ['y', 'n']", 'digits'])
```

---

## `@struct` Field Validators

Validation integrates with `@struct` through an **opt-in** class attribute. Declare
`__validators__`, a `dict[str, Validator]` mapping field names to validators
(compose several per field with `all_of`):

```python
from stolas.struct import struct
from stolas.validation import all_of, non_empty, length, between

@struct
class User:
    name: str
    age: int
    __validators__ = {
        "name": all_of(non_empty(), length(max=20)),
        "age": between(0, 150),
    }

User(name="Alice", age=30)   # User(name='Alice', age=30)
```

### Order of checks: TypeError first, then one aggregated ValueError

`__init__` runs its checks in a fixed order, and the **kind of error tells you
which stage failed**:

1. **Unknown or missing fields** raise `TypeError` — before any value is stored.
2. **Wrong field type** raises `TypeError` — value validators never see
   ill-typed input.
3. Only then does **value validation** run. Every failing field contributes its
   message(s), and they are aggregated into a **single `ValueError`** of the form
   `field: message`, joined with `; ` in field-declaration order.

```python
# 1. Unknown / missing -> TypeError
User(name="Alice", age=30, extra=1)   # TypeError: Unknown fields: {'extra'}
User(name="Alice")                    # TypeError: Missing required fields: {'age'}

# 2. Wrong type -> TypeError (before value validation)
User(name=123, age=30)                # TypeError: Field 'name' expects str, got int

# 3. Wrong value -> one aggregated ValueError listing every failed field
User(name="", age=200)
# ValueError: name: must not be empty; age: must be between 0 and 150
```

A single field whose validator emits multiple messages contributes all of them,
each under that field's prefix:

```python
@struct
class Form:
    code: str
    __validators__ = {"code": all_of(non_empty(), length(min=3))}

Form(code="")
# ValueError: code: must not be empty; code: length must be at least 3, got 0
```

> [!NOTE]
> The split is deliberate: a `TypeError` means the *shape* of the data is wrong
> (decision D6), while a `ValueError` means the data is well-typed but
> semantically invalid. Catch them separately when that distinction matters.

### No `__validators__` is byte-identical to before

A `@struct` that does not declare `__validators__` is **exactly** the struct you
had before this feature existed — zero overhead. The generated class doesn't even
carry the attribute, and the value-validation step is skipped entirely:

```python
@struct
class Plain:
    x: int
    y: str

hasattr(Plain, "__validators__")   # False
Plain(x=1, y="a")                  # Plain(x=1, y='a')
```

An **empty** `__validators__ = {}` is falsy and behaves identically — nothing is
installed:

```python
@struct
class Guarded:
    x: int
    __validators__ = {}

hasattr(Guarded, "__validators__")   # False
```

### `replace()`, `.replace()` and `from_dict()` re-validate

Because every path that builds a struct goes through `__init__`, validation runs
on **every** construction — including the immutable-update and deserialization
paths. Invalid changes raise `ValueError`; valid ones succeed.

```python
from stolas.struct import struct, replace
from stolas.serde import from_dict
from stolas.validation import all_of, non_empty, length, between

@struct
class User:
    name: str
    age: int
    __validators__ = {
        "name": all_of(non_empty(), length(max=20)),
        "age": between(0, 150),
    }

u = User(name="Alice", age=30)

replace(u, age=999)        # ValueError: age: must be between 0 and 150
u.replace(name="")         # ValueError: name: must not be empty
replace(u, name="Bob")     # User(name='Bob', age=30)  (valid)

from_dict(User, {"name": "", "age": 30})
# ValueError: name: must not be empty
from_dict(User, {"name": "Bob", "age": 40})   # User(name='Bob', age=40)  (valid)
```

See **[Struct & Trait](struct.md)** for `replace()` / `.replace()` and
**[Monadic Types](types.md)** for `from_dict()`.

---

## Policy: no domain validators

Stolas ships **only generic primitives**. There are deliberately **no**
`email`, `url`, or `phone` built-ins — those are domain conventions that drift,
disagree across standards, and don't belong in a framework core.

`rule()` and `matches()` are the extension hooks. Build the domain validator your
application actually needs, name it, and reuse it. This keeps the library small
and your validation rules explicit and version-controlled in *your* codebase.

---

<a id="recipe-email-via-matches"></a>

## Recipe: email via `matches()`

An email check is a **user recipe**, not a built-in — a regular validator you
assemble from `matches()`:

```python
from stolas.validation import matches
from stolas.struct import struct

# A pragmatic "looks like an email" check. Tune the pattern to your needs.
email = matches(r"[^@\s]+@[^@\s]+\.[^@\s]+", "must be a valid email")

email("alice@example.com")   # Valid('alice@example.com')
email("not-an-email")        # Invalid(['must be a valid email'])
email(123)                   # Invalid(['must be a valid email'])  (non-str)

@struct
class Account:
    email: str
    __validators__ = {"email": email}

Account(email="bob@example.com")   # Account(email='bob@example.com')
Account(email="nope")              # ValueError: email: must be a valid email
```

The same shape gives you URL, phone, slug, or any other domain rule: pick a
pattern, give it a message, and (optionally) compose it with the generic
primitives via `all_of` / `any_of`.
