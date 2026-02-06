"""Unit tests for @trait decorator."""

import os
import sys
import warnings
from typing import Any

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.struct import MissingImplementationWarning, struct, trait


@struct
class Point:
    x: int
    y: int


@struct
class Circle:
    radius: int


@struct
class Rectangle:
    width: int
    height: int


@struct
class Person:
    name: str
    age: int


@struct
class Employee:
    name: str
    department: str


@struct
class Dog:
    name: str


@struct
class Cat:
    name: str


@struct
class Mouse:
    name: str


class TestTraitDispatch:
    """Tests for single dispatch functionality."""

    def test_dispatches_by_first_argument_type(self) -> None:
        @trait
        def describe(x: Any) -> str:
            pass

        @describe.impl(Point)
        def describe_point(p: Point) -> str:
            return f"Point({p.x}, {p.y})"

        @describe.impl(Circle)
        def describe_circle(c: Circle) -> str:
            return f"Circle(r={c.radius})"

        assert describe(Point(x=1, y=2)) == "Point(1, 2)"
        assert describe(Circle(radius=5)) == "Circle(r=5)"

    def test_raises_not_implemented_for_unknown_type(self) -> None:
        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            return p.x + p.y

        with pytest.warns(MissingImplementationWarning, match="No implementation"):
            with pytest.raises(NotImplementedError, match="No implementation"):
                process(Circle(radius=5))


class TestTraitMultiTarget:
    """Tests for single dispatch with union types (same impl for multiple types)."""

    def test_impl_with_separate_registrations(self) -> None:
        """Separate impl() calls for different types."""
        @trait
        def area(shape: Any) -> int:
            pass

        @area.impl(Circle)
        def area_circle(shape: Circle) -> int:
            return shape.radius * shape.radius * 3

        @area.impl(Rectangle)
        def area_rect(shape: Rectangle) -> int:
            return shape.width * shape.height

        assert area(Circle(radius=2)) == 12
        assert area(Rectangle(width=3, height=4)) == 12

    def test_impl_with_union_type(self) -> None:
        """Union type registers same impl for all types in union."""
        @trait
        def stringify(x: Any) -> str:
            pass

        @stringify.impl(Point | Circle | Rectangle)
        def stringify_shape(x: Any) -> str:
            return f"shape:{type(x).__name__}"

        assert stringify(Point(x=1, y=2)) == "shape:Point"
        assert stringify(Circle(radius=5)) == "shape:Circle"
        assert stringify(Rectangle(width=3, height=4)) == "shape:Rectangle"

    def test_union_types_in_types_property(self) -> None:
        """Union types are unwrapped and all appear in .types property."""
        @trait
        def process(x: Any) -> str:
            pass

        @process.impl(Dog | Cat | Mouse)
        def process_animal(x: Any) -> str:
            return x.name

        assert Dog in process.types
        assert Cat in process.types
        assert Mouse in process.types


