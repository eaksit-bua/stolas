"""Unit tests for Validated[T, E] type."""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types import Valid, Invalid


class TestValidCreation:
    """Tests for Valid variant creation."""

    def test_creates_valid_with_value(self) -> None:
        validated = Valid(42)
        assert validated.value == 42

    def test_valid_repr(self) -> None:
        assert repr(Valid(42)) == "Valid(42)"

    def test_valid_equality(self) -> None:
        assert Valid(42) == Valid(42)
        assert Valid(42) != Valid(99)

    def test_valid_hashable(self) -> None:
        assert hash(Valid(42)) == hash(Valid(42))
        assert len({Valid(42), Valid(42)}) == 1


class TestInvalidCreation:
    """Tests for Invalid variant creation."""

    def test_creates_invalid_with_single_error(self) -> None:
        validated = Invalid("error")
        assert validated.errors == ("error",)

    def test_creates_invalid_with_error_list(self) -> None:
        validated = Invalid(["error1", "error2"])
        assert validated.errors == ("error1", "error2")

    def test_invalid_repr(self) -> None:
        assert repr(Invalid("error")) == "Invalid(['error'])"

    def test_invalid_equality(self) -> None:
        assert Invalid("error") == Invalid("error")
        assert Invalid("error") != Invalid("other")

    def test_invalid_hashable(self) -> None:
        assert hash(Invalid("x")) == hash(Invalid("x"))
        assert len({Invalid("x"), Invalid("x")}) == 1


class TestValidatedImmutability:
    """Tests for immutability."""

    def test_valid_is_immutable(self) -> None:
        validated = Valid(42)
        with pytest.raises(AttributeError, match="immutable"):
            validated.value = 99

    def test_invalid_is_immutable(self) -> None:
        validated = Invalid("error")
        with pytest.raises(AttributeError, match="immutable"):
            validated.errors = ("other",)


class TestValidatedMethods:
    """Tests for Validated methods."""

    def test_valid_map(self) -> None:
        result = Valid(10).map(lambda x: x * 2)
        assert result.value == 20

    def test_invalid_map_noop(self) -> None:
        result = Invalid("error").map(lambda x: x * 2)
        assert result.errors == ("error",)

    def test_valid_is_valid(self) -> None:
        assert Valid(42).is_valid() is True
        assert Valid(42).is_invalid() is False

    def test_invalid_is_invalid(self) -> None:
        assert Invalid("error").is_valid() is False
        assert Invalid("error").is_invalid() is True


class TestValidatedCombine:
    """Tests for error accumulation."""

    def test_combine_valid_with_valid(self) -> None:
        result = Valid(1).combine(Valid(2))
        assert result.value == (1, 2)

    def test_combine_valid_with_invalid(self) -> None:
        result = Valid(1).combine(Invalid("error"))
        assert result.errors == ("error",)

    def test_combine_invalid_with_valid(self) -> None:
        result = Invalid("error").combine(Valid(1))
        assert result.errors == ("error",)

    def test_combine_invalid_with_invalid_accumulates(self) -> None:
        result = Invalid("error1").combine(Invalid("error2"))
        assert result.errors == ("error1", "error2")

    def test_combine_multiple_invalids(self) -> None:
        result = Invalid(["e1", "e2"]).combine(Invalid(["e3", "e4"]))
        assert result.errors == ("e1", "e2", "e3", "e4")


class TestValidatedPipeline:
    """Tests for pipeline operator."""

    def test_valid_pipeline_with_raw_return(self) -> None:
        result = Valid(10) >> (lambda x: x * 2)
        assert result.value == 20

    def test_valid_pipeline_with_validated_return(self) -> None:
        result = Valid(10) >> (lambda x: Valid(x * 2))
        assert result.value == 20

    def test_valid_pipeline_to_invalid(self) -> None:
        result = Valid(10) >> (lambda x: Invalid("failed"))
        assert result.errors == ("failed",)

    def test_invalid_pipeline_short_circuits(self) -> None:
        result = Invalid("error") >> (lambda x: x * 2)
        assert result.errors == ("error",)

    def test_chained_pipeline(self) -> None:
        result = Valid(5) >> (lambda x: x + 1) >> (lambda x: x * 2)
        assert result.value == 12


class TestValidatedPatternMatching:
    """Tests for pattern matching."""

    def test_match_valid(self) -> None:
        validated = Valid(42)
        match validated:
            case Valid(value):
                assert value == 42
            case _:
                pytest.fail("Should match Valid")

    def test_match_invalid(self) -> None:
        validated = Invalid(["error1", "error2"])
        match validated:
            case Invalid(errors):
                assert errors == ("error1", "error2")
            case _:
                pytest.fail("Should match Invalid")


class TestValidatedEdgeCases:
    """Tests for Validated edge cases."""

    def test_valid_delattr_raises(self) -> None:
        v = Valid(42)
        with pytest.raises(AttributeError, match="immutable"):
            del v._value

    def test_valid_eq_with_non_valid(self) -> None:
        v = Valid(42)
        assert v.__eq__(42) is False

    def test_invalid_delattr_raises(self) -> None:
        inv = Invalid("error")
        with pytest.raises(AttributeError, match="immutable"):
            del inv._errors

    def test_invalid_eq_with_non_invalid(self) -> None:
        inv = Invalid("error")
        assert inv.__eq__("error") is False


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
        TestValidCreation,
        TestInvalidCreation,
        TestValidatedImmutability,
        TestValidatedMethods,
        TestValidatedCombine,
        TestValidatedPipeline,
        TestValidatedPatternMatching,
    ]

    all_results: list[tuple[str, str]] = []
    for cls in test_classes:
        all_results.extend(_run_test_class(cls))

    _print_results(all_results)
