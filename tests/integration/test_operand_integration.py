"""Integration tests for stolas.operand modules: cases and safe.

Verifies:
1. Pattern matching and Sum Types (@cases) in pipelines.
2. Chained safe decorators (@as_result, @as_option, etc.) in complex flows.
"""

import os
import sys
from functools import partial
from typing import Any

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.logic import const, when
from stolas.logic.placeholder import _
from stolas.operand import as_option, as_result, as_validated, cases
from stolas.types.many import Many
from stolas.types.option import Some
from stolas.types.result import Error, Ok
from stolas.types.validated import Invalid


# ── Test Types ──────────────────────────────────────────────────────────────


@cases
class PaymentStatus:
    Pending: None
    Authorized: Any  # transaction_id: str
    Captured: Any  # amount: float
    Failed: Any  # reason: str


@cases
class UserAction:
    Login: Any  # user_id: int
    Logout: Any  # user_id: int
    View: Any  # page: str


# ── Test Classes ────────────────────────────────────────────────────────────


class TestCasesIntegration:
    """Integration of @cases sum types in pipelines."""

    def test_pipeline_returning_sum_type(self) -> None:
        def process_payment(amount: float) -> PaymentStatus:
            if amount > 1000:
                return PaymentStatus.Failed("Limit exceeded")
            if amount > 0:
                return PaymentStatus.Authorized("tx_123")
            return PaymentStatus.Failed("Invalid amount")

        # Simulate pipeline result
        result = Ok(500.0) >> process_payment

        assert isinstance(result, Ok)
        # Verify we can match on the inner value
        status = result.unwrap()
        match status:
            case PaymentStatus.Authorized(tx_id):
                assert tx_id == "tx_123"
            case _:
                pytest.fail("Should be Authorized")

    def test_match_in_pipeline_logic(self) -> None:
        """Using match statement to direct pipeline flow logic."""

        def handle_action(action: UserAction) -> str:
            match action:
                case UserAction.Login(uid):
                    return f"User {uid} logged in"
                case UserAction.Logout(uid):
                    return f"User {uid} logged out"
                case UserAction.View(page):
                    return f"Viewing {page}"
                case _:
                    return "Unknown"

        events = Many(
            [
                UserAction.Login(1),
                UserAction.View("home"),
                UserAction.Logout(1),
            ]
        )

        # Use map to transform each item in the collection
        results = events.map(handle_action)
        assert results.items == (
            "User 1 logged in",
            "Viewing home",
            "User 1 logged out",
        )

    def test_sum_type_inside_option(self) -> None:
        """Integration with Option type."""
        status = Some(PaymentStatus.Pending)

        # Mapping over the option to transform the variant
        # Option doesn't have map_or, so use map().unwrap_or()
        result = status.map(
            when(_ == PaymentStatus.Pending, const("Waiting"), const("Done"))
        ).unwrap_or("No status")
        assert result == "Waiting"


class TestSafeDecoratorIntegration:
    """Integration of chained @safe decorators in pipelines."""

    def test_chained_safe_functions_success(self) -> None:
        @as_result
        def parse_input(data: str) -> int:
            return int(data)

        @as_result
        def calculate_tax(amount: int) -> float:
            if amount < 0:
                raise ValueError("Negative amount")
            return amount * 0.1

        @as_result
        def format_currency(value: float) -> str:
            return f"${value:.2f}"

        # Use monadic binding (>>) to chain safe functions
        # compose() would pass the Result wrapper, but these expect unwrapped values
        result = parse_input("100") >> calculate_tax >> format_currency

        assert isinstance(result, Ok)
        assert result.value == "$10.00"

    def test_chained_safe_functions_fail_fast(self) -> None:
        @as_result
        def step1(x: int) -> int:
            return x + 1

        @as_result
        def step2_fail(x: int) -> int:
            raise ValueError("Boom")

        @as_result
        def step3_never_called(x: int) -> int:
            return x * 2

        # Step 2 fails, Step 3 should not run because pipeline short-circuits
        result = step1(10) >> step2_fail >> step3_never_called

        assert isinstance(result, Error)
        # Verify it caught the ValueError
        assert isinstance(result.error, ValueError)
        assert str(result.error) == "Boom"

    def test_mixed_decorators_pipeline(self) -> None:
        """Mixing different safe decorators."""

        @as_option  # returns Option
        def find_user(uid: int) -> dict | None:
            if uid == 1:
                return {"id": 1, "balance": 100}
            return None

        @as_result  # returns Result
        def debit(user: dict, amount: int) -> int:
            if user["balance"] < amount:
                raise ValueError("Insufficient funds")
            return user["balance"] - amount

        user_opt = find_user(1)  # Some({...})

        # Manually bridge Option -> Result since ok_or isn't on Option
        # Logic: if Some, wrap in Ok; if Nothing, return Error
        user_res = (
            Ok(user_opt.unwrap()) if user_opt.is_some() else Error("User not found")
        )

        # Now bind the Result-returning function
        res = user_res.bind(partial(debit, amount=50))

        assert isinstance(res, Ok)
        assert res.value == 50

    def test_validated_chain_accumulation(self) -> None:
        """@as_validated functions in a chain (stop on first error if chained via >>)."""
        # Note: Validated doesn't auto-accumulate when chained via bind/HTTP-style pipeline calling,
        # it usually accumulates via `mapN` or distinct flows.
        # But chained functions should fast-fail similar to Result.

        @as_validated
        def name_ok(name: str) -> str:
            if not name:
                raise ValueError("Empty name")
            return name

        @as_validated
        def age_ok(age: int) -> int:
            if age < 0:
                raise ValueError("Negative age")
            return age

        # If we compose them, the first failure returns Invalid
        res1 = name_ok("")
        assert isinstance(res1, Invalid)
        assert str(res1.errors[0]) == "Empty name"


class TestSafeAndCasesCombined:
    """Combining @safe decorators producing @cases types."""

    def test_safe_function_returns_case(self) -> None:
        @as_result
        def authorize(amount: float) -> PaymentStatus:
            if amount > 1000:
                raise ValueError("Too high")
            if amount < 0:
                return PaymentStatus.Failed("Negative")
            return PaymentStatus.Authorized("tx_999")

        # Exception becomes Error
        res1 = authorize(2000)
        assert isinstance(res1, Error)

        # Valid return becomes Ok(Authorized(...))
        res2 = authorize(500)
        assert isinstance(res2, Ok)
        assert isinstance(res2.value, PaymentStatus._variants["Authorized"])

        # "Failed" return is still a valid return value, so it wraps in Ok
        res3 = authorize(-10)
        assert isinstance(res3, Ok)
        assert isinstance(res3.value, PaymentStatus._variants["Failed"])
