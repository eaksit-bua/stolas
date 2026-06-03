"""Unit tests for the serde codec: to_dict / from_dict / to_json / from_json."""

import os
import sys
from typing import Any

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import cases
from stolas.serde import from_dict, from_json, to_dict, to_json
from stolas.struct import struct
from stolas.types import (
    Effect,
    Error,
    Invalid,
    Many,
    Nothing,
    Ok,
    Option,
    Result,
    Some,
    Valid,
    Validated,
)


@struct
class Point:
    x: int
    y: int


@struct
class Line:
    start: Point
    end: Point


@cases
class Box:
    Item: Any  # value variant
    Empty: None  # unit variant


@cases
class Shape:
    point: Point  # struct-backed (existing-class) variant
    nothing: None


@struct
class Drawing:
    shape: Shape  # union-typed field
    label: str


class TestToDictPrimitivesAndStructs:
    def test_primitives_passthrough(self) -> None:
        assert to_dict(1) == 1
        assert to_dict("x") == "x"
        assert to_dict(None) is None
        assert to_dict(True) is True

    def test_struct_is_bare_dict(self) -> None:
        assert to_dict(Point(x=1, y=2)) == {"x": 1, "y": 2}

    def test_nested_struct(self) -> None:
        line = Line(start=Point(x=1, y=2), end=Point(x=3, y=4))
        assert to_dict(line) == {
            "start": {"x": 1, "y": 2},
            "end": {"x": 3, "y": 4},
        }

    def test_struct_round_trip(self) -> None:
        line = Line(start=Point(x=1, y=2), end=Point(x=3, y=4))
        assert from_dict(Line, to_dict(line)) == line


class TestToDictMonads:
    def test_ok(self) -> None:
        assert to_dict(Ok(5)) == {"__tag__": "Ok", "value": 5}

    def test_error(self) -> None:
        assert to_dict(Error("boom")) == {"__tag__": "Error", "error": "boom"}

    def test_some(self) -> None:
        assert to_dict(Some(7)) == {"__tag__": "Some", "value": 7}

    def test_nothing(self) -> None:
        assert to_dict(Nothing) == {"__tag__": "Nothing"}

    def test_valid(self) -> None:
        assert to_dict(Valid(1)) == {"__tag__": "Valid", "value": 1}

    def test_invalid(self) -> None:
        assert to_dict(Invalid(["a", "b"])) == {
            "__tag__": "Invalid",
            "errors": ["a", "b"],
        }

    def test_many(self) -> None:
        assert to_dict(Many([1, 2])) == {"__tag__": "Many", "items": [1, 2]}

    def test_nested_monad_and_struct(self) -> None:
        assert to_dict(Ok(Point(x=1, y=2))) == {
            "__tag__": "Ok",
            "value": {"x": 1, "y": 2},
        }

    def test_effect_not_serializable(self) -> None:
        with pytest.raises(TypeError, match="not serializable"):
            to_dict(Effect.pure(1))


class TestMonadRoundTrip:
    def test_result_ok(self) -> None:
        assert from_dict(Result, to_dict(Ok(5))) == Ok(5)

    def test_result_error(self) -> None:
        assert from_dict(Result, to_dict(Error("x"))) == Error("x")

    def test_option_some(self) -> None:
        assert from_dict(Option, to_dict(Some(7))) == Some(7)

    def test_option_nothing(self) -> None:
        assert from_dict(Option, to_dict(Nothing)) is Nothing

    def test_validated(self) -> None:
        assert from_dict(Validated, to_dict(Valid(1))) == Valid(1)
        assert from_dict(Validated, to_dict(Invalid(["e"]))) == Invalid(["e"])

    def test_many_of_structs_parameterized(self) -> None:
        # Bug C: a Many of structs only round-trips with a parameterized target.
        m = Many([Point(x=1, y=2), Point(x=3, y=4)])
        assert from_dict(Many[Point], to_dict(m)) == m

    def test_bad_tag_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid for target"):
            from_dict(Result, {"__tag__": "Nope", "value": 1})


class TestCasesSerde:
    def test_value_variant_self_tags(self) -> None:
        assert to_dict(Box.Item(7)) == {"__tag__": "Item", "value": 7}

    def test_unit_variant_self_tags(self) -> None:
        assert to_dict(Box.Empty) == {"__tag__": "Empty"}

    def test_value_variant_round_trip(self) -> None:
        assert from_dict(Box, to_dict(Box.Item(7))) == Box.Item(7)

    def test_unit_variant_round_trip(self) -> None:
        assert from_dict(Box, to_dict(Box.Empty)) is Box.Empty

    def test_struct_backed_variant_in_field_is_tagged(self) -> None:
        d = Drawing(shape=Point(x=3, y=4), label="hi")
        assert to_dict(d) == {
            "shape": {"__tag__": "point", "value": {"x": 3, "y": 4}},
            "label": "hi",
        }

    def test_struct_backed_variant_round_trip(self) -> None:
        d = Drawing(shape=Point(x=3, y=4), label="hi")
        assert from_dict(Drawing, to_dict(d)) == d

    def test_unit_variant_in_field_round_trip(self) -> None:
        d = Drawing(shape=Shape.nothing, label="x")
        assert from_dict(Drawing, to_dict(d)) == d

    def test_many_of_variants_round_trip(self) -> None:
        m = Many([Box.Item(1), Box.Empty])
        assert from_dict(Many[Box], to_dict(m)) == m

    def test_unknown_tag_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown variant"):
            from_dict(Box, {"__tag__": "Nope", "value": 1})

    def test_missing_tag_raises(self) -> None:
        with pytest.raises(ValueError, match="tagged dict"):
            from_dict(Box, {"value": 1})

    def test_value_variant_missing_value_raises(self) -> None:
        with pytest.raises(ValueError, match="requires a 'value'"):
            from_dict(Box, {"__tag__": "Item"})


