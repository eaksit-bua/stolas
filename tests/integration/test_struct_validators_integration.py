"""Integration tests for @struct opt-in field validators (Milestone 3)."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.serde import from_dict
from stolas.struct import replace, struct
from stolas.validation import min_val, non_empty


@struct
class User:
    name: str
    age: int
    __validators__ = {"name": non_empty(), "age": min_val(0)}


@struct
class Plain:
    x: int
    y: int


@struct
class Partial:
    name: str
    age: int
    __validators__ = {"name": non_empty()}


@struct
class DefaultInvalid:
    name: str = ""
    __validators__ = {"name": non_empty()}


@struct
class EmptyValidators:
    x: int
    __validators__ = {}


class TestValidStructConstruction:
    """A struct with validators builds normally when every value is valid."""

    def test_all_valid_values_construct_instance(self) -> None:
        assert User(name="ada", age=36).name == "ada"


class TestValueValidationRaisesValueError:
    """Valid type but invalid value raises ValueError (decision D6)."""

    def test_invalid_value_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            User(name="", age=5)

    def test_invalid_value_does_not_raise_type_error(self) -> None:
        with pytest.raises(ValueError):
            User(name="ada", age=-1)

    def test_value_error_message_includes_field_name(self) -> None:
        with pytest.raises(ValueError, match="name"):
            User(name="", age=5)


class TestExceptionPrecedence:
    """Field/type checks (TypeError) run before value validation (ValueError)."""

    def test_wrong_type_raises_type_error_before_value_validation(self) -> None:
        with pytest.raises(TypeError):
            User(name=123, age=5)

    def test_unknown_field_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            User(name="ada", age=5, bogus=1)

    def test_missing_field_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            User(name="ada")


class TestAggregatedValueError:
    """Multiple failing fields produce one ValueError listing every field."""

    def test_single_value_error_raised_for_two_failing_fields(self) -> None:
        with pytest.raises(ValueError):
            User(name="", age=-1)

    def test_aggregated_message_names_first_failing_field(self) -> None:
        with pytest.raises(ValueError, match="name: must not be empty"):
            User(name="", age=-1)

    def test_aggregated_message_names_second_failing_field(self) -> None:
        with pytest.raises(ValueError, match="age: must be at least 0"):
            User(name="", age=-1)


class TestPartialValidatorCoverage:
    """Only fields listed in __validators__ are value-validated."""

    def test_field_without_validator_entry_is_not_validated(self) -> None:
        assert Partial(name="ok", age=-999).age == -999

    def test_listed_field_is_still_validated(self) -> None:
        with pytest.raises(ValueError):
            Partial(name="", age=0)


class TestInvalidDefault:
    """A default that fails its own validator raises when no override is given."""

    def test_invalid_default_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            DefaultInvalid()

    def test_valid_override_of_invalid_default_constructs(self) -> None:
        assert DefaultInvalid(name="ok").name == "ok"


class TestByteIdenticalWhenAbsent:
    """A struct with no __validators__ is unchanged from a plain struct."""

    def test_plain_struct_has_no_validators_attribute(self) -> None:
        assert hasattr(Plain, "__validators__") is False

    def test_empty_validators_dict_adds_no_class_attribute(self) -> None:
        assert hasattr(EmptyValidators, "__validators__") is False

    def test_validated_struct_exposes_validators_attribute(self) -> None:
        assert hasattr(User, "__validators__") is True

    def test_validators_not_added_to_slots(self) -> None:
        assert "__validators__" not in Plain.__slots__

    def test_plain_struct_repr_unchanged(self) -> None:
        assert repr(Plain(x=1, y=2)) == "Plain(x=1, y=2)"

    def test_plain_struct_equality_unchanged(self) -> None:
        assert Plain(x=1, y=2) == Plain(x=1, y=2)

    def test_plain_struct_hash_unchanged(self) -> None:
        assert hash(Plain(x=1, y=2)) == hash(Plain(x=1, y=2))


class TestReplaceRevalidates:
    """replace() re-runs validators by re-entering __init__."""

    def test_replace_with_invalid_value_raises_value_error(self) -> None:
        user = User(name="ada", age=36)
        with pytest.raises(ValueError):
            replace(user, name="")

    def test_replace_with_valid_value_succeeds(self) -> None:
        user = User(name="ada", age=36)
        assert replace(user, age=40).age == 40

    def test_method_replace_with_invalid_value_raises_value_error(self) -> None:
        user = User(name="ada", age=36)
        with pytest.raises(ValueError):
            user.replace(age=-5)


class TestFromDictRevalidates:
    """serde.from_dict builds validated structs via __init__, so it re-runs them."""

    def test_from_dict_with_invalid_value_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            from_dict(User, {"name": "", "age": 5})

    def test_from_dict_with_valid_values_constructs_instance(self) -> None:
        assert from_dict(User, {"name": "ada", "age": 3}).age == 3
