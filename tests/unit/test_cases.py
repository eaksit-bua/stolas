"""Unit tests for @cases decorator."""

import os
import sys
from typing import Any

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import cases
from stolas.struct import struct


@cases
class Option:
    Some: Any
    Nothing: None


@cases
class Result:
    Ok: Any
    Error: Any


@struct
class Dog:
    name: str


@struct
class Cat:
    name: str


@cases
class Animal:
    dog: Dog
    cat: Cat


class TestCasesValueVariant:
    """Tests for value variant creation."""

    def test_creates_value_variant(self) -> None:
        some = Option.Some(42)
        assert some.value == 42

    def test_value_variant_repr(self) -> None:
        some = Option.Some(42)
        assert repr(some) == "Option.Some(42)"

    def test_value_variant_equality(self) -> None:
        assert Option.Some(42) == Option.Some(42)
        assert Option.Some(42) != Option.Some(99)

    def test_value_variant_hashable(self) -> None:
        assert hash(Option.Some(42)) == hash(Option.Some(42))
        assert len({Option.Some(42), Option.Some(42)}) == 1

    def test_value_variant_immutable(self) -> None:
        some = Option.Some(42)
        with pytest.raises(AttributeError, match="immutable"):
            some.value = 99


class TestCasesUnitVariant:
    """Tests for unit variant (singleton)."""

    def test_unit_variant_is_singleton(self) -> None:
        nothing1 = Option.Nothing
        nothing2 = Option.Nothing
        assert nothing1 is nothing2

    def test_unit_variant_repr(self) -> None:
        assert repr(Option.Nothing) == "Option.Nothing"

    def test_unit_variant_equality(self) -> None:
        assert Option.Nothing == Option.Nothing

    def test_unit_variant_hashable(self) -> None:
        assert len({Option.Nothing, Option.Nothing}) == 1

    def test_unit_variant_immutable(self) -> None:
        with pytest.raises(AttributeError, match="immutable"):
            Option.Nothing.value = 99


class TestCasesMetadata:
    """Tests for cases metadata."""

    def test_variants_dict(self) -> None:
        assert "Some" in Option._variants
        assert "Nothing" in Option._variants

    def test_union_type(self) -> None:
        assert Option._union is not None


class TestCasesInstanceCheck:
    """Tests for isinstance checks."""

    def test_isinstance_value_variant(self) -> None:
        some = Option.Some(42)
        assert isinstance(some, Option._variants["Some"])

    def test_isinstance_unit_variant(self) -> None:
        assert isinstance(Option.Nothing, Option._variants["Nothing"])

    def test_different_variants_different_types(self) -> None:
        some = Option.Some(42)
        assert not isinstance(some, type(Option.Nothing))


class TestCasesPatternMatching:
    """Tests for pattern matching."""

    def test_match_value_variant(self) -> None:
        opt = Option.Some(42)
        match opt:
            case Option.Some(value):
                assert value == 42
            case _:
                pytest.fail("Should match Some")

    def test_match_unit_variant(self) -> None:
        opt = Option.Nothing
        matched = False
        match opt:
            case Option.Some(_):
                pytest.fail("Should not match Some")
            case _:
                matched = True
        assert matched

    def test_match_multiple_variants(self) -> None:
        def describe(opt: Any) -> str:
            match opt:
                case Option.Some(v):
                    return f"has {v}"
                case _:
                    return "empty"

        assert describe(Option.Some(42)) == "has 42"
        assert describe(Option.Nothing) == "empty"


class TestCasesPipeline:
    """Tests for pipeline operator."""

    def test_value_variant_pipeline(self) -> None:
        result = Option.Some(10) >> (lambda x: x * 2)
        assert result == 20

    def test_unit_variant_pipeline_returns_self(self) -> None:
        result = Option.Nothing >> (lambda x: x * 2)
        assert result is Option.Nothing


class TestCasesExistingTypes:
    """Tests for aliasing existing types."""

    def test_aliases_existing_class(self) -> None:
        assert Animal.dog is Dog
        assert Animal.cat is Cat

    def test_create_via_alias(self) -> None:
        dog = Animal.dog(name="Rex")
        assert dog.name == "Rex"
        assert isinstance(dog, Dog)

    def test_variants_contains_aliases(self) -> None:
        assert "dog" in Animal._variants
        assert "cat" in Animal._variants
        assert Animal._variants["dog"] is Dog


class TestCasesMultipleVariants:
    """Tests for cases with multiple value variants."""

    def test_multiple_value_variants(self) -> None:
        ok = Result.Ok("success")
        error = Result.Error("failed")

        assert ok.value == "success"
        assert error.value == "failed"

    def test_different_variant_types(self) -> None:
        ok = Result.Ok("success")
        error = Result.Error("failed")

        assert type(ok) is not type(error)


class TestCasesImmutability:
    """Tests for @cases variant immutability."""

    def test_value_variant_delattr_raises(self) -> None:
        from typing import Any

        @cases
        class Status:
            Active: Any
            Inactive: None

        instance = Status.Active(1)
        with pytest.raises(AttributeError, match="immutable"):
            del instance._value

    def test_unit_variant_delattr_raises(self) -> None:
        from typing import Any

        @cases
        class Status:
            Active: Any
            Inactive: None

        with pytest.raises(AttributeError, match="immutable"):
            del Status.Inactive._instance  # type: ignore[attr-defined]

    def test_value_variant_eq_different_type(self) -> None:
        from typing import Any

        @cases
        class MyResult:
            Success: Any
            Failure: Any

        success = MyResult.Success(42)
        failure = MyResult.Failure(42)
        assert success != failure


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
        TestCasesValueVariant,
        TestCasesUnitVariant,
        TestCasesMetadata,
        TestCasesInstanceCheck,
        TestCasesPatternMatching,
        TestCasesPipeline,
        TestCasesExistingTypes,
        TestCasesMultipleVariants,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
