"""Unit tests for Milestone 2 monad-collection combinators.

Covers sequence, traverse, partition and combine_all in
``stolas.logic.collection``: fail-fast Result/Option, accumulating
Validated, lazy Effect, empty/kind rules, heterogeneity/non-monad
ValueError paths, traverse short-circuit, partition split and the flat
combine_all accumulator.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.logic import combine_all, partition, sequence, traverse
from stolas.types.effect import Effect
from stolas.types.many import Many
from stolas.types.option import Nothing, Some, _Nothing
from stolas.types.result import Error, Ok
from stolas.types.validated import Invalid, Valid

# ---------------------------------------------------------------------------
# Exports / import surface
# ---------------------------------------------------------------------------


def test_combinators_importable_from_logic_package() -> None:
    from stolas.logic import combine_all, partition, sequence, traverse  # noqa: F401


def test_combinators_are_listed_in_logic_all() -> None:
    import stolas.logic as logic

    assert {"sequence", "traverse", "partition", "combine_all"} <= set(logic.__all__)


# ---------------------------------------------------------------------------
# sequence :: Result (fail-fast)
# ---------------------------------------------------------------------------


def test_sequence_result_all_ok_yields_ok_of_many() -> None:
    assert sequence()(Many([Ok(1), Ok(2), Ok(3)])) == Ok(Many([1, 2, 3]))


def test_sequence_result_all_ok_returns_ok_instance() -> None:
    assert isinstance(sequence()(Many([Ok(1), Ok(2)])), Ok)


def test_sequence_result_first_error_short_circuits_to_that_error() -> None:
    assert sequence()(Many([Ok(1), Error("boom"), Ok(3)])) == Error("boom")


def test_sequence_result_returns_the_same_error_object_verbatim() -> None:
    err = Error("boom")
    assert sequence()(Many([Ok(1), err, Ok(3)])) is err


def test_sequence_result_error_in_head_position_returns_that_error() -> None:
    assert sequence()(Many([Error("first"), Ok(2)])) == Error("first")


def test_sequence_result_non_result_after_ok_head_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sequence()(Many([Ok(1), 42]))


# ---------------------------------------------------------------------------
# sequence :: Option (fail-fast)
# ---------------------------------------------------------------------------


def test_sequence_option_all_some_yields_some_of_many() -> None:
    assert sequence()(Many([Some(1), Some(2)])) == Some(Many([1, 2]))


def test_sequence_option_all_some_returns_some_instance() -> None:
    assert isinstance(sequence()(Many([Some(1), Some(2)])), Some)


def test_sequence_option_first_nothing_returns_the_nothing_singleton() -> None:
    assert sequence()(Many([Some(1), Nothing, Some(3)])) is Nothing


def test_sequence_option_nothing_in_head_position_returns_nothing() -> None:
    assert isinstance(sequence()(Many([Nothing, Some(2)])), _Nothing)


def test_sequence_option_non_option_after_some_head_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sequence()(Many([Some(1), "nope"]))


# ---------------------------------------------------------------------------
# sequence :: Validated (accumulating)
# ---------------------------------------------------------------------------


def test_sequence_validated_all_valid_yields_valid_of_many() -> None:
    assert sequence()(Many([Valid(1), Valid(2)])) == Valid(Many([1, 2]))


def test_sequence_validated_all_valid_returns_valid_instance() -> None:
    assert isinstance(sequence()(Many([Valid(1), Valid(2)])), Valid)


def test_sequence_validated_accumulates_all_errors_flat_in_order() -> None:
    result = sequence()(Many([Valid(1), Invalid(["a"]), Invalid(["b", "c"])]))
    assert result == Invalid(["a", "b", "c"])


def test_sequence_validated_invalid_in_head_position_accumulates() -> None:
    assert sequence()(Many([Invalid(["x"]), Valid(2)])) == Invalid(["x"])


def test_sequence_validated_non_validated_after_valid_head_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sequence()(Many([Valid(1), object()]))


# ---------------------------------------------------------------------------
# sequence :: Effect (lazy)
# ---------------------------------------------------------------------------


def test_sequence_effect_returns_an_effect() -> None:
    result = sequence()(Many([Effect.pure(1), Effect.pure(2)]))
    assert isinstance(result, Effect)


def test_sequence_effect_does_not_run_any_thunk_at_sequence_time() -> None:
    ran: list[int] = []

    def make(v: int) -> Effect[int]:
        return Effect(lambda: ran.append(v) or v)

    sequence()(Many([make(1), make(2)]))
    assert ran == []


def test_sequence_effect_run_collects_results_into_many() -> None:
    result = sequence()(Many([Effect.pure(1), Effect.pure(2)]))
    assert result.run() == Many([1, 2])


def test_sequence_effect_non_effect_after_effect_head_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sequence()(Many([Effect.pure(1), 5]))


# ---------------------------------------------------------------------------
# sequence :: empty + kind rules
# ---------------------------------------------------------------------------


def test_sequence_empty_without_kind_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sequence()(Many(()))


def test_sequence_empty_result_kind_yields_ok_of_empty_many() -> None:
    assert sequence("result")(Many(())) == Ok(Many(()))


def test_sequence_empty_option_kind_yields_some_of_empty_many() -> None:
    assert sequence("option")(Many(())) == Some(Many(()))


def test_sequence_empty_validated_kind_yields_valid_of_empty_many() -> None:
    assert sequence("validated")(Many(())) == Valid(Many(()))


def test_sequence_empty_effect_kind_yields_effect_of_empty_many() -> None:
    result = sequence("effect")(Many(()))
    assert isinstance(result, Effect)


def test_sequence_empty_effect_kind_runs_to_empty_many() -> None:
    assert sequence("effect")(Many(())).run() == Many(())


def test_sequence_empty_unknown_kind_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sequence("bogus")(Many(()))


# ---------------------------------------------------------------------------
# sequence :: heterogeneous / non-monad heads
# ---------------------------------------------------------------------------


def test_sequence_heterogeneous_ok_then_some_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sequence()(Many([Ok(1), Some(2)]))


def test_sequence_non_monad_elements_raise_value_error() -> None:
    with pytest.raises(ValueError):
        sequence()(Many([1, 2]))


# ---------------------------------------------------------------------------
# traverse :: Result short-circuit
# ---------------------------------------------------------------------------


def test_traverse_result_all_ok_yields_ok_of_mapped_many() -> None:
    assert traverse(lambda x: Ok(x + 1))(Many([1, 2, 3])) == Ok(Many([2, 3, 4]))


def test_traverse_result_returns_first_error() -> None:
    def f(x: int) -> Ok[int] | Error[str]:
        return Ok(x) if x < 2 else Error(f"bad-{x}")

    assert traverse(f)(Many([0, 1, 2, 3])) == Error("bad-2")


def test_traverse_result_does_not_call_func_past_first_failure() -> None:
    seen: list[int] = []

    def f(x: int) -> Ok[int] | Error[str]:
        seen.append(x)
        return Ok(x) if x < 2 else Error("bad")

    traverse(f)(Many([0, 1, 2, 3, 4]))
    assert seen == [0, 1, 2]


# ---------------------------------------------------------------------------
# traverse :: Option short-circuit
# ---------------------------------------------------------------------------


def test_traverse_option_all_some_yields_some_of_mapped_many() -> None:
    assert traverse(lambda x: Some(x * 2))(Many([1, 2])) == Some(Many([2, 4]))


def test_traverse_option_returns_nothing_on_first_failure() -> None:
    def f(x: int) -> Some[int] | _Nothing:
        return Some(x) if x < 2 else Nothing

    assert traverse(f)(Many([0, 1, 2, 3])) is Nothing


def test_traverse_option_does_not_call_func_past_first_failure() -> None:
    seen: list[int] = []

    def f(x: int) -> Some[int] | _Nothing:
        seen.append(x)
        return Some(x) if x < 2 else Nothing

    traverse(f)(Many([0, 1, 2, 3, 4]))
    assert seen == [0, 1, 2]


# ---------------------------------------------------------------------------
# traverse :: Validated accumulate (func called on every element)
# ---------------------------------------------------------------------------


def test_traverse_validated_all_valid_yields_valid_of_mapped_many() -> None:
    assert traverse(lambda x: Valid(x + 1))(Many([1, 2])) == Valid(Many([2, 3]))


def test_traverse_validated_accumulates_all_errors_flat() -> None:
    def f(x: int) -> Valid[int] | Invalid[str]:
        return Valid(x) if x < 2 else Invalid([f"e{x}"])

    assert traverse(f)(Many([0, 1, 2, 3])) == Invalid(["e2", "e3"])


def test_traverse_validated_calls_func_on_every_element() -> None:
    seen: list[int] = []

    def f(x: int) -> Valid[int] | Invalid[str]:
        seen.append(x)
        return Valid(x) if x < 2 else Invalid([f"e{x}"])

    traverse(f)(Many([0, 1, 2, 3]))
    assert seen == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# traverse :: Effect lazy
# ---------------------------------------------------------------------------


def test_traverse_effect_returns_an_effect() -> None:
    result = traverse(lambda x: Effect.pure(x * 10))(Many([1, 2]))
    assert isinstance(result, Effect)


def test_traverse_effect_does_not_run_thunks_before_run() -> None:
    ran: list[int] = []

    def f(x: int) -> Effect[int]:
        return Effect(lambda: ran.append(x) or x)

    traverse(f)(Many([1, 2]))
    assert ran == []


def test_traverse_effect_run_collects_mapped_results() -> None:
    result = traverse(lambda x: Effect.pure(x * 10))(Many([1, 2]))
    assert result.run() == Many([10, 20])


# ---------------------------------------------------------------------------
# traverse :: empty / kind / non-monad result
# ---------------------------------------------------------------------------


def test_traverse_empty_without_kind_raises_value_error() -> None:
    with pytest.raises(ValueError):
        traverse(lambda x: Ok(x))(Many(()))


def test_traverse_empty_with_kind_yields_success_of_empty() -> None:
    assert traverse(lambda x: Ok(x), "result")(Many(())) == Ok(Many(()))


def test_traverse_non_monad_func_result_raises_value_error() -> None:
    with pytest.raises(ValueError):
        traverse(lambda x: x)(Many([1, 2]))


# ---------------------------------------------------------------------------
# partition
# ---------------------------------------------------------------------------


def test_partition_splits_oks_and_errors_preserving_order() -> None:
    result = partition()(Many([Ok(1), Error("a"), Ok(2), Error("b")]))
    assert result == (Many([1, 2]), Many(["a", "b"]))


def test_partition_all_ok_yields_empty_error_side() -> None:
    assert partition()(Many([Ok(1), Ok(2)])) == (Many([1, 2]), Many(()))


def test_partition_all_error_yields_empty_ok_side() -> None:
    assert partition()(Many([Error("a"), Error("b")])) == (Many(()), Many(["a", "b"]))


def test_partition_returns_a_plain_tuple_not_a_many() -> None:
    result = partition()(Many([Ok(1)]))
    assert isinstance(result, tuple) and not isinstance(result, Many)


def test_partition_non_result_element_raises_value_error() -> None:
    with pytest.raises(ValueError):
        partition()(Many([Ok(1), 7]))


# ---------------------------------------------------------------------------
# combine_all
# ---------------------------------------------------------------------------


def test_combine_all_all_valid_yields_flat_valid_tuple() -> None:
    assert combine_all(Valid(1), Valid(2), Valid(3)) == Valid((1, 2, 3))


def test_combine_all_does_not_nest_tuple_valued_inputs() -> None:
    assert combine_all(Valid((1, 2)), Valid(3)) == Valid(((1, 2), 3))


def test_combine_all_no_args_yields_valid_empty_tuple() -> None:
    assert combine_all() == Valid(())


def test_combine_all_any_invalid_concatenates_all_errors_flat() -> None:
    result = combine_all(Valid(1), Invalid(["a"]), Invalid(["b", "c"]))
    assert result == Invalid(["a", "b", "c"])


def test_combine_all_returns_invalid_instance_when_errors_present() -> None:
    assert isinstance(combine_all(Invalid(["a"])), Invalid)


def test_combine_all_non_validated_arg_raises_value_error() -> None:
    with pytest.raises(ValueError):
        combine_all(Valid(1), 99)