class TestTraitMultiDispatch:
    """Tests for multi-argument dispatch."""

    def test_dispatch_on_two_arguments(self) -> None:
        @trait
        def interact(a: Any, b: Any) -> str:
            raise NotImplementedError

        @interact.impl(Dog, Cat)
        def dog_cat(dog: Dog, cat: Cat) -> str:
            return f"{dog.name} chases {cat.name}"

        @interact.impl(Cat, Dog)
        def cat_dog(cat: Cat, dog: Dog) -> str:
            return f"{cat.name} hisses at {dog.name}"

        assert interact(Dog(name="Rex"), Cat(name="Whiskers")) == "Rex chases Whiskers"
        assert interact(Cat(name="Whiskers"), Dog(name="Rex")) == "Whiskers hisses at Rex"

    def test_dispatch_on_three_arguments(self) -> None:
        @trait
        def meeting(a: Any, b: Any, c: Any) -> str:
            raise NotImplementedError

        @meeting.impl(Dog, Cat, Mouse)
        def dog_cat_mouse(dog: Dog, cat: Cat, mouse: Mouse) -> str:
            return f"{dog.name} watches {cat.name} chase {mouse.name}"

        result = meeting(Dog(name="Rex"), Cat(name="Whiskers"), Mouse(name="Jerry"))
        assert result == "Rex watches Whiskers chase Jerry"

    def test_multi_dispatch_with_mro(self) -> None:
        """Multi-dispatch should respect MRO for each argument."""

        class Animal:
            def __init__(self, name: str):
                self.name = name

        class Canine(Animal):
            pass

        class Feline(Animal):
            pass

        @trait
        def encounter(a: Any, b: Any) -> str:
            raise NotImplementedError

        @encounter.impl(Animal, Animal)
        def animal_animal(a: Animal, b: Animal) -> str:
            return f"{a.name} meets {b.name}"

        @encounter.impl(Canine, Feline)
        def canine_feline(a: Canine, b: Feline) -> str:
            return f"{a.name} barks at {b.name}"

        # Specific match
        assert encounter(Canine("Rex"), Feline("Whiskers")) == "Rex barks at Whiskers"
        # Falls back to Animal, Animal
        assert encounter(Feline("Whiskers"), Canine("Rex")) == "Whiskers meets Rex"

    def test_multi_dispatch_require(self) -> None:
        @trait
        def interact(a: Any, b: Any) -> str:
            raise NotImplementedError

        @interact.impl(Dog, Cat)
        def dog_cat(dog: Dog, cat: Cat) -> str:
            return "dog-cat"

        assert interact.require(Dog(name="Rex"), Cat(name="Whiskers")) is True
        assert interact.require(Cat(name="Whiskers"), Dog(name="Rex")) is False

    def test_multi_dispatch_check(self) -> None:
        @trait
        def interact(a: Any, b: Any) -> str:
            raise NotImplementedError

        @interact.impl(Dog, Cat)
        def dog_cat(dog: Dog, cat: Cat) -> str:
            return "dog-cat"

        interact.check(Dog(name="Rex"), Cat(name="Whiskers"))  # Should not raise

        with pytest.raises(TypeError, match="No implementation"):
            interact.check(Cat(name="Whiskers"), Dog(name="Rex"))

    def test_multi_dispatch_signatures_property(self) -> None:
        @trait
        def interact(a: Any, b: Any) -> str:
            raise NotImplementedError

        @interact.impl(Dog, Cat)
        def dog_cat(dog: Dog, cat: Cat) -> str:
            return "dog-cat"

        @interact.impl(Cat, Dog)
        def cat_dog(cat: Cat, dog: Dog) -> str:
            return "cat-dog"

        assert (Dog, Cat) in interact.signatures
        assert (Cat, Dog) in interact.signatures


class TestTraitWarnings:
    """Tests for missing implementation warnings."""

    def test_warns_on_missing_single_dispatch(self) -> None:
        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            return p.x + p.y

        with pytest.warns(MissingImplementationWarning, match="process.*Circle"):
            with pytest.raises(NotImplementedError):
                process(Circle(radius=5))

    def test_warns_on_missing_multi_dispatch(self) -> None:
        @trait
        def interact(a: Any, b: Any) -> str:
            raise NotImplementedError

        @interact.impl(Dog, Cat)
        def dog_cat(dog: Dog, cat: Cat) -> str:
            return "dog-cat"

        with pytest.warns(MissingImplementationWarning, match="interact.*Mouse, Dog"):
            with pytest.raises(NotImplementedError):
                interact(Mouse(name="Jerry"), Dog(name="Rex"))

    def test_warning_includes_trait_name(self) -> None:
        @trait
        def my_custom_trait(x: Any) -> str:
            raise NotImplementedError

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                my_custom_trait(Circle(radius=5))
            except NotImplementedError:
                pass

            assert len(w) == 1
            assert "my_custom_trait" in str(w[0].message)


class TestTraitValidation:
    """Tests for require and check methods."""

    def test_require_returns_true_for_registered_type(self) -> None:
        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            return p.x

        assert process.require(Point(x=1, y=2)) is True

    def test_require_returns_false_for_unknown_type(self) -> None:
        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            return p.x

        assert process.require(Circle(radius=5)) is False

    def test_check_passes_for_registered_type(self) -> None:
        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            return p.x

        process.check(Point(x=1, y=2))

    def test_check_raises_for_unknown_type(self) -> None:
        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            return p.x

        with pytest.raises(TypeError, match="No implementation"):
            process.check(Circle(radius=5))


class TestTraitIntrospection:
    """Tests for types introspection."""

    def test_types_returns_registered_types(self) -> None:
        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            return p.x

        @process.impl(Circle)
        def process_circle(c: Circle) -> int:
            return c.radius

        assert set(process.types) == {Point, Circle}


