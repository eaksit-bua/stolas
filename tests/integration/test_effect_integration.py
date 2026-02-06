"""Integration tests: Effect Deferred Execution.

Tests for `Effect` lazy execution and composition.
Covers Section 6 of the integration test plan.
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.logic import compose
from stolas.logic.placeholder import _
from stolas.operand import as_effect
from stolas.types.effect import Effect
from stolas.types.result import Ok, Error


# ── Test Classes ────────────────────────────────────────────────────────────


class TestDeferredExecution:
    """Effect(thunk) does not execute until .run() is called."""

    def test_thunk_not_called_on_creation(self) -> None:
        """Creating Effect does not call the thunk."""
        call_count = 0

        def thunk() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        effect = Effect(thunk)
        assert call_count == 0  # Not called yet
        assert isinstance(effect, Effect)

    def test_thunk_called_on_run(self) -> None:
        """Calling .run() executes the thunk."""
        call_count = 0

        def thunk() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        effect = Effect(thunk)
        assert call_count == 0

        result = effect.run()
        assert call_count == 1
        assert result == 42

    def test_run_can_be_called_multiple_times(self) -> None:
        """Each .run() call executes the thunk again."""
        call_count = 0

        def thunk() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        effect = Effect(thunk)

        assert effect.run() == 1
        assert effect.run() == 2
        assert effect.run() == 3
        assert call_count == 3


class TestMultipleCompositions:
    """Effect >> f1 >> f2 >> f3 builds composition without execution."""

    def test_composition_without_execution(self) -> None:
        """Chaining >> does not execute effects."""
        call_count = 0

        def thunk() -> int:
            nonlocal call_count
            call_count += 1
            return 1

        def add_one(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + 1

        effect = Effect(thunk)
        composed = effect >> add_one >> add_one >> add_one

        assert call_count == 0  # Nothing executed yet
        assert isinstance(composed, Effect)

    def test_three_compositions(self) -> None:
        """Three >> compositions build correctly."""
        effect = Effect.pure(1)
        composed = effect >> (_ + 1) >> (_ * 2) >> (_ + 10)

        assert isinstance(composed, Effect)
        # (1 + 1) = 2, then 2 * 2 = 4, then 4 + 10 = 14
        assert composed.run() == 14


class TestRunTriggersAll:
    """Calling .run() executes entire composed chain."""

    def test_run_executes_full_chain(self) -> None:
        """Single .run() executes all composed functions."""
        execution_order: list[str] = []

        def initial() -> int:
            execution_order.append("initial")
            return 1

        def step_one(x: int) -> int:
            execution_order.append("step_one")
            return x + 1

        def step_two(x: int) -> int:
            execution_order.append("step_two")
            return x * 2

        effect = Effect(initial) >> step_one >> step_two

        assert execution_order == []  # Nothing yet

        result = effect.run()

        assert result == 4  # (1 + 1) * 2
        assert execution_order == ["initial", "step_one", "step_two"]

    def test_run_preserves_order(self) -> None:
        """Execution order is preserved in chain."""
        steps: list[int] = []

        effect = (
            Effect.pure(0)
            >> (lambda x: (steps.append(1), x + 1)[1])
            >> (lambda x: (steps.append(2), x + 1)[1])
            >> (lambda x: (steps.append(3), x + 1)[1])
        )

        result = effect.run()
        assert result == 3
        assert steps == [1, 2, 3]


class TestEffectBindFlattening:
    """Effect bind with Effect-returning functions flattens correctly."""

    def test_bind_flattens(self) -> None:
        """Bind with Effect-returning function flattens."""
        effect = Effect.pure(5)

        def double_effect(x: int) -> Effect[int]:
            return Effect.pure(x * 2)

        bound = effect.bind(double_effect)

        assert isinstance(bound, Effect)
        assert bound.run() == 10

    def test_nested_bind_chain(self) -> None:
        """Multiple binds flatten correctly."""
        effect = Effect.pure(1)

        result = (
            effect.bind(compose(_ + 1, Effect.pure))
            .bind(compose(_ * 3, Effect.pure))
            .bind(compose(_ + 10, Effect.pure))
        )

        # 1 + 1 = 2, 2 * 3 = 6, 6 + 10 = 16
        assert result.run() == 16

    def test_rshift_with_effect_returning_function(self) -> None:
        """>> with Effect-returning function handles nesting."""
        effect = Effect.pure(5)

        # When >> receives an Effect, it unwraps via run()
        composed = effect >> compose(_ * 2, Effect.pure)

        result = composed.run()
        # The composed effect contains Effect(10), so we need to run it
        if isinstance(result, Effect):
            assert result.run() == 10
        else:
            assert result == 10


class TestEffectDefer:
    """Effect.defer(func, *args) captures arguments correctly."""

    def test_defer_with_args(self) -> None:
        """Defer captures function and arguments."""

        def add(a: int, b: int) -> int:
            return a + b

        effect = Effect.defer(add, 3, 4)

        assert isinstance(effect, Effect)
        assert effect.run() == 7

    def test_defer_with_kwargs(self) -> None:
        """Defer captures keyword arguments."""

        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        effect = Effect.defer(greet, "Alice", greeting="Hi")

        assert effect.run() == "Hi, Alice!"

    def test_defer_is_lazy(self) -> None:
        """Defer does not execute immediately."""
        call_count = 0

        def tracked(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        effect = Effect.defer(tracked, 42)
        assert call_count == 0

        result = effect.run()
        assert call_count == 1
        assert result == 42


class TestEffectPure:
    """Effect.pure wraps a value in an Effect."""

    def test_pure_wraps_value(self) -> None:
        """Pure creates Effect containing the value."""
        effect = Effect.pure(42)

        assert isinstance(effect, Effect)
        assert effect.run() == 42

    def test_pure_with_complex_value(self) -> None:
        """Pure works with complex values."""
        data = {"key": [1, 2, 3]}
        effect = Effect.pure(data)

        assert effect.run() == data
        assert effect.run() is data  # Same object


class TestPipelineWithEffect:
    """Ok(val) >> as_effect(func) produces Ok(Effect(...))."""

    def test_ok_to_effect(self) -> None:
        """as_effect wraps function result in Effect."""

        @as_effect
        def double(x: int) -> int:
            return x * 2

        effect = double(5)
        assert isinstance(effect, Effect)
        assert effect.run() == 10

    def test_ok_pipeline_with_as_effect(self) -> None:
        """Ok >> as_effect produces Ok(Effect)."""

        @as_effect
        def compute(x: int) -> int:
            return x * 3

        result = Ok(4) >> compute

        assert isinstance(result, Ok)
        effect = result.unwrap()
        assert isinstance(effect, Effect)
        assert effect.run() == 12

    def test_error_skips_as_effect(self) -> None:
        """Error >> as_effect skips computation."""

        @as_effect
        def compute(x: int) -> int:
            return x * 3

        result = Error("failed") >> compute

        assert isinstance(result, Error)
        assert result.error == "failed"


class TestEffectWithSideEffects:
    """Test Effect with real side effects (tracking, state changes)."""

    def test_effect_tracks_side_effects(self) -> None:
        """Side effects happen only on run()."""
        log: list[str] = []

        def log_and_compute() -> int:
            log.append("computing")
            return 42

        effect = Effect(log_and_compute)
        assert log == []

        effect.run()
        assert log == ["computing"]

    def test_composed_effects_track_order(self) -> None:
        """Composed effects execute side effects in order."""
        log: list[str] = []

        effect = (
            Effect(lambda: (log.append("start"), 1)[1])
            >> (lambda x: (log.append("middle"), x + 1)[1])
            >> (lambda x: (log.append("end"), x * 2)[1])
        )

        assert log == []
        result = effect.run()
        assert log == ["start", "middle", "end"]
        assert result == 4


class TestEffectMap:
    """Test Effect.map for value transformation."""

    def test_map_transforms_value(self) -> None:
        """Map applies function to eventual result."""
        effect = Effect.pure(5)
        mapped = effect.map(_ * 2)

        assert isinstance(mapped, Effect)
        assert mapped.run() == 10

    def test_map_is_lazy(self) -> None:
        """Map doesn't execute until run()."""
        call_count = 0

        def transform(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        effect = Effect.pure(5).map(transform)
        assert call_count == 0

        effect.run()
        assert call_count == 1
