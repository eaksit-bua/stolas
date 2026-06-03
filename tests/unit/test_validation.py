"""Unit tests for the stolas.validation generic field validators."""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types.validated import Invalid, Valid
from stolas.validation import (
    all_of,
    any_of,
    between,
    length,
    matches,
    max_val,
    min_val,
    non_empty,
    one_of,
    rule,
)


class TestRule:
    """rule(predicate, message) is the base hook."""

    def test_passing_predicate_returns_valid_with_value(self) -> None:
        assert rule(lambda v: v > 0, "must be positive")(5) == Valid(5)

    def test_failing_predicate_returns_invalid_with_message(self) -> None:
        assert rule(lambda v: v > 0, "must be positive")(-1) == Invalid(
            ["must be positive"]
        )

    def test_predicate_that_raises_returns_invalid_not_exception(self) -> None:
        assert rule(lambda v: v.missing_attr, "boom")(5) == Invalid(["boom"])


class TestMatches:
    """matches(pattern, message) is the regex hook for domain recipes."""

    def test_matching_string_returns_valid(self) -> None:
        assert matches(r"^\d+$")("123") == Valid("123")

    def test_non_matching_string_returns_invalid_with_pattern_in_message(self) -> None:
        result = matches(r"^\d+$")("abc")
        assert result == Invalid(["must match pattern '^\\\\d+$'"])

    def test_non_string_value_returns_invalid_without_raising(self) -> None:
        assert matches(r"\d+")(123) == Invalid(["must match pattern '\\\\d+'"])

    def test_custom_message_overrides_default(self) -> None:
        assert matches(r"^\d+$", "digits only")("abc") == Invalid(["digits only"])


class TestLength:
    """length(min, max) checks len() against inclusive bounds."""

    def test_value_within_both_bounds_returns_valid(self) -> None:
        assert length(min=1, max=5)("abc") == Valid("abc")

    def test_value_shorter_than_min_returns_invalid(self) -> None:
        assert length(min=3)("a") == Invalid(["length must be at least 3, got 1"])

    def test_value_longer_than_max_returns_invalid(self) -> None:
        assert length(max=2)("abcd") == Invalid(["length must be at most 2, got 4"])

    def test_unbounded_length_passes_any_sized_value(self) -> None:
        assert length()("anything") == Valid("anything")

    def test_non_sized_value_returns_invalid_without_raising(self) -> None:
        assert length(min=1)(5) == Invalid(["must have a length, got int"])


class TestBetween:
    """between(lo, hi) is inclusive on both ends."""

    def test_value_inside_range_returns_valid(self) -> None:
        assert between(0, 100)(50) == Valid(50)

    def test_value_equal_to_low_bound_returns_valid(self) -> None:
        assert between(0, 100)(0) == Valid(0)

    def test_value_equal_to_high_bound_returns_valid(self) -> None:
        assert between(0, 100)(100) == Valid(100)

    def test_value_below_low_bound_returns_invalid(self) -> None:
        assert between(0, 100)(-1) == Invalid(["must be between 0 and 100"])

    def test_value_above_high_bound_returns_invalid(self) -> None:
        assert between(0, 100)(101) == Invalid(["must be between 0 and 100"])


class TestMinVal:
    """min_val(n) checks value >= n."""

    def test_value_at_least_n_returns_valid(self) -> None:
        assert min_val(0)(0) == Valid(0)

    def test_value_below_n_returns_invalid(self) -> None:
        assert min_val(0)(-1) == Invalid(["must be at least 0"])


class TestMaxVal:
    """max_val(n) checks value <= n."""

    def test_value_at_most_n_returns_valid(self) -> None:
        assert max_val(10)(10) == Valid(10)

    def test_value_above_n_returns_invalid(self) -> None:
        assert max_val(10)(11) == Invalid(["must be at most 10"])


class TestNonEmpty:
    """non_empty() rejects empty and non-Sized values."""

    def test_non_empty_sized_value_returns_valid(self) -> None:
        assert non_empty()("x") == Valid("x")

    def test_empty_sized_value_returns_invalid(self) -> None:
        assert non_empty()("") == Invalid(["must not be empty"])

    def test_non_sized_value_returns_invalid_without_raising(self) -> None:
        assert non_empty()(5) == Invalid(["must have a length, got int"])


class TestOneOf:
    """one_of(*choices) checks membership."""

    def test_value_in_choices_returns_valid(self) -> None:
        assert one_of("a", "b")("a") == Valid("a")

    def test_value_not_in_choices_returns_invalid(self) -> None:
        assert one_of("a", "b")("z") == Invalid(["must be one of ['a', 'b']"])


class TestAllOf:
    """all_of(*validators) requires every validator to pass."""

    def test_all_passing_returns_valid_wrapping_original_value(self) -> None:
        assert all_of(non_empty(), length(max=10))("hi") == Valid("hi")

    def test_all_passing_returns_original_value_not_combine_all_tuple(self) -> None:
        result = all_of(non_empty(), length(max=10))("hi")
        assert isinstance(result, Valid) and result.value == "hi"

    def test_multiple_failures_accumulate_all_messages_flat(self) -> None:
        assert all_of(min_val(10), max_val(0))(5) == Invalid(
            ["must be at least 10", "must be at most 0"]
        )


class TestAnyOf:
    """any_of(*validators) requires at least one validator to pass."""

    def test_first_validator_passing_returns_valid(self) -> None:
        assert any_of(one_of("y", "n"), matches(r"^\d+$"))("y") == Valid("y")

    def test_later_validator_passing_after_earlier_failure_returns_valid(self) -> None:
        assert any_of(one_of("y", "n"), matches(r"^\d+$"))("123") == Valid("123")

    def test_all_failing_returns_invalid_with_every_message(self) -> None:
        assert any_of(one_of("y", "n"), matches(r"^\d+$"))("zz") == Invalid(
            ["must be one of ['y', 'n']", "must match pattern '^\\\\d+$'"]
        )


class TestValidatorsNeverRaise:
    """No validator lets an exception escape on inapplicable input."""

    def test_between_on_incomparable_value_returns_invalid(self) -> None:
        assert between(0, 100)("not a number") == Invalid(["must be between 0 and 100"])

    def test_min_val_on_incomparable_value_returns_invalid(self) -> None:
        assert min_val(0)("not a number") == Invalid(["must be at least 0"])

    def test_max_val_on_incomparable_value_returns_invalid(self) -> None:
        assert max_val(0)("not a number") == Invalid(["must be at most 0"])
