"""Integration tests: Trait Dispatch Integration.

Tests for `@trait` polymorphic dispatch working with monadic types.
Covers Section 5 of the integration test plan.
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.logic.placeholder import _
from stolas.struct import struct, trait
from stolas.types.option import Some, Nothing, _Nothing
from stolas.types.result import Ok, Error
from stolas.types.validated import Valid, Invalid


# ── Test Classes ────────────────────────────────────────────────────────────


class TestDispatchOnSomeNothing:
    """Trait with different implementations for Some and Nothing."""

    def test_dispatch_to_some(self) -> None:
        """Trait dispatches correctly to Some implementation."""

        @trait
        def unwrap_or_default(x: object) -> str:
            raise NotImplementedError("No implementation")

        @unwrap_or_default.impl(Some)
        def unwrap_some(x: Some[str]) -> str:
            return x.value

        @unwrap_or_default.impl(_Nothing)
        def unwrap_default(x: _Nothing) -> str:
            return "default"

        assert unwrap_or_default(Some("hello")) == "hello"
        assert unwrap_or_default(Nothing) == "default"

    def test_dispatch_with_transformation(self) -> None:
        """Trait with transformation logic per type."""

        @trait
        def describe_option(x: object) -> str:
            raise NotImplementedError("No implementation")

        @describe_option.impl(Some)
        def describe_some(x: Some[int]) -> str:
            return f"Has value: {x.value}"

        @describe_option.impl(_Nothing)
        def describe_nothing(x: _Nothing) -> str:
            return "Empty"

        assert describe_option(Some(42)) == "Has value: 42"
        assert describe_option(Nothing) == "Empty"


class TestDispatchOnOkError:
    """Trait with different implementations for Ok and Error."""

    def test_dispatch_to_ok(self) -> None:
        """Trait dispatches correctly to Ok implementation."""

        @trait
        def result_message(x: object) -> str:
            raise NotImplementedError("No implementation")

        @result_message.impl(Ok)
        def message_ok(x: Ok[int]) -> str:
            return f"Success: {x.value}"

        @result_message.impl(Error)
        def message_err(x: Error[str]) -> str:
            return f"Failure: {x.error}"

        assert result_message(Ok(100)) == "Success: 100"
        assert result_message(Error("oops")) == "Failure: oops"

    def test_dispatch_with_error_recovery(self) -> None:
        """Trait that recovers from errors."""

        @trait
        def recover(x: object) -> int:
            raise NotImplementedError("No implementation")

        @recover.impl(Ok)
        def recover_ok(x: Ok[int]) -> int:
            return x.value

        @recover.impl(Error)
        def recover_err(x: Error[str]) -> int:
            return -1  # Default value on error

        assert recover(Ok(42)) == 42
        assert recover(Error("failed")) == -1


class TestDispatchOnValidInvalid:
    """Trait with different implementations for Valid and Invalid."""

    def test_dispatch_to_valid(self) -> None:
        """Trait dispatches correctly to Valid implementation."""

        @trait
        def validation_result(x: object) -> str:
            raise NotImplementedError("No implementation")

        @validation_result.impl(Valid)
        def validate_valid(x: Valid[str]) -> str:
            return f"Valid: {x.value}"

        @validation_result.impl(Invalid)
        def validate_invalid(x: Invalid[str]) -> str:
            return f"Invalid with {len(x.errors)} error(s)"

        assert validation_result(Valid("data")) == "Valid: data"
        assert validation_result(Invalid(["e1", "e2"])) == "Invalid with 2 error(s)"

    def test_dispatch_extract_errors(self) -> None:
        """Trait that extracts data differently per type."""

        @trait
        def extract_info(x: object) -> list[str]:
            raise NotImplementedError("No implementation")

        @extract_info.impl(Valid)
        def extract_valid(x: Valid[str]) -> list[str]:
            return [x.value]

        @extract_info.impl(Invalid)
        def extract_invalid(x: Invalid[str]) -> list[str]:
            return list(x.errors)

        assert extract_info(Valid("hello")) == ["hello"]
        assert extract_info(Invalid(["e1", "e2"])) == ["e1", "e2"]


class TestTraitInPipeline:
    """Use trait dispatch within a >> pipeline."""

    def test_trait_in_result_pipeline(self) -> None:
        """Apply trait function in pipeline."""

        @trait
        def double_if_ok(x: object) -> int:
            raise NotImplementedError("No implementation")

        @double_if_ok.impl(Ok)
        def double_ok(x: Ok[int]) -> int:
            return x.value * 2

        @double_if_ok.impl(Error)
        def zero_on_error(x: Error[str]) -> int:
            return 0

        # Use trait in pipeline
        result = Ok(5)
        doubled = double_if_ok(result)
        assert doubled == 10

        error_result = Error("oops")
        doubled = double_if_ok(error_result)
        assert doubled == 0

    def test_trait_after_pipeline_transform(self) -> None:
        """Pipeline transforms data, then trait dispatches on result."""

        @trait
        def format_result(x: object) -> str:
            raise NotImplementedError("No implementation")

        @format_result.impl(Ok)
        def format_ok(x: Ok[int]) -> str:
            return f"Got {x.value}"

        @format_result.impl(Error)
        def format_err(x: Error[str]) -> str:
            return f"Error: {x.error}"

        pipeline_result = Ok(5) >> (_ * 2)
        assert format_result(pipeline_result) == "Got 10"

        error_pipeline = Error("failed") >> (_ * 2)
        assert format_result(error_pipeline) == "Error: failed"


class TestTraitMROLookup:
    """Verify trait dispatch respects method resolution order for subclasses."""

    def test_mro_lookup_with_inheritance(self) -> None:
        """Trait finds implementation via MRO."""

        class Animal:
            pass

        class Dog(Animal):
            pass

        class Cat(Animal):
            pass

        @trait
        def speak(x: object) -> str:
            raise NotImplementedError("No implementation")

        @speak.impl(Animal)
        def speak_animal(x: Animal) -> str:
            return "Generic animal sound"

        @speak.impl(Dog)
        def speak_dog(x: Dog) -> str:
            return "Woof!"

        # Dog has specific impl, Cat falls back to Animal
        assert speak(Dog()) == "Woof!"
        assert speak(Cat()) == "Generic animal sound"

    def test_mro_with_struct_types(self) -> None:
        """Trait works with @struct types."""

        @struct
        class Point:
            x: int
            y: int

        @struct
        class Point3D:
            x: int
            y: int
            z: int

        @trait
        def dimensions(x: object) -> int:
            raise NotImplementedError("No implementation")

        @dimensions.impl(Point)
        def dimensions_2d(p: Point) -> int:
            return 2

        @dimensions.impl(Point3D)
        def dimensions_3d(p: Point3D) -> int:
            return 3

        assert dimensions(Point(x=1, y=2)) == 2
        assert dimensions(Point3D(x=1, y=2, z=3)) == 3


class TestTraitWithMultipleMonadicTypes:
    """Single trait handling multiple monadic types."""

    def test_unified_trait_for_all_types(self) -> None:
        """One trait handles Option, Result, and Validated."""

        @trait
        def is_success(x: object) -> bool:
            raise NotImplementedError("No implementation")

        @is_success.impl(Some)
        def is_success_some(x: Some[object]) -> bool:
            return True

        @is_success.impl(_Nothing)
        def is_success_nothing(x: _Nothing) -> bool:
            return False

        @is_success.impl(Ok)
        def is_success_ok(x: Ok[object]) -> bool:
            return True

        @is_success.impl(Error)
        def is_success_error(x: Error[object]) -> bool:
            return False

        @is_success.impl(Valid)
        def is_success_valid(x: Valid[object]) -> bool:
            return True

        @is_success.impl(Invalid)
        def is_success_invalid(x: Invalid[object]) -> bool:
            return False

        # Test all types
        assert is_success(Some(1)) is True
        assert is_success(Nothing) is False
        assert is_success(Ok(1)) is True
        assert is_success(Error("x")) is False
        assert is_success(Valid(1)) is True
        assert is_success(Invalid("x")) is False

    def test_trait_require_check(self) -> None:
        """Trait.require checks if implementation exists."""

        @trait
        def process(x: object) -> str:
            raise NotImplementedError("No implementation")

        @process.impl(Some)
        def process_some(x: Some[object]) -> str:
            return "some"

        assert process.require(Some(1)) is True
        assert process.require(Nothing) is False  # No impl for _Nothing

    def test_trait_types_property(self) -> None:
        """Trait.types returns registered types."""

        @trait
        def handle(x: object) -> str:
            raise NotImplementedError("No implementation")

        @handle.impl(Some | _Nothing)
        def handle_option(x: object) -> str:
            return "option"

        @handle.impl(Ok | Error)
        def handle_result(x: object) -> str:
            return "result"

        registered = handle.types
        assert Some in registered
        assert _Nothing in registered
        assert Ok in registered
        assert Error in registered
