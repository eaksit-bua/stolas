"""Unit tests for struct.replace() and parameterized-generic field validation."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.struct import replace, struct


@struct
class Point:
    x: int
    y: int


@struct
class Config:
    name: str
    timeout: int = 30


@struct
class Bag:
    tags: list[str]
    counts: dict[str, int]
    pair: tuple[int, str]


@struct
class Maybe:
    value: int | None


class TestReplace:
    """Copy-with-changes semantics."""

    def test_changes_one_field(self) -> None:
        p = Point(x=1, y=2)
        assert replace(p, x=9) == Point(x=9, y=2)

    def test_original_unchanged(self) -> None:
        p = Point(x=1, y=2)
        replace(p, x=9)
        assert p == Point(x=1, y=2)

    def test_changes_multiple_fields(self) -> None:
        assert replace(Point(x=1, y=2), x=9, y=8) == Point(x=9, y=8)

    def test_no_changes_returns_equal_but_new(self) -> None:
        p = Point(x=1, y=2)
        clone = replace(p)
        assert clone == p
        assert clone is not p

    def test_method_form(self) -> None:
        assert Point(x=1, y=2).replace(y=5) == Point(x=1, y=5)

    def test_default_carried_over(self) -> None:
        c = Config(name="a")  # timeout defaults to 30
        assert replace(c, name="b") == Config(name="b", timeout=30)

    def test_unknown_field_raises(self) -> None:
        with pytest.raises(TypeError, match="Unknown fields"):
            replace(Point(x=1, y=2), z=3)

    def test_type_invalid_change_raises(self) -> None:
        with pytest.raises(TypeError, match="expects int"):
            replace(Point(x=1, y=2), x="nope")

    def test_replace_on_non_struct_raises(self) -> None:
        with pytest.raises(TypeError, match="expects a @struct"):
            replace(object(), x=1)

    def test_generic_field_preserved(self) -> None:
        b = Bag(tags=["a"], counts={"k": 1}, pair=(1, "x"))
        assert replace(b, tags=["a", "b"]).tags == ["a", "b"]


class TestReplaceFieldNameCollision:
    """A field literally named ``replace`` keeps data; the free fn still works."""

    def test_field_named_replace(self) -> None:
        @struct
        class Weird:
            replace: int
            other: str

        w = Weird(replace=1, other="x")
        assert w.replace == 1  # the field value, not the method
        updated = replace(w, replace=2)
        assert updated.replace == 2 and updated.other == "x"


class TestParameterizedGenericValidation:
    """`@struct` no longer crashes on parameterized generic field types."""

    def test_list_field_constructs(self) -> None:
        assert Bag(tags=["a"], counts={}, pair=(1, "x")).tags == ["a"]

    def test_list_field_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError, match="expects list"):
            Bag(tags="notalist", counts={}, pair=(1, "x"))

    def test_dict_and_tuple_fields(self) -> None:
        b = Bag(tags=[], counts={"k": 2}, pair=(5, "z"))
        assert b.counts == {"k": 2} and b.pair == (5, "z")

    def test_optional_accepts_none_and_value(self) -> None:
        assert Maybe(value=None).value is None
        assert Maybe(value=5).value == 5

    def test_optional_rejects_wrong_type(self) -> None:
        with pytest.raises(TypeError):
            Maybe(value="nope")

    def test_plain_type_message_preserved(self) -> None:
        with pytest.raises(TypeError, match="Field 'x' expects int, got str"):
            Point(x="a", y=2)
