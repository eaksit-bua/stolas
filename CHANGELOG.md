# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Fixed
- `@struct` field validation no longer crashes on parameterized generic annotations (`list[int]`, `dict[str, int]`, `tuple[int, str]`). It now does a shallow container check and additionally supports union/optional and `@cases`-union field types.

### Changed
- `@cases` now records `_variant_names` / `_variant_kinds`, and a `__tag__` on unit/value variant wrappers, to support type-directed serialization.

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
