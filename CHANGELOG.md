# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
