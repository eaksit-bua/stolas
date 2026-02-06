"""Unit tests for Effect[T] type."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types import Effect


class TestEffectCreation:
    """Tests for Effect creation."""

    def test_creates_effect_with_thunk(self) -> None:
        effect = Effect(lambda: 42)
        assert effect.run() == 42

    def test_effect_repr(self) -> None:
        effect = Effect(lambda: 42)
        assert repr(effect) == "Effect(<thunk>)"

    def test_effect_pure(self) -> None:
        effect = Effect.pure(42)
        assert effect.run() == 42

    def test_effect_defer(self) -> None:
        effect = Effect.defer(lambda x, y: x + y, 10, 20)
        assert effect.run() == 30


class TestEffectImmutability:
    """Tests for immutability."""

    def test_effect_is_immutable(self) -> None:
        effect = Effect(lambda: 42)
        with pytest.raises(AttributeError, match="immutable"):
            effect.thunk = lambda: 99


class TestEffectLaziness:
    """Tests for lazy evaluation."""

    def test_effect_does_not_execute_on_creation(self) -> None:
        executed = []

        def side_effect() -> int:
            executed.append(True)
            return 42

        _ = Effect(side_effect)
        assert len(executed) == 0

    def test_effect_executes_on_run(self) -> None:
        executed = []

        def side_effect() -> int:
            executed.append(True)
            return 42

        effect = Effect(side_effect)
        result = effect.run()

        assert len(executed) == 1
        assert result == 42

    def test_effect_does_not_execute_on_chain(self) -> None:
        executed = []

        def side_effect() -> int:
            executed.append(True)
            return 42

        _ = Effect(side_effect) >> (lambda x: x * 2)
        assert len(executed) == 0


class TestEffectMethods:
    """Tests for Effect methods."""

    def test_effect_map(self) -> None:
        effect = Effect(lambda: 10).map(lambda x: x * 2)
        assert effect.run() == 20

    def test_effect_bind(self) -> None:
        effect = Effect(lambda: 10).bind(lambda x: Effect(lambda: x * 2))
        assert effect.run() == 20

    def test_effect_bind_flattens(self) -> None:
        effect = Effect(lambda: 5).bind(
            lambda x: Effect(lambda: x + 1).bind(lambda y: Effect(lambda: y * 2))
        )
        assert effect.run() == 12


class TestEffectPipeline:
    """Tests for pipeline operator."""

    def test_pipeline_composes_without_executing(self) -> None:
        executed = []

        def step1() -> int:
            executed.append("step1")
            return 10

        def step2(x: int) -> int:
            executed.append("step2")
            return x * 2

        effect = Effect(step1) >> step2
        assert len(executed) == 0

        result = effect.run()
        assert result == 20
        assert executed == ["step1", "step2"]

    def test_chained_pipeline(self) -> None:
        effect = Effect(lambda: 5) >> (lambda x: x + 1) >> (lambda x: x * 2)
        assert effect.run() == 12

    def test_pipeline_with_multiple_effects(self) -> None:
        effect = (
            Effect(lambda: 1)
            >> (lambda x: x + 1)
            >> (lambda x: x + 1)
            >> (lambda x: x + 1)
        )
        assert effect.run() == 4


class TestEffectSideEffects:
    """Tests for side effect handling."""

    def test_captures_side_effects(self) -> None:
        log: list[str] = []

        def log_action() -> str:
            log.append("executed")
            return "done"

        effect = Effect(log_action)
        assert log == []

        result = effect.run()
        assert log == ["executed"]
        assert result == "done"

    def test_multiple_runs_execute_multiple_times(self) -> None:
        counter = [0]

        def increment() -> int:
            counter[0] += 1
            return counter[0]

        effect = Effect(increment)

        assert effect.run() == 1
        assert effect.run() == 2
        assert effect.run() == 3


class TestEffectEdgeCases:
    """Tests for Effect edge cases."""

    def test_thunk_property(self) -> None:
        def thunk():
            return 42

        effect = Effect(thunk)
        assert effect.thunk is thunk

    def test_delattr_raises(self) -> None:
        effect = Effect(lambda: 42)
        with pytest.raises(AttributeError, match="immutable"):
            del effect._thunk

    def test_eq_with_non_effect(self) -> None:
        effect = Effect(lambda: 42)
        result = effect.__eq__("not an effect")
        assert result is NotImplemented

    def test_eq_with_same_thunk(self) -> None:
        def thunk():
            return 42

        e1 = Effect(thunk)
        e2 = Effect(thunk)
        assert e1 == e2

    def test_hash(self) -> None:
        effect = Effect(lambda: 42)
        h = hash(effect)
        assert isinstance(h, int)

    def test_rshift_with_effect_result(self) -> None:
        effect = Effect(lambda: Effect(lambda: 42))
        result = effect >> (lambda x: x + 1)
        assert result.run() == 43


def _run_test_method(instance: object, method_name: str) -> tuple[str, str]:
    """Run a single test method and return result."""
    test_name = f"{instance.__class__.__name__}.{method_name}"
    try:
        getattr(instance, method_name)()
        return (test_name, "✅ PASS")
    except Exception as e:
        return (test_name, f"❌ FAIL: {e}")


def _run_test_class(test_class: type) -> list[tuple[str, str]]:
    """Run all test methods in a test class."""
    instance = test_class()
    results: list[tuple[str, str]] = []
    for method_name in dir(instance):
        if method_name.startswith("test_"):
            results.append(_run_test_method(instance, method_name))
    return results


def _print_results(results: list[tuple[str, str]]) -> None:
    """Print test results summary."""
    for test_name, status in results:
        print(f"{status}: {test_name}")

    passed = sum(1 for _, status in results if "PASS" in status)
    failed = len(results) - passed
    print(f"\nTotal: {len(results)} | ✅ Passed: {passed} | ❌ Failed: {failed}")


if __name__ == "__main__":
    test_classes = [
        TestEffectCreation,
        TestEffectImmutability,
        TestEffectLaziness,
        TestEffectMethods,
        TestEffectPipeline,
        TestEffectSideEffects,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