class TestContainers:
    def test_list(self) -> None:
        assert to_dict([Point(x=1, y=2)]) == [{"x": 1, "y": 2}]

    def test_tuple_becomes_array(self) -> None:
        assert to_dict((1, "a")) == [1, "a"]

    def test_set_becomes_array(self) -> None:
        assert sorted(to_dict({1, 2, 3})) == [1, 2, 3]

    def test_dict_str_keys(self) -> None:
        assert to_dict({"a": Point(x=1, y=2)}) == {"a": {"x": 1, "y": 2}}

    def test_dict_non_str_key_raises(self) -> None:
        with pytest.raises(TypeError, match="keys must be str"):
            to_dict({1: "a"})

    def test_unserializable_raises(self) -> None:
        with pytest.raises(TypeError, match="Cannot serialize"):
            to_dict(object())

    def test_from_dict_list(self) -> None:
        assert from_dict(list[Point], [{"x": 1, "y": 2}]) == [Point(x=1, y=2)]

    def test_from_dict_tuple_fixed(self) -> None:
        assert from_dict(tuple[int, str], [1, "a"]) == (1, "a")

    def test_from_dict_tuple_variadic(self) -> None:
        assert from_dict(tuple[int, ...], [1, 2, 3]) == (1, 2, 3)

    def test_from_dict_set(self) -> None:
        assert from_dict(set[int], [1, 2, 3]) == {1, 2, 3}

    def test_from_dict_dict(self) -> None:
        assert from_dict(dict[str, Point], {"a": {"x": 1, "y": 2}}) == {
            "a": Point(x=1, y=2)
        }


class TestFromDictStruct:
    def test_unknown_key_raises(self) -> None:
        with pytest.raises(TypeError, match="Unknown fields"):
            from_dict(Point, {"x": 1, "y": 2, "z": 3})

    def test_missing_field_uses_default(self) -> None:
        @struct
        class C:
            name: str
            timeout: int = 30

        assert from_dict(C, {"name": "a"}) == C(name="a", timeout=30)

    def test_non_dict_raises(self) -> None:
        with pytest.raises(TypeError, match="Expected dict"):
            from_dict(Point, [1, 2])

    def test_any_target_passthrough(self) -> None:
        assert from_dict(Any, {"raw": 1}) == {"raw": 1}


class TestJson:
    def test_round_trip(self) -> None:
        p = Point(x=1, y=2)
        assert from_json(Point, to_json(p)) == p

    def test_indent_produces_newlines(self) -> None:
        assert "\n" in to_json(Point(x=1, y=2), indent=2)

    def test_malformed_json_raises(self) -> None:
        import json

        with pytest.raises(json.JSONDecodeError):
            from_json(Point, "{not json}")

    def test_cases_json_round_trip(self) -> None:
        assert from_json(Box, to_json(Box.Item(9))) == Box.Item(9)


@struct
class Held:
    box: Box  # union field whose variant is a value variant
    n: int


@struct
class OptionalShape:
    shape: Point | None


class TestUnionFieldsAndEdges:
    def test_value_variant_in_field_is_tagged(self) -> None:
        h = Held(box=Box.Item(7), n=1)
        assert to_dict(h) == {"box": {"__tag__": "Item", "value": 7}, "n": 1}

    def test_value_variant_in_field_round_trip(self) -> None:
        h = Held(box=Box.Item(7), n=1)
        assert from_dict(Held, to_dict(h)) == h

    def test_from_dict_monad_non_dict_raises(self) -> None:
        with pytest.raises(TypeError, match="tagged dict for monad"):
            from_dict(Result, "not a dict")

    def test_optional_field_none(self) -> None:
        o = OptionalShape(shape=None)
        assert from_dict(OptionalShape, to_dict(o)) == o

    def test_optional_field_present(self) -> None:
        o = OptionalShape(shape=Point(x=1, y=2))
        assert from_dict(OptionalShape, to_dict(o)) == o

    def test_ambiguous_union_passthrough(self) -> None:
        # A non-monad union with >1 concrete member can't be disambiguated.
        assert from_dict(int | str, 5) == 5

    def test_cases_union_field_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError, match="variant"):
            Drawing(shape="not a shape", label="x")
