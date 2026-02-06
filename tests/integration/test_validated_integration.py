"""Integration tests: Validated Error Accumulation.

Tests for `Validated.combine()` accumulating all errors instead of short-circuiting.
Covers Section 3 of the integration test plan.
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types.validated import Valid, Invalid, Validated
from stolas.operand import as_validated
from stolas.struct import struct
from stolas.logic.placeholder import _


# ── Test domain models ──────────────────────────────────────────────────────


@struct
class RegistrationForm:
    username: str
    email: str
    age: int


# ── Validation functions ────────────────────────────────────────────────────


def validate_username(username: str) -> Validated[str, str]:
    """Username must be at least 3 characters."""
    if len(username) < 3:
        return Invalid("Username too short")
    return Valid(username)


def validate_email(email: str) -> Validated[str, str]:
    """Email must contain @."""
    if "@" not in email:
        return Invalid("Invalid email format")
    return Valid(email)


def validate_age(age: int) -> Validated[int, str]:
    """Age must be 18+."""
    if age < 18:
        return Invalid("Must be 18 or older")
    return Valid(age)


# ── Test Classes ────────────────────────────────────────────────────────────


class TestMultipleValidCombines:
    """Test combining multiple Valid values."""

    def test_two_valid_combines(self) -> None:
        """Valid + Valid = Valid with tuple."""
        result = Valid("a").combine(Valid("b"))
        assert isinstance(result, Valid)
        assert result.value == ("a", "b")

    def test_three_valid_combines(self) -> None:
        """Three Valid combines produce nested tuple."""
        result = Valid("a").combine(Valid("b")).combine(Valid("c"))
        assert isinstance(result, Valid)
        assert result.value == (("a", "b"), "c")

    def test_valid_with_integers(self) -> None:
        """Valid combines with integer values."""
        result = Valid(1).combine(Valid(2)).combine(Valid(3))
        assert isinstance(result, Valid)
        assert result.value == ((1, 2), 3)


class TestSingleInvalid:
    """Test Valid combined with Invalid produces Invalid."""

    def test_valid_then_invalid(self) -> None:
        """Valid.combine(Invalid) returns Invalid."""
        result = Valid("a").combine(Invalid("error"))
        assert isinstance(result, Invalid)
        assert result.errors == ("error",)

    def test_invalid_then_valid(self) -> None:
        """Invalid.combine(Valid) returns Invalid."""
        result = Invalid("error").combine(Valid("a"))
        assert isinstance(result, Invalid)
        assert result.errors == ("error",)


class TestMultipleInvalidCombines:
    """Test that multiple Invalid combines accumulate errors."""

    def test_two_invalid_combines(self) -> None:
        """Invalid + Invalid accumulates both errors."""
        result = Invalid("e1").combine(Invalid("e2"))
        assert isinstance(result, Invalid)
        assert result.errors == ("e1", "e2")

    def test_three_invalid_combines(self) -> None:
        """Three Invalid combines accumulate all errors."""
        result = Invalid("e1").combine(Invalid("e2")).combine(Invalid("e3"))
        assert isinstance(result, Invalid)
        assert result.errors == ("e1", "e2", "e3")

    def test_invalid_with_list_errors(self) -> None:
        """Invalid with list of errors combines correctly."""
        result = Invalid(["e1", "e2"]).combine(Invalid(["e3"]))
        assert isinstance(result, Invalid)
        assert result.errors == ("e1", "e2", "e3")


class TestMixedValidInvalidChain:
    """Test complex chains with mixed Valid/Invalid accumulating all errors."""

    def test_valid_invalid_valid_invalid(self) -> None:
        """V + I + V + I only accumulates the Invalid errors."""
        result = (
            Valid("a")
            .combine(Invalid("e1"))
            .combine(Valid("b"))  # This is skipped since already Invalid
            .combine(Invalid("e2"))
        )
        # After first Invalid, it stays Invalid and accumulates new errors
        assert isinstance(result, Invalid)
        assert "e1" in result.errors
        assert "e2" in result.errors

    def test_all_validation_fails(self) -> None:
        """All validations fail, accumulating all errors."""
        username_result = validate_username("ab")  # Too short
        email_result = validate_email("invalid")  # No @
        age_result = validate_age(16)  # Under 18

        combined = username_result.combine(email_result).combine(age_result)

        assert isinstance(combined, Invalid)
        assert len(combined.errors) == 3
        assert "Username too short" in combined.errors
        assert "Invalid email format" in combined.errors
        assert "Must be 18 or older" in combined.errors

    def test_partial_validation_fails(self) -> None:
        """Some validations fail, accumulating only failed errors."""
        username_result = validate_username("alice")  # Valid
        email_result = validate_email("invalid")  # Invalid
        age_result = validate_age(16)  # Invalid

        combined = username_result.combine(email_result).combine(age_result)

        assert isinstance(combined, Invalid)
        assert len(combined.errors) == 2
        assert "Invalid email format" in combined.errors
        assert "Must be 18 or older" in combined.errors

    def test_all_validation_passes(self) -> None:
        """All validations pass, producing Valid with all values."""
        username_result = validate_username("alice")
        email_result = validate_email("alice@example.com")
        age_result = validate_age(25)

        combined = username_result.combine(email_result).combine(age_result)

        assert isinstance(combined, Valid)
        assert combined.value == (("alice", "alice@example.com"), 25)


class TestValidatedInPipeline:
    """Test using >> as_validated in pipeline and combining results."""

    def test_as_validated_success(self) -> None:
        """as_validated wraps successful function call."""

        @as_validated
        def parse_int(s: str) -> int:
            return int(s)

        result = parse_int("42")
        assert isinstance(result, Valid)
        assert result.value == 42

    def test_as_validated_failure(self) -> None:
        """as_validated catches exception as Invalid."""

        @as_validated
        def parse_int(s: str) -> int:
            return int(s)

        result = parse_int("not_a_number")
        assert isinstance(result, Invalid)
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], ValueError)

    def test_validated_map_on_valid(self) -> None:
        """Valid >> transform produces Valid with transformed value."""
        result = Valid(5) >> (_ * 2)
        assert isinstance(result, Valid)
        assert result.value == 10

    def test_validated_map_on_invalid(self) -> None:
        """Invalid >> transform is no-op."""
        result = Invalid("error") >> (_ * 2)
        assert isinstance(result, Invalid)
        assert result.errors == ("error",)

    def test_pipeline_with_validation_functions(self) -> None:
        """Pipeline using validation functions."""
        # Start with Valid and apply validation
        result = Valid("alice") >> validate_username
        assert isinstance(result, Valid)
        assert result.value == "alice"

        # Start with invalid data
        result = Valid("ab") >> validate_username
        assert isinstance(result, Invalid)


class TestValidatedWithStruct:
    """Test Validated with @struct domain objects."""

    def test_validate_struct_fields(self) -> None:
        """Validate fields of a struct independently."""
        form = RegistrationForm(username="ab", email="invalid", age=16)

        username_v = validate_username(form.username)
        email_v = validate_email(form.email)
        age_v = validate_age(form.age)

        combined = username_v.combine(email_v).combine(age_v)

        assert isinstance(combined, Invalid)
        assert len(combined.errors) == 3

    def test_valid_struct_fields(self) -> None:
        """Valid struct produces Valid with all field values."""
        form = RegistrationForm(username="alice", email="alice@test.com", age=25)

        username_v = validate_username(form.username)
        email_v = validate_email(form.email)
        age_v = validate_age(form.age)

        combined = username_v.combine(email_v).combine(age_v)

        assert isinstance(combined, Valid)
