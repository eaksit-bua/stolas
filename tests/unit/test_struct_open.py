"""Unit tests for the dual-form @struct decorator: open=False vs open=True.

``open=False`` (bare ``@struct`` and ``@struct(open=False)``) must stay
byte-identical to the historical struct: frozen, ``__slots__``-only, hashable,
and NOT subclassable. ``open=True`` opts into subclassing while keeping the base
struct itself immutable.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.serde import from_dict, to_dict
from stolas.struct import struct


@struct
class Bare:
    x: int
    y: int


@struct(open=False)
class ClosedExplicit:
    x: int
    y: int


@struct(open=True)
class Open:
    x: int
    y: int


# --- open=False (bare AND explicit) is byte-identical to the historical struct ---


class TestBareStructUnchanged:
    """A bare @struct keeps every historical guarantee."""

    def test_bare_struct_constructs_from_keywords(self) -> None:
        assert Bare(x=1, y=2).x == 1

    def test_bare_struct_blocks_mutation(self) -> None:
        with pytest.raises(AttributeError, match="immutable"):
            Bare(x=1, y=2).x = 9

    def test_bare_struct_blocks_deletion(self) -> None:
        with pytest.raises(AttributeError, match="immutable"):
            del Bare(x=1, y=2).x

    def test_bare_struct_blocks_inheritance(self) -> None:
        with pytest.raises(TypeError, match="Cannot inherit"):

            class Sub(Bare):
                z: int

    def test_bare_struct_keeps_init_subclass_guard_in_dict(self) -> None:
        assert "__init_subclass__" in Bare.__dict__

    def test_bare_struct_has_no_instance_dict(self) -> None:
        assert not hasattr(Bare(x=1, y=2), "__dict__")

    def test_bare_struct_repr(self) -> None:
        assert repr(Bare(x=1, y=2)) == "Bare(x=1, y=2)"

    def test_bare_struct_equal_instances_compare_equal(self) -> None:
        assert Bare(x=1, y=2) == Bare(x=1, y=2)

    def test_bare_struct_equal_instances_hash_equal(self) -> None:
        assert hash(Bare(x=1, y=2)) == hash(Bare(x=1, y=2))

    def test_bare_struct_slots(self) -> None:
        assert Bare.__slots__ == ("x", "y")

    def test_bare_struct_match_args(self) -> None:
        assert Bare.__match_args__ == ("x", "y")


class TestExplicitClosedMatchesBare:
    """@struct(open=False) produces the same namespace as bare @struct."""

    def test_namespace_keys_identical_to_bare(self) -> None:
        assert set(ClosedExplicit.__dict__) == set(Bare.__dict__)

    def test_explicit_closed_blocks_inheritance(self) -> None:
        with pytest.raises(TypeError, match="Cannot inherit"):

            class Sub(ClosedExplicit):
                z: int

    def test_explicit_closed_keeps_init_subclass_guard(self) -> None:
        assert "__init_subclass__" in ClosedExplicit.__dict__

    def test_explicit_closed_is_immutable(self) -> None:
        with pytest.raises(AttributeError, match="immutable"):
            ClosedExplicit(x=1, y=2).x = 9


# --- open=True allows subclassing while the base stays immutable ---


class TestOpenStructSubclassing:
    """open=True opts into inheritance without losing immutability."""

    def test_open_struct_omits_init_subclass_guard(self) -> None:
        assert "__init_subclass__" not in Open.__dict__

    def test_open_struct_namespace_differs_only_by_init_subclass(self) -> None:
        assert set(Bare.__dict__) - set(Open.__dict__) == {"__init_subclass__"}

    def test_open_struct_subclass_can_be_defined(self) -> None:
        class Sub(Open):
            pass

        assert issubclass(Sub, Open)

    def test_open_struct_subclass_can_be_instantiated(self) -> None:
        class Sub(Open):
            pass

        assert Sub(x=1, y=2).x == 1

    def test_open_struct_base_instance_is_immutable(self) -> None:
        with pytest.raises(AttributeError, match="immutable"):
            Open(x=1, y=2).x = 9

    def test_open_struct_subclass_instance_is_immutable(self) -> None:
        class Sub(Open):
            pass

        with pytest.raises(AttributeError, match="immutable"):
            Sub(x=1, y=2).x = 9


class TestOpenStructPreservesStructBehavior:
    """Everything except the inheritance guard is the same under open=True."""

    def test_open_struct_repr(self) -> None:
        assert repr(Open(x=1, y=2)) == "Open(x=1, y=2)"

    def test_open_struct_equal_instances_compare_equal(self) -> None:
        assert Open(x=1, y=2) == Open(x=1, y=2)

    def test_open_struct_equal_instances_hash_equal(self) -> None:
        assert hash(Open(x=1, y=2)) == hash(Open(x=1, y=2))

    def test_open_struct_slots(self) -> None:
        assert Open.__slots__ == ("x", "y")

    def test_open_struct_match_args(self) -> None:
        assert Open.__match_args__ == ("x", "y")

    def test_open_struct_has_no_instance_dict(self) -> None:
        assert not hasattr(Open(x=1, y=2), "__dict__")

    def test_open_struct_pipeline_operator(self) -> None:
        assert (Open(x=1, y=2) >> (lambda o: o.x + o.y)) == 3

    def test_open_struct_replace_returns_modified_copy(self) -> None:
        assert Open(x=1, y=2).replace(x=7) == Open(x=7, y=2)

    def test_open_struct_replace_revalidates_type(self) -> None:
        with pytest.raises(TypeError, match="expects int"):
            Open(x=1, y=2).replace(x="nope")

    def test_open_struct_rejects_wrong_type_on_construction(self) -> None:
        with pytest.raises(TypeError, match="expects int"):
            Open(x="bad", y=2)

    def test_open_struct_serde_round_trip(self) -> None:
        o = Open(x=1, y=2)
        assert from_dict(Open, to_dict(o)) == o
