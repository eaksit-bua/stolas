"""Integration tests for Milestone 2 combinators inside ``>>`` pipelines.

Exercises sequence/traverse/partition/combine_all through the dual-mode
``Many.__rshift__`` operator (the factory-combinator usage the milestone
targets) and in composition with the existing collection helpers.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.logic import apply, combine_all, partition, sequence, traverse, where
from stolas.types.effect import Effect
from stolas.types.many import Many
from stolas.types.option import Nothing, Some
from stolas.types.result import Error, Ok
from stolas.types.validated import Invalid, Valid

# ---------------------------------------------------------------------------
# sequence through the >> pipeline
# ---------------------------------------------------------------------------


def test_pipeline_sequence_result_all_ok() -> None:
    assert (Many([Ok(1), Ok(2)]) >> sequence()) == Ok(Many([1, 2]))


def test_pipeline_sequence_result_short_circuits_on_error() -> None:
    assert (Many([Ok(1), Error("e"), Ok(3)]) >> sequence()) == Error("e")


def test_pipeline_sequence_option_all_some() -> None:
    assert (Many([Some(1), Some(2)]) >> sequence()) == Some(Many([1, 2]))


def test_pipeline_sequence_option_short_circuits_on_nothing() -> None:
    assert (Many([Some(1), Nothing]) >> sequence()) is Nothing


def test_pipeline_sequence_validated_accumulates() -> None:
    pipeline = Many([Valid(1), Invalid(["a"]), Invalid(["b"])]) >> sequence()
    assert pipeline == Invalid(["a", "b"])


def test_pipeline_sequence_effect_is_lazy_until_run() -> None:
    ran: list[int] = []

    def make(v: int) -> Effect[int]:
        return Effect(lambda: ran.append(v) or v)

    result = Many([make(1), make(2)]) >> sequence()
    assert ran == []
    assert result.run() == Many([1, 2])


def test_pipeline_sequence_empty_with_kind() -> None:
    assert (Many(()) >> sequence("result")) == Ok(Many(()))


def test_pipeline_sequence_value_error_propagates_through_rshift() -> None:
    with pytest.raises(ValueError):
        Many([Ok(1), Some(2)]) >> sequence()


def test_pipeline_sequence_non_monad_value_error_propagates() -> None:
    with pytest.raises(ValueError):
        Many([1, 2, 3]) >> sequence()


# ---------------------------------------------------------------------------
# traverse through the >> pipeline
# ---------------------------------------------------------------------------


def test_pipeline_traverse_result_maps_then_sequences() -> None:
    assert (Many([1, 2, 3]) >> traverse(lambda x: Ok(x * 2))) == Ok(Many([2, 4, 6]))


def test_pipeline_traverse_result_short_circuit_does_not_run_past_failure() -> None:
    seen: list[int] = []

    def f(x: int) -> Ok[int] | Error[str]:
        seen.append(x)
        return Ok(x) if x < 3 else Error("stop")

    result = Many([1, 2, 3, 4, 5]) >> traverse(f)
    assert result == Error("stop")
    assert seen == [1, 2, 3]


def test_pipeline_traverse_validated_accumulates_all() -> None:
    def f(x: int) -> Valid[int] | Invalid[str]:
        return Valid(x) if x % 2 == 0 else Invalid([f"odd-{x}"])

    result = Many([1, 2, 3]) >> traverse(f)
    assert result == Invalid(["odd-1", "odd-3"])


def test_pipeline_traverse_effect_lazy_until_run() -> None:
    ran: list[int] = []

    def f(x: int) -> Effect[int]:
        return Effect(lambda: ran.append(x) or x * 10)

    result = Many([1, 2]) >> traverse(f)
    assert ran == []
    assert result.run() == Many([10, 20])


# ---------------------------------------------------------------------------
# partition through the >> pipeline
# ---------------------------------------------------------------------------


def test_pipeline_partition_returns_unwrapped_tuple_of_many() -> None:
    result = Many([Ok(1), Error("a"), Ok(2)]) >> partition()
    assert result == (Many([1, 2]), Many(["a"]))


def test_pipeline_partition_non_result_value_error_propagates() -> None:
    with pytest.raises(ValueError):
        Many([Ok(1), 5]) >> partition()


# ---------------------------------------------------------------------------
# composition with existing collection helpers
# ---------------------------------------------------------------------------


def test_pipeline_apply_then_traverse_composes() -> None:
    result = Many([1, 2, 3]) >> apply(lambda x: x + 1) >> traverse(lambda x: Ok(x))
    assert result == Ok(Many([2, 3, 4]))


def test_pipeline_where_then_sequence_composes() -> None:
    data = Many([Ok(1), Ok(2), Ok(3)])
    result = data >> where(lambda r: r.value % 2 == 1) >> sequence()
    assert result == Ok(Many([1, 3]))


def test_pipeline_partition_oks_feed_into_further_pipeline() -> None:
    oks, _errors = Many([Ok(1), Error("e"), Ok(3)]) >> partition()
    assert (oks >> apply(lambda x: x * 10)) == Many([10, 30])


# ---------------------------------------------------------------------------
# combine_all combined with sequence's Validated branch
# ---------------------------------------------------------------------------


def test_combine_all_matches_sequence_validated_success_values() -> None:
    flat = combine_all(Valid(1), Valid(2), Valid(3))
    seq = Many([Valid(1), Valid(2), Valid(3)]) >> sequence()
    assert flat == Valid((1, 2, 3)) and seq == Valid(Many([1, 2, 3]))


def test_combine_all_matches_sequence_validated_error_accumulation() -> None:
    flat = combine_all(Valid(1), Invalid(["a"]), Invalid(["b"]))
    seq = Many([Valid(1), Invalid(["a"]), Invalid(["b"])]) >> sequence()
    assert flat == Invalid(["a", "b"]) and seq == Invalid(["a", "b"])
