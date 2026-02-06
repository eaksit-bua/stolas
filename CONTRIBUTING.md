# Contributing to Stolas

We welcome contributions! Stolas is a strict library, so we ask that you follow these guidelines.

## Development Setup

1.  **Clone the repository**
2.  **Install dependencies** with `pip` (or `uv`):
    ```bash
    pip install ".[dev]"
    ```
3.  **Install pre-commit hooks** (optional but recommended):
    ```bash
    pre-commit install
    ```

## Quality Standards

We enforce strict quality control. Before submitting a PR, ensure:

1.  **Tests Pass**: All tests must pass.
    ```bash
    pytest tests/
    ```
2.  **Linting**: Code must be formatted and linted with Ruff.
    ```bash
    ruff check .
    ruff format .
    ```
3.  **Security**: No security issues found by Bandit.
    ```bash
    bandit -r src
    ```
4.  **Type Safety**: 100% strict typing is required.
    ```bash
    mypy src/stolas --strict
    ```

## Coding Style

*   **Immutable by Default**: Use `@struct` and `@cases`.
*   **No Exceptions**: Return `Result[T, E]` instead of raising exceptions for expected failures.
*   **Type Hints**: Everything must be typed. Use `.pyi` stubs if necessary.

## Pull Requests

1.  Open an issue to discuss major changes first.
2.  Create a feature branch.
3.  Submit a PR with a description of changes.
