"""Integration tests: Cross-Type Bridging.

Tests for seamless transitions between Option, Result, and Validated in pipelines.
Covers Section 4 of the integration test plan.
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.types.option import Some, Nothing, Option
from stolas.types.result import Ok, Error, Result
from stolas.types.validated import Valid, Invalid, Validated
from stolas.struct import struct
from stolas.logic.placeholder import _


# ── Test domain models ──────────────────────────────────────────────────────


@struct
class User:
    id: int
    name: str
    email: str


USERS_DB: dict[int, User] = {
    1: User(id=1, name="Alice", email="alice@example.com"),
    2: User(id=2, name="Bob", email="bob_no_at"),
}


# ── Bridge functions ────────────────────────────────────────────────────────


def option_to_result(opt: Option[any], error_msg: str) -> Result[any, str]:
    """Convert Option to Result with custom error message."""
    if opt.is_some():
        return Ok(opt.unwrap())
    return Error(error_msg)


def result_to_option(res: Result[any, any]) -> Option[any]:
    """Convert Result to Option (Error becomes Nothing)."""
    if res.is_ok():
        return Some(res.unwrap())
    return Nothing


def option_to_validated(opt: Option[any], error_msg: str) -> Validated[any, str]:
    """Convert Option to Validated."""
    if opt.is_some():
        return Valid(opt.unwrap())
    return Invalid(error_msg)


def result_to_validated(res: Result[any, any]) -> Validated[any, any]:
    """Convert Result to Validated."""
    if res.is_ok():
        return Valid(res.unwrap())
    return Invalid(res.unwrap_err())


# ── Validation functions returning Result ───────────────────────────────────


def check_email(user: User) -> Result[User, str]:
    """Check if user has valid email."""
    if "@" in user.email:
        return Ok(user)
    return Error(f"Invalid email for {user.name}")


def check_name_length(user: User) -> Result[User, str]:
    """Check if name is at least 3 characters."""
    if len(user.name) >= 3:
        return Ok(user)
    return Error(f"Name too short: {user.name}")


# ── Test Classes ────────────────────────────────────────────────────────────


class TestResultToOption:
    """Test converting Ok/Error to Some/Nothing."""

    def test_ok_to_some(self) -> None:
        """Ok(x) converts to Some(x)."""
        result = result_to_option(Ok(42))
        assert isinstance(result, Some)
        assert result.value == 42

    def test_error_to_nothing(self) -> None:
        """Error converts to Nothing."""
        result = result_to_option(Error("failed"))
        assert result is Nothing

    def test_ok_to_some_with_struct(self) -> None:
        """Ok(User) converts to Some(User)."""
        user = User(id=1, name="Alice", email="alice@test.com")
        result = result_to_option(Ok(user))
        assert isinstance(result, Some)
        assert result.value == user

    def test_in_pipeline(self) -> None:
        """Result to Option conversion in pipeline."""
        # Transform inside Result, then convert to Option
        result = Ok(10) >> (_ * 2)
        opt = result_to_option(result)
        assert isinstance(opt, Some)
        assert opt.value == 20

        # Error short-circuits, result_to_option converts to Nothing
        err_result = Error("oops") >> (_ * 2)
        opt = result_to_option(err_result)
        assert opt is Nothing


class TestOptionToValidated:
    """Test converting Some/Nothing to Valid/Invalid."""

    def test_some_to_valid(self) -> None:
        """Some(x) converts to Valid(x)."""
        result = option_to_validated(Some(42), "Value missing")
        assert isinstance(result, Valid)
        assert result.value == 42

    def test_nothing_to_invalid(self) -> None:
        """Nothing converts to Invalid with error message."""
        result = option_to_validated(Nothing, "Value missing")
        assert isinstance(result, Invalid)
        assert result.errors == ("Value missing",)

    def test_in_pipeline(self) -> None:
        """Option to Validated in pipeline context."""
        # Some flows through
        result = Some(5) >> (_ * 2)
        validated = option_to_validated(result, "Failed")
        assert isinstance(validated, Valid)
        assert validated.value == 10

        # Nothing short-circuits
        result = Nothing >> (_ * 2)
        validated = option_to_validated(result, "Failed")
        assert isinstance(validated, Invalid)


class TestFullBridgePipeline:
    """Test Option -> Result -> Validated with transforms at each stage."""

    def test_full_bridge_happy_path(self) -> None:
        """Option -> Result -> Validated succeeds all the way."""

        def fetch_user(user_id: int) -> Option[User]:
            return Some(USERS_DB.get(user_id)) if user_id in USERS_DB else Nothing

        # Fetch user (Option) -> Check email (Result) -> Convert to Validated
        user_option = fetch_user(1)  # Alice exists
        user_result = option_to_result(user_option, "User not found")
        checked_result = user_result >> check_email
        final = result_to_validated(checked_result)

        assert isinstance(final, Valid)
        assert final.value.name == "Alice"

    def test_full_bridge_option_fails(self) -> None:
        """Nothing at Option stage propagates to Invalid."""

        def fetch_user(user_id: int) -> Option[User]:
            return Some(USERS_DB.get(user_id)) if user_id in USERS_DB else Nothing

        user_option = fetch_user(999)  # Does not exist
        user_result = option_to_result(user_option, "User not found")
        final = result_to_validated(user_result)

        assert isinstance(final, Invalid)
        assert "User not found" in final.errors

    def test_full_bridge_result_fails(self) -> None:
        """Error at Result stage propagates to Invalid."""

        def fetch_user(user_id: int) -> Option[User]:
            return Some(USERS_DB.get(user_id)) if user_id in USERS_DB else Nothing

        user_option = fetch_user(2)  # Bob has invalid email
        user_result = option_to_result(user_option, "User not found")
        checked_result = user_result >> check_email

        assert isinstance(checked_result, Error)

        final = result_to_validated(checked_result)
        assert isinstance(final, Invalid)
        assert "Invalid email" in final.errors[0]


class TestNothingErrorShortCircuit:
    """Verify short-circuit behavior is preserved across type boundaries."""

    def test_nothing_short_circuits_all(self) -> None:
        """Nothing stops pipeline, no further functions called."""
        call_count = 0

        def track_and_transform(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result = Nothing >> track_and_transform >> track_and_transform
        assert result is Nothing
        assert call_count == 0

    def test_error_short_circuits_all(self) -> None:
        """Error stops pipeline, no further functions called."""
        call_count = 0

        def track_and_transform(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result = Error("oops") >> track_and_transform >> track_and_transform
        assert isinstance(result, Error)
        assert call_count == 0

    def test_invalid_short_circuits_map(self) -> None:
        """Invalid >> map is no-op."""
        call_count = 0

        def track_and_transform(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result = Invalid("err") >> track_and_transform
        assert isinstance(result, Invalid)
        assert call_count == 0


class TestCrossTypePipelineChaining:
    """Test chaining across types in realistic scenarios."""

    def test_option_result_chain(self) -> None:
        """Option flows into Result-producing function."""

        def lookup(key: str) -> Option[int]:
            data = {"a": 1, "b": 2}
            return Some(data[key]) if key in data else Nothing

        def validate_positive(x: int) -> Result[int, str]:
            return Ok(x) if x > 0 else Error("Not positive")

        # Option -> Unwrap -> Validate
        opt = lookup("a")
        if opt.is_some():
            result = validate_positive(opt.unwrap())
            assert isinstance(result, Ok)
            assert result.value == 1

    def test_result_option_validated_chain(self) -> None:
        """Result -> Option -> Validated in sequence."""

        def parse_int(s: str) -> Result[int, str]:
            try:
                return Ok(int(s))
            except ValueError:
                return Error(f"Cannot parse: {s}")

        def positive_or_none(x: int) -> Option[int]:
            return Some(x) if x > 0 else Nothing

        # Parse "42" -> Ok(42) -> Some(42) -> Valid(42)
        parsed = parse_int("42")
        assert isinstance(parsed, Ok)

        opt = result_to_option(parsed)
        assert isinstance(opt, Some)

        as_positive = positive_or_none(opt.unwrap())
        final = option_to_validated(as_positive, "Not positive")
        assert isinstance(final, Valid)
        assert final.value == 42

    def test_complex_real_world_pipeline(self) -> None:
        """Real-world: fetch -> validate -> transform -> accumulate."""

        def fetch_users(ids: list[int]) -> list[Option[User]]:
            return [Some(USERS_DB[uid]) if uid in USERS_DB else Nothing for uid in ids]

        def validate_user(user: User) -> Validated[User, str]:
            errors = []
            if "@" not in user.email:
                errors.append(f"Invalid email: {user.email}")
            if len(user.name) < 2:
                errors.append(f"Name too short: {user.name}")
            return Valid(user) if not errors else Invalid(errors)

        # Fetch users and validate
        user_options = fetch_users([1, 2])  # Alice (valid), Bob (invalid email)

        validated_users = []
        for opt in user_options:
            if opt.is_some():
                validated_users.append(validate_user(opt.unwrap()))
            else:
                validated_users.append(Invalid("User not found"))

        # Alice is valid, Bob has invalid email
        assert isinstance(validated_users[0], Valid)
        assert isinstance(validated_users[1], Invalid)
        assert "Invalid email" in validated_users[1].errors[0]
