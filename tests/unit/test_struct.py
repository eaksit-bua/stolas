"""Unit tests for @struct decorator."""

import os
import sys
from typing import Any

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.struct import struct


@struct
class Point:
    x: int
    y: int


@struct
class Config:
    name: str
    timeout: int = 30


class TestStructCreation:
    """Tests for struct instance creation."""

    def test_creates_instance_with_fields(self) -> None:
        point = Point(x=1, y=2)
        assert point.x == 1
        assert point.y == 2

    def test_creates_instance_with_defaults(self) -> None:
        config = Config(name="test")
        assert config.name == "test"
        assert config.timeout == 30

    def test_overrides_default_value(self) -> None:
        config = Config(name="test", timeout=60)
        assert config.timeout == 60


class TestStructImmutability:
    """Tests for immutability constraints."""

    def test_blocks_attribute_modification(self) -> None:
        point = Point(x=1, y=2)
        with pytest.raises(AttributeError, match="immutable"):
            point.x = 10

    def test_blocks_attribute_deletion(self) -> None:
        point = Point(x=1, y=2)
        with pytest.raises(AttributeError, match="immutable"):
            del point.x


class TestStructSlots:
    """Tests for slots-only constraint."""

    def test_has_slots(self) -> None:
        assert hasattr(Point, "__slots__")

    def test_no_dict(self) -> None:
        point = Point(x=1, y=2)
        assert not hasattr(point, "__dict__")


class TestStructValidation:
    """Tests for field validation."""

    def test_rejects_wrong_type(self) -> None:
        with pytest.raises(TypeError, match="expects int"):
            Point(x="bad", y=2)

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(TypeError, match="Unknown fields"):
            Point(x=1, y=2, z=3)

    def test_rejects_missing_fields(self) -> None:
        with pytest.raises(TypeError, match="Missing"):
            Point(x=1)


class TestStructInheritance:
    """Tests for inheritance blocking."""

    def test_blocks_inheritance(self) -> None:
        with pytest.raises(TypeError, match="Cannot inherit"):

            class Point3D(Point):
                z: int


class TestStructPatternMatching:
    """Tests for pattern matching support."""

    def test_has_match_args(self) -> None:
        assert Point.__match_args__ == ("x", "y")

    def test_pattern_matching_works(self) -> None:
        point = Point(x=1, y=2)
        match point:
            case Point(x, y):
                assert x == 1
                assert y == 2
            case _:
                pytest.fail("Pattern match failed")


class TestStructHashable:
    """Tests for hashability."""

    def test_equal_instances_have_same_hash(self) -> None:
        point1 = Point(x=1, y=2)
        point2 = Point(x=1, y=2)
        assert hash(point1) == hash(point2)

    def test_usable_in_set(self) -> None:
        point1 = Point(x=1, y=2)
        point2 = Point(x=1, y=2)
        assert len({point1, point2}) == 1


class TestStructEquality:
    """Tests for equality comparison."""

    def test_equal_instances(self) -> None:
        assert Point(x=1, y=2) == Point(x=1, y=2)

    def test_unequal_instances(self) -> None:
        assert Point(x=1, y=2) != Point(x=2, y=3)


class TestStructPipeline:
    """Tests for pipeline operator (>>)."""

    def test_rshift_chains_function(self) -> None:
        def double_x(point: Any) -> Any:
            return Point(x=point.x * 2, y=point.y)

        result = Point(x=1, y=2) >> double_x
        assert result.x == 2
        assert result.y == 2


class TestStructRepr:
    """Tests for string representation."""

    def test_repr_format(self) -> None:
        point = Point(x=1, y=2)
        assert repr(point) == "Point(x=1, y=2)"


class TestStructEqualityEdgeCases:
    """Tests for struct equality edge cases."""

    def test_eq_returns_not_implemented(self) -> None:
        p = Point(x=1, y=2)
        result = p.__eq__("not a point")
        assert result is NotImplemented

    def test_get_field_value_missing_key_raises(self) -> None:
        from stolas.struct.struct import _get_field_value

        with pytest.raises(TypeError, match="Missing required field: z"):
            _get_field_value("z", {"x": 1}, {"y": 2})


class TestStructAnyType:
    """Test struct with Any typed field."""

    def test_any_type_accepts_anything(self) -> None:
        from typing import Any

        @struct
        class Container:
            value: Any

        c1 = Container(value=42)
        c2 = Container(value="string")
        c3 = Container(value=[1, 2, 3])
        assert c1.value == 42
        assert c2.value == "string"
        assert c3.value == [1, 2, 3]


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
        TestStructCreation,
        TestStructImmutability,
        TestStructSlots,
        TestStructValidation,
        TestStructInheritance,
        TestStructPatternMatching,
        TestStructHashable,
        TestStructEquality,
        TestStructPipeline,
        TestStructRepr,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