class TestTraitCaching:
    """Tests for dispatch caching."""

    def test_caching_works_for_repeated_calls(self) -> None:
        call_count = 0

        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            nonlocal call_count
            call_count += 1
            return p.x

        process(Point(x=1, y=2))
        process(Point(x=3, y=4))
        process(Point(x=5, y=6))

        assert call_count == 3

    def test_multi_dispatch_caching(self) -> None:
        """Multi-dispatch cache hit on repeated calls with same type signature."""
        call_count = 0

        @trait
        def interact(a: Any, b: Any) -> str:
            raise NotImplementedError

        @interact.impl(Dog, Cat)
        def dog_cat(dog: Dog, cat: Cat) -> str:
            nonlocal call_count
            call_count += 1
            return f"{dog.name}-{cat.name}"

        # First call - cache miss
        result1 = interact(Dog(name="Rex"), Cat(name="Whiskers"))
        # Second call - cache hit (same type signature)
        result2 = interact(Dog(name="Buddy"), Cat(name="Mittens"))
        # Third call - cache hit
        result3 = interact(Dog(name="Max"), Cat(name="Felix"))

        assert result1 == "Rex-Whiskers"
        assert result2 == "Buddy-Mittens"
        assert result3 == "Max-Felix"
        assert call_count == 3


class TestTraitWithPipeline:
    """Tests for trait with struct pipeline operator."""

    def test_trait_works_with_pipeline(self) -> None:
        @trait
        def transform(x: Any) -> Any:
            pass

        @transform.impl(Point)
        def transform_point(p: Point) -> Point:
            return Point(x=p.x * 2, y=p.y * 2)

        result = Point(x=1, y=2) >> transform
        assert result.x == 2
        assert result.y == 4

    def test_chained_pipeline_with_trait(self) -> None:
        @trait
        def double(x: Any) -> Any:
            pass

        @trait
        def add_one(x: Any) -> Any:
            pass

        @double.impl(Point)
        def double_point(p: Point) -> Point:
            return Point(x=p.x * 2, y=p.y * 2)

        @add_one.impl(Point)
        def add_one_point(p: Point) -> Point:
            return Point(x=p.x + 1, y=p.y + 1)

        result = Point(x=1, y=2) >> double >> add_one
        assert result.x == 3
        assert result.y == 5


class TestTraitWithCasesADT:
    """Tests for trait with @cases ADT types."""

    def test_impl_with_cases_adt_unwraps_union(self) -> None:
        """Using @cases ADT in impl() unwraps its _union to register all variants."""
        from stolas.operand import cases

        @cases
        class Shape:
            Circle: Any  # radius
            Square: Any  # side

        @trait
        def area(shape: Any) -> int:
            pass

        @area.impl(Shape)
        def area_shape(s: Any) -> int:
            if isinstance(s, Shape.Circle):
                return s.value * s.value * 3
            return s.value * s.value

        assert area(Shape.Circle(2)) == 12
        assert area(Shape.Square(3)) == 9
        assert Shape.Circle in area.types
        assert Shape.Square in area.types


class TestTraitEdgeCases:
    """Edge case tests."""

    def test_no_args_raises_type_error(self) -> None:
        @trait
        def process(x: Any) -> Any:
            pass

        @process.impl(Point)
        def process_point(p: Point) -> int:
            return p.x

        with pytest.raises(TypeError, match="requires at least one argument"):
            process()

    def test_single_dispatch_with_extra_args(self) -> None:
        """Single dispatch should pass extra args to the implementation."""

        @trait
        def process(x: Any, multiplier: int = 1) -> int:
            pass

        @process.impl(Point)
        def process_point(p: Point, multiplier: int = 1) -> int:
            return (p.x + p.y) * multiplier

        assert process(Point(x=1, y=2)) == 3
        assert process(Point(x=1, y=2), 2) == 6
        assert process(Point(x=1, y=2), multiplier=3) == 9


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
        TestTraitDispatch,
        TestTraitMultiTarget,
        TestTraitMultiDispatch,
        TestTraitWarnings,
        TestTraitValidation,
        TestTraitIntrospection,
        TestTraitCaching,
        TestTraitWithPipeline,
        TestTraitEdgeCases,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
