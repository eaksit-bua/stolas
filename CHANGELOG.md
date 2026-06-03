# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-03

### Added
- **`@struct(open=True)`** (`stolas.struct`): `@struct` is now a **dual-form** decorator — usable bare as `@struct` (the default, `open=False`) or called as `@struct(open=True)`. The call form relaxes **only** the inheritance guard, so subclasses are permitted; the base struct stays frozen, `__slots__`-only, runtime-type-checked, and keeps `>>` / `.replace()`. `open=False` is byte-identical to the historical behavior (same generated namespace, repr/eq/hash/slots, and `__init_subclass__` block). The bundled mypy plugin still fires for the call form, so `>>` and `.replace()` stay typed on open structs. Documented soundness caveat: a subclass can reintroduce mutability while the frozen stub still types it as immutable (the gap is documented, not solved). See **[Struct & Trait](docs/struct.md)** and **[Interop](docs/interop.md)**.
- **`variant_from_dict(cls, data)`** (`stolas.serde`): reconstruct a **single** `@cases` variant instance from a dict, complementing `from_dict` (which takes the union) for when you already hold the concrete variant class. Accepts a value-variant class, a unit variant (class or singleton), or an existing-class variant (a `@struct`/builtin aliased as a variant); a `__tag__` that names a different variant raises `ValueError`. Exported from `stolas.serde`. Zero runtime dependencies.
- **Zero-dependency interop docs** (`docs/interop.md`): `stolas.serde`'s free functions (`to_dict`/`from_dict`/`to_json`/`from_json`) are the documented interop path to pydantic / SQLAlchemy / msgspec — recipe-level adapters, a few lines each, no heavy adapter code. Deliberately **no `stolas[pydantic]` extra** ships (decision D11). Cross-linked from the README docs list.
- **Async effects & control flow** (`AsyncEffect` + `stolas.control`): a native `async`/`await` effect type and effectful flow combinators, with zero runtime dependencies.
  - `Effect.attempt(thunk)` / `Effect.as_result()` capture a raised `Exception` as an `Error` value (errors-as-values); `BaseException` (e.g. `KeyboardInterrupt`) propagates.
  - **`AsyncEffect[T]`** (`stolas.types`): an immutable async *sibling* of `Effect` — no free-monad interpreter, just `await`. Wraps a factory yielding a **fresh awaitable per run**, with `map` / `bind` / `>>` / async `run` / `pure` / `defer` / `attempt` / `as_result`. `attempt`/`as_result` catch `Exception` only, so `asyncio.CancelledError` always propagates.
  - **Bridges**: `Effect.to_async()` and module-level `from_effect()` lift a sync effect to async; `to_effect()` runs an `AsyncEffect` to completion via `asyncio.run` (and raises a clear `RuntimeError` if invoked inside an already-running event loop).
  - **`stolas.control`**: `bracket` / `bracket_async` (acquire/use/release with release-always-runs semantics); `RetryPolicy(attempts, delay=0.0, backoff=1.0, retry_on_error=False)` plus `retry` / `retry_async` (retry on raised exception by default; opt into error-as-value retries via `retry_on_error`; `delay`/`backoff` between attempts); and `timeout(seconds, ae)` (async-only, raises `TimeoutError`).
- **Validation** (`stolas.validation`): generic, composable field validators that return `Validated` (errors-as-values) and never raise. Primitives: `rule` (base hook), `matches` (regex), `length`, `between`, `min_val`, `max_val`, `non_empty`, `one_of`, plus `all_of` (accumulates all failures) and `any_of` (succeeds if any passes). Deliberately domain-agnostic — no `email`/`url`/`phone` built-ins; `rule`/`matches` are the documented hooks for such recipes.
  - **`@struct` field validators**: opt-in `__validators__: dict[str, Validator]` runs after type checks during `__init__`, aggregating every value failure into a single `ValueError` (type errors still raise `TypeError` first). A struct without `__validators__` is byte-identical to before (zero overhead). `replace()` / `.replace()` / `from_dict()` re-run the validators.
- **Monadic collection combinators** (`stolas.logic`): `sequence`, `traverse`, `partition`, and `combine_all` for working with collections of monads.
  - `sequence` / `traverse` dispatch on the element monad: fail-fast for `Result`/`Option`, error-accumulating (flat) for `Validated`, and lazy (a single `Effect`) for `Effect`. Empty collections require a `kind` string (`"result"`/`"option"`/`"validated"`/`"effect"`).
  - `partition` splits a `Many[Result]` into an order-preserving `(Many[oks], Many[errors])` tuple.
  - `combine_all` combines `Validated` values into a flat `Valid(tuple(...))`, or an `Invalid` with all errors concatenated flat.
