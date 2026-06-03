"""Unit tests for stolas.serde.variant_from_dict.

``variant_from_dict(cls, data)`` reconstructs ONE concrete ``@cases`` variant
instance, complementing ``from_dict`` (which takes the union). It accepts a
value-variant class, a unit variant (class or singleton instance), or an
existing-class variant (a ``@struct``/builtin aliased as a variant), and mirrors
the standalone encodings that ``to_dict`` emits.
"""

import os
import sys
from typing import Any

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import cases
from stolas.serde import to_dict, variant_from_dict
from stolas.struct import struct


@struct
class Point:
    x: int
    y: int


@cases
class Box:
    Item: Any  # value variant
    Empty: None  # unit variant


@cases
class Shape:
    point: Point  # existing-class (struct-backed) variant
    nothing: None  # unit variant


class TestValueVariant:
    """A value variant unwraps the tagged ``value`` payload."""

    def test_round_trips_via_variant_class(self) -> None:
        assert variant_from_dict(Box.Item, to_dict(Box.Item(7))) == Box.Item(7)

    def test_reconstructs_without_tag(self) -> None:
        assert variant_from_dict(Box.Item, {"value": 9}) == Box.Item(9)

    def test_unwraps_nested_struct_value(self) -> None:
        @cases
        class Holder:
            Wrapped: Any

        encoded = to_dict(Holder.Wrapped(Point(x=1, y=2)))
        # value is decoded via from_dict(Any, ...): a struct stays a bare dict.
        assert variant_from_dict(Holder.Wrapped, encoded).value == {"x": 1, "y": 2}

    def test_missing_value_field_raises(self) -> None:
        with pytest.raises(ValueError, match="requires a 'value' field"):
            variant_from_dict(Box.Item, {"__tag__": "Item"})

    def test_tag_naming_other_variant_raises(self) -> None:
        with pytest.raises(ValueError, match="does not match variant"):
            variant_from_dict(Box.Item, {"__tag__": "Empty", "value": 1})


class TestUnitVariant:
    """A unit variant returns its singleton, regardless of how it's referenced."""

    def test_singleton_instance_returns_same_singleton(self) -> None:
        assert variant_from_dict(Box.Empty, to_dict(Box.Empty)) is Box.Empty

    def test_variant_class_returns_singleton(self) -> None:
        assert variant_from_dict(Box._variants["Empty"], {"__tag__": "Empty"}) is (
            Box.Empty
        )

    def test_payload_without_tag_returns_singleton(self) -> None:
        assert variant_from_dict(Box.Empty, {}) is Box.Empty

    def test_tag_naming_other_variant_raises(self) -> None:
        with pytest.raises(ValueError, match="does not match variant"):
            variant_from_dict(Box.Empty, {"__tag__": "Item"})


class TestExistingClassVariant:
    """An existing-class variant (Shape.point -> Point) has no tag of its own."""

    def test_struct_backed_variant_reconstructs_from_bare_dict(self) -> None:
        assert variant_from_dict(Shape.point, {"x": 3, "y": 4}) == Point(x=3, y=4)

    def test_struct_backed_variant_round_trips(self) -> None:
        assert variant_from_dict(Shape.point, to_dict(Point(x=3, y=4))) == Point(
            x=3, y=4
        )
