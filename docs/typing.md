# Typing Model

Stolas is a typed package (it ships a PEP 561 `py.typed` marker and hand-written
`.pyi` stubs). This document is an **honest map** of what the type-checker can and
cannot see: which surfaces are precisely typed, which are intentionally opaque, and
how the bundled mypy plugin fills the gaps that stubs alone cannot.

The guiding rule — the **north star** — is: *tighten types only where the runtime
is single-valued; leave dynamic / dual-mode surfaces opaque rather than
over-promising.* A type that lies is worse than a type that admits it does not know.

---

## Honest scope

The core library type-checks clean under `mypy --strict`:

```bash
mypy src/stolas --strict
# Success: no issues found in 30 source files
```

That run loads the bundled plugin (see [Enabling the plugin](#enabling-the-plugin-in-your-own-project)).
"Clean core" is precise, but two surfaces are **deliberately** left dynamic, and you
should expect them to type as `Any`:

- The **`_` placeholder** (`stolas.logic`) — a lambda-free expression builder.
- The **dual-mode `Many.__rshift__`** — the `>>` operator on the `Many` collection
  monad.

Everything else — the monads (`Result`, `Option`, `Validated`, `Effect`,
`AsyncEffect`), `@struct`, `@trait`, the `@cases` constructors, the `as_*`
combinators — is precisely typed via stubs and/or the plugin. The sections below
say exactly which is which.

---

## What is precisely typed

| Surface | Mechanism | Notes |
|---------|-----------|-------|
| `Result` / `Option` / `Validated` | `.pyi` stubs | `>>` is narrowed per-variant (e.g. `Error[E] >> f -> Error[E]`). |
| `Effect` / `AsyncEffect` | `.pyi` stubs | `eff >> f -> Effect[U]` / `AsyncEffect[U]`. |
| `@struct` class shape | `dataclass_transform` (stub) | Synthesized `__init__`, `__eq__`, fields, etc. (see below). |
| `@struct` `instance >> func` | **plugin** | Reveals `func`'s return type. |
| `@struct` `instance.replace(**changes)` | **plugin** | Returns the struct's own type (`Self`). |
| `@cases` variant constructors | **plugin** | Callable; result is `Any` (see below). |
| `@trait` dispatch | `.pyi` stubs | Trait function + `.impl` / `.require` / `.check` / `.types`. |
| `as_result` / `as_option` / `as_validated` / `as_many` / `as_effect` | `.pyi` stubs | Wrap a function so it returns the corresponding monad. |

---

## What is intentionally opaque

These surfaces are dynamic at runtime, so their static type is honestly `Any`.
They are **pinned** by typing fixtures (under `tests/typing/fixtures/`) so a future
change that accidentally over-types them is caught.

### The `_` placeholder

`stolas.logic._` builds expressions like `_.name` or `_ > 5` without writing a
`lambda`. Its operations return `PlaceholderExpression[Any, Any]` — the payload type
is **not** narrowed:

```python
from stolas.logic import _

reveal_type(_.name)   # Revealed type is "...PlaceholderExpression[Any, Any]"
```

Narrowing the placeholder would require knowing the element type it will later be
applied to, which is not available at the point `_.name` is written. Leaving it
opaque keeps the ergonomic API honest rather than fabricating a type it cannot
guarantee.

### Dual-mode `Many.__rshift__`

`Many.__rshift__` returns `Any` (see `src/stolas/types/many.pyi`). At runtime it is
**dual-mode**: depending on the right-hand operand it may map element-wise, flatten,
or apply a combinator, and it swallows `TypeError` / `AttributeError` to stay inside
the pipeline. Because the result type depends on runtime behavior the operator
cannot statically commit to, the stub returns `Any`. The other monads' `>>` *are*
narrowed, because each of those is single-valued; `Many`'s is the documented
exception.

### `@cases` constructor argument and result type

The plugin makes `@cases`-annotated attributes **callable** by retyping them to
`Any`, so `Format.Digital("dvd")` type-checks. The result is `Any`, and the
constructor's argument type is deliberately *not* tightened:

```python
from stolas.operand.cases import cases

@cases
class Format:
    Digital: str
    Print: int

reveal_type(Format.Digital("dvd"))   # Revealed type is "Any"
```

This is conservative on purpose. The runtime distinguishes three kinds of variant
from one annotation, and a blanket arg-type tightening would be dishonest for two of
them:

| Annotation | Kind | Runtime meaning |
|------------|------|-----------------|
| `Digital: str` | **alias** | `Format.Digital` *is* `str` — not a wrapper. |
| `Amount: Any` | **value** | A real value wrapper you call to construct. |
| `Empty: None` | **unit** | A non-callable singleton. |

Only the value kind is a genuine "call this with an argument" constructor.
Synthesizing per-variant callable signatures would mistype the alias and unit kinds,
so the plugin keeps the constructor `Any` rather than over-promising.

---

## The mypy plugin

Stolas bundles a mypy plugin at `src/stolas/mypy_plugin.py`. It exists because some
of the library's behavior is created **dynamically** — on user-defined classes — and
a stub for a `struct`/`cases` *function* cannot describe what happens to the *classes
those functions decorate*. The plugin does three things, all narrow and all proven by
fixtures.

### `@struct` — `instance >> func`

`@struct` is modelled statically via PEP 681 `dataclass_transform` (in
`struct.pyi`), which gives the synthesized class its `__init__`, `__eq__`, fields,
and so on — but a `dataclass_transform`-ed class has no place to declare the
runtime-only `>>` pipeline operator. The plugin injects it onto every
`@struct`-decorated class as:

```python
def __rshift__(self, func: Callable[[Self], R]) -> R: ...
```

so `instance >> f` type-checks as `f(instance)` and reveals `f`'s return type
(the runtime is exactly `f(self)`):

```python
@struct
class Point:
    x: int
    y: int

def to_str(p: Point) -> str:
    return f"{p.x},{p.y}"

point = Point(x=1, y=2)
reveal_type(point >> to_str)   # Revealed type is "builtins.str"
```

Piping into a function that cannot accept the struct is correctly rejected with an
`[operator]` error.

### `@struct` — typed `.replace()`

`replace()` returns a re-validated copy of the struct with selected fields
overridden (see **[Struct & Trait](struct.md)**). The plugin injects the method form
onto every `@struct` class as:

```python
def replace(self, **changes: Any) -> Self: ...
```

so it returns the struct's own type:

```python
reveal_type(point.replace(x=5))   # Revealed type is "...Point"
```

Assigning the result to an incompatible type errors. This is done in the plugin
rather than in `struct.pyi` precisely because `.replace()` applies to the
dynamically `dataclass_transform`-ed **user** class — a stub for the `struct`
function has no class to attach it to. (The free function `replace(instance,
**changes)` is also typed independently; the `.replace()` method is the convenience
form.)

### `@cases` — callable variant constructors

The plugin retypes `@cases`-annotated attributes to `Any` so they may be *called*
(`Format.Digital("dvd")`). The result and argument types are left opaque on purpose
— see [`@cases` constructor argument and result type](#cases-constructor-argument-and-result-type)
above.

### Why a plugin, and the `dataclass_transform` interaction

There is a subtle but important interaction. mypy only falls back to its built-in
`dataclass_transform` handling when **no** class-decorator hook is registered for a
decorator. Registering the plugin's hook for `@struct` would therefore *suppress*
mypy's synthesized `__init__` — breaking `Point(x=1, y=2)` with an "Unexpected
keyword argument" error.

The plugin compensates by forwarding to mypy's own dataclasses plugin
(`dataclass_tag_callback` in the main pass and `dataclass_class_maker_callback` in
the later pass) **before** injecting the extra `>>` and `.replace()` methods. The
net effect: you keep the full synthesized dataclass shape *and* the two extra
methods.

The plugin adds **no** strictness-loosening behavior — it never ignores errors or
disables error codes. The gate stays `mypy src/stolas --strict`.

---

## Enabling the plugin in your own project

The plugin lives at `src/stolas/mypy_plugin.py` in this repo. To get the
`@struct` `>>` / `.replace()` and callable `@cases` constructors in **your** project,
register it in your mypy config.

For most consumers, stolas is installed as a normal package, so reference the plugin
by its **module path**:

```ini
# mypy.ini  (or the [mypy] section of setup.cfg)
[mypy]
plugins = stolas.mypy_plugin
```

```toml
# pyproject.toml
[tool.mypy]
plugins = ["stolas.mypy_plugin"]
```

Nothing else is required — no extra dependency (mypy resolves the plugin via your
installed `stolas`), and no strictness option needs changing. You can keep running
mypy under `--strict`.

> [!NOTE]
> **This repo's own config uses the file-path form**, because stolas is *not*
> installed into this repo's virtualenv (the tests inject `src/` onto `sys.path`).
> mypy imports a plugin via the runtime Python path, so the module form
> `plugins = ["stolas.mypy_plugin"]` fails here with *"No module named 'stolas'"*.
> This repo therefore uses:
>
> ```toml
> [tool.mypy]
> mypy_path = ["src"]
> plugins = ["src/stolas/mypy_plugin.py"]
> ```
>
> The file path is resolved relative to the config file's directory, and
> `mypy_path = ["src"]` lets `import stolas...` resolve for the type-check itself.
> In a project where stolas is pip-installed you do **not** need either of these —
> the module form above is enough.

---

## The `>>` typing matrix

`>>` means different things on different types. It is narrowed only where the runtime
is single-valued:

| Left-hand type | `lhs >> f` static type | Narrowed? |
|----------------|------------------------|-----------|
| `Ok[T]` / `Error[E]` | `Ok[Any] \| Error[Any]` / `Error[E]` | ✅ stub |
| `Some[T]` / `Nothing` | `Some[Any] \| _Nothing` / `_Nothing` | ✅ stub |
| `Valid[T]` / `Invalid[E]` | `Valid[Any] \| Invalid[Any]` / `Invalid[E]` | ✅ stub |
| `Effect[T]` / `AsyncEffect[T]` | `Effect[U]` / `AsyncEffect[U]` | ✅ stub |
| `@struct` instance | return type of `f` | ✅ plugin |
| `Many[T]` | `Any` | ❌ opaque (dual-mode) |
| `_` placeholder expression | `PlaceholderExpression[Any, Any]` | ❌ opaque |

See **[Monadic Types](types.md)** for the per-monad `>>` semantics and **[Logic
Reference](logic.md)** for the placeholder.

---

## Verifying the model

The claims above are not aspirational — they are pinned by a mypy fixture harness
under `tests/typing/`. It runs mypy as a subprocess (with the project config, so the
plugin is active) against small fixture files and asserts on the `reveal_type` notes
and expected error codes. Notable fixtures:

- `struct_pipe_replace.py` — `point >> to_str` reveals `str`; `point.replace(x=5)`
  reveals `Point`.
- `cases_constructor.py` — `Format.Digital("dvd")` reveals `Any`.
- `placeholder_opaque.py` — `_.name` reveals `PlaceholderExpression[Any, Any]`
  (pins that the placeholder was *not* over-typed).
- `plugin_active_proof.py` — type-checks clean only when the plugin is active; with
  the plugin off, the three plugin-only surfaces emit `[operator]` / `[attr-defined]`
  errors. This is the registration proof.