- **Immutable update**: `replace(struct, **changes)` free function and a `.replace()` method on every `@struct`, returning a re-validated copy with selected fields overridden (the original is never mutated). Exported from `stolas.struct`.
- **Serialization** (`stolas.serde`): `to_dict` / `from_dict`, plus stdlib-JSON `to_json` / `from_json`, for `@struct`, the monads (`Result`/`Option`/`Validated`/`Many`), `@cases` variants, and nested containers. Zero runtime dependencies.
  - `@cases` serialization is **type-directed**: a `__tag__` discriminator is emitted on union-typed positions (the union owns the tag, Rust-`serde` style), while unit/value variant wrappers self-tag.
  - `from_dict` honours parameterized targets, e.g. `from_dict(Many[User], data)` reconstructs each element.
  - `Effect` is intentionally not serializable (`to_dict` raises `TypeError`).
- **Registered the bundled mypy plugin** (`stolas.mypy_plugin`) via a `[tool.mypy]` section in `pyproject.toml`, so type-checking now sees `@struct` and `@cases` correctly. The plugin injects, onto every `@struct`-decorated class, a precise `instance >> func` operator (typed as the return of `func`) and a `.replace(**changes) -> Self` method, and makes `@cases` variant constructors callable. It adds no strictness-loosening options — `mypy src/stolas --strict` stays clean with the plugin active. Consumers enable it with `plugins = ["stolas.mypy_plugin"]` in their own mypy config (see the new typing docs).
- **Typing documentation** (`docs/typing.md`): an honest map of what is precisely typed, what is intentionally opaque (the `_` placeholder and the dual-mode `Many.__rshift__`), what the mypy plugin does for `@struct`/`@cases`, how a consumer enables the plugin, the `dataclass_transform` story for `@struct`, the typed `.replace()`, and the full `>>` typing matrix. Cross-linked from the README docs list.

### Fixed
- `@struct` field validation no longer crashes on parameterized generic annotations (`list[int]`, `dict[str, int]`, `tuple[int, str]`). It now does a shallow container check and additionally supports union/optional and `@cases`-union field types.

### Changed
- **`@struct` is now dual-form** — `struct(cls=None, *, open=False)` — so it works both bare (`@struct`) and called (`@struct(open=True)`). The default (`open=False`) is byte-identical to before; only the call form with `open=True` changes behavior (subclassing permitted). The `struct.pyi` stub now uses two `@overload` forms, each carrying the full `@dataclass_transform(frozen_default=True, kw_only_default=True, ...)` so kw-only/frozen modelling holds for both the bare-class form and the `(*, open: bool = ...) -> Callable[...]` call form.
- `@cases` now records `_variant_names` / `_variant_kinds`, and a `__tag__` on unit/value variant wrappers, to support type-directed serialization.
- **Re-scoped the strictness claim** in the README from "100% mypy strict compliance" to "`mypy --strict`-clean core + bundled plugin", with the `_` placeholder and dual-mode `>>` called out as intentionally opaque. The wording now matches how the library actually types itself rather than over-promising.

---

## [0.1.2] - 2026-02-06

### Added
- **ADT Trait Dispatch**: `@trait` now automatically unwraps `@cases` classes (ADTs) into their constituent variants during registration. This allows `impl(Animal)` to correctly register implementations for `Dog` and `Cat` when `Animal` is a sum type.

### Fixed
- Resolved `NotImplementedError` when dispatching trait methods on instances (like `Dog`) that rely on a parent ADT wrapper (like `Animal`) for registration.

---

## [0.1.1] - 2026-02-06

### Fixed
- **Arity Decorator Compatibility**: `@unary`/`@binary` now work correctly when stacked above `@as_result`. Previously, arity validation failed on wrapped functions because it checked `__code__.co_argcount` directly. Now uses `inspect.signature` to correctly resolve signatures through `functools.wraps` chains.

### Changed
- `Many.first()`, `Many.last()` now return `Option[T]` instead of `T | None` for consistency with monadic patterns.
- `Many.count()` now returns `Some[int]` instead of `int`.

---

## [0.1.0] - 2026-02-05

### Added
- **Struct System**: `@struct` decorator for immutable data classes, `@trait` for polymorphic dispatch.
- **Monadic Types**: `Result`, `Option`, `Validated`, `Many`, `Effect`.
- **Logic Combinators**: Rich functional utilities (`compose`, `check`, `when`, `where`) and placeholder expression syntax (`_`).
- **Operand Decorators**: `@cases` for sum types, `@safe` (as_result, as_option) for error handling integration.
- **Integration**: Pipeline operator support (`>>`) across all major types.
- **Testing**: Complete test suite with 100% coverage (730 passing tests).
- **Concurrency**: `concurrent` module for parallel execution.

### Changed
- Refactored core modules to ensure `mypy --strict` compliance.
- Consolidated error handling patterns around `Result` monad.

### Security
- Initial release with scoped strictness; no known vulnerabilities.
