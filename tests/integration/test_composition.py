"""Integration tests: complex cross-type composition and end-to-end pipelines.

Covers Section 4 of the integration test plan:
- Pipeline simulation: fetch → validate → transform → result
- Error propagation through multi-step pipelines
- Cross-type flows (Option → Result, Effect chains, Validated accumulation)
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.logic import (
    alt,
    apply,
    both,
    call,
    check,
    compose,
    const,
    contains,
    either,
    find,
    first,
    fmt,
    negate,
    strict,
    when,
    where,
    wrap,
)
from stolas.logic.placeholder import _
from stolas.operand import as_effect, as_many, as_option, as_result, as_validated
from stolas.struct import struct, trait
from stolas.types.effect import Effect
from stolas.types.many import Many
from stolas.types.option import Nothing, Some, _Nothing
from stolas.types.result import Error, Ok
from stolas.types.validated import Invalid, Valid


# ── Test domain models ──────────────────────────────────────────────────────


@struct
class User:
    id: int
    name: str
    email: str
    age: int


@struct
class Product:
    id: int
    name: str
    price: float
    in_stock: bool


USERS_DB: dict[int, User] = {
    1: User(id=1, name="Alice", email="alice@example.com", age=30),
    2: User(id=2, name="Bob", email="bob_no_email", age=17),
    3: User(id=3, name="Charlie", email="charlie@example.com", age=25),
    4: User(id=4, name="Diana", email="diana@example.com", age=15),
}

PRODUCTS_DB: dict[int, Product] = {
    1: Product(id=1, name="Laptop", price=999.99, in_stock=True),
    2: Product(id=2, name="Mouse", price=29.99, in_stock=True),
    3: Product(id=3, name="Keyboard", price=0.0, in_stock=False),
}


# ── Pipeline simulation tests ───────────────────────────────────────────────


class TestFetchValidateTransformPipeline:
    """Simulate: fetch_user → validate → option.map → result."""

    def _fetch_user(self, user_id: int) -> Some[User] | type[Nothing]:
        user = USERS_DB.get(user_id)
        if user is None:
            return Nothing
        return Some(user)

    def test_full_happy_path(self) -> None:
        """fetch → validate email → validate age → transform name."""
        user_opt = self._fetch_user(1)
        if user_opt.is_nothing():
            result = Nothing
        else:
            result = (
                Ok(user_opt.unwrap())
                >> check(compose(_.email, contains("@")), "Invalid email")
                >> check(_.age >= 18, "Must be adult")
                >> _.name.upper()
            )
        assert isinstance(result, Ok)
        assert result.value == "ALICE"

    def test_user_not_found_stops_pipeline(self) -> None:
        """Nothing propagates through the entire pipeline."""
        result = (
            self._fetch_user(999)
            >> check(compose(_.email, contains("@")), "Invalid email")
            >> check(_.age >= 18, "Must be adult")
            >> _.name.upper()
        )
        assert result is Nothing

    def test_first_validation_fails(self) -> None:
        """Bob has no @ in email → Error at first check."""
        user_opt = self._fetch_user(2)
        result = (
            Ok(user_opt.unwrap())
            >> check(compose(_.email, contains("@")), "Invalid email")
            >> check(_.age >= 18, "Must be adult")
        )
        assert isinstance(result, Error)
        assert result.error == "Invalid email"

    def test_second_validation_fails(self) -> None:
        """Diana has valid email but is underage → Error at second check."""
        user_opt = self._fetch_user(4)
        result = (
            Ok(user_opt.unwrap())
            >> check(compose(_.email, contains("@")), "Invalid email")
            >> check(_.age >= 18, "Must be adult")
        )
        assert isinstance(result, Error)
        assert result.error == "Must be adult"

    def test_error_stops_further_transforms(self) -> None:
        """Once Error, subsequent >> are no-ops."""
        call_count = 0

        def tracked_transform(u: User) -> str:
            nonlocal call_count
            call_count += 1
            return u.name

        user_opt = self._fetch_user(2)
        (
            Ok(user_opt.unwrap())
            >> check(compose(_.email, contains("@")), "Invalid email")
            >> tracked_transform
        )
        # tracked_transform not called because Error short-circuits
        assert call_count == 0


class TestOptionToResultBridge:
    """Option values flowing into Result-producing functions."""

    def test_some_unwrap_into_check(self) -> None:
        opt = Some(42)
        result = Ok(opt.unwrap()) >> check(_ > 0, "must be positive")
        assert isinstance(result, Ok)
        assert result.value == 42

    def test_some_unwrap_into_strict(self) -> None:
        opt = Some("hello")
        result = Ok(opt.unwrap()) >> strict(str)
        assert isinstance(result, Ok)
        assert result.value == "hello"

    def test_some_fails_strict(self) -> None:
        opt = Some("hello")
        result = Ok(opt.unwrap()) >> strict(int)
        assert isinstance(result, Error)

    def test_nothing_returns_nothing(self) -> None:
        result = Nothing >> check(_ > 0, "must be positive")
        assert result is Nothing

    def test_nothing_skips_strict(self) -> None:
        result = Nothing >> strict(int)
        assert result is Nothing

    def test_option_to_result_chain(self) -> None:
        result = (
            Ok(25)
            >> check(_ > 0, "must be positive")
            >> check(_ < 100, "must be under 100")
            >> (_ * 2)
        )
        assert isinstance(result, Ok)
        assert result.value == 50

    def test_alt_unwrap_with_default(self) -> None:
        assert alt(0)(Some(10)) == 10
        assert alt(0)(Nothing) == 0


# ── Error propagation tests ─────────────────────────────────────────────────


class TestErrorPropagation:
    """Verify errors bubble up correctly through multi-step pipelines."""

    def test_result_error_stops_all_transforms(self) -> None:
        result = Ok(10) >> check(_ > 100, "too small") >> (_ * 2) >> (_ + 1)
        assert isinstance(result, Error)
        assert result.error == "too small"

    def test_result_chain_first_error_wins(self) -> None:
        result = (
            Ok(-5)
            >> check(_ > 0, "must be positive")
            >> check(_ < 100, "must be under 100")
            >> check(_ % 2 == 0, "must be even")
        )
        assert isinstance(result, Error)
        assert result.error == "must be positive"

    def test_ok_flows_through_all_checks(self) -> None:
        result = (
            Ok(42)
            >> check(_ > 0, "must be positive")
            >> check(_ < 100, "must be under 100")
            >> check(_ % 2 == 0, "must be even")
        )
        assert isinstance(result, Ok)
        assert result.value == 42

    def test_map_err_transforms_error(self) -> None:
        result = Ok(-1) >> check(_ > 0, "negative")
        assert isinstance(result, Error)
        mapped = result.map_err(fmt("Validation failed: {}"))
        assert mapped.error == "Validation failed: negative"


# ── Effect composition tests ────────────────────────────────────────────────


class TestEffectComposition:
    """Effect chains remain lazy until .run()."""

    def test_effect_map_chain(self) -> None:
        effect = Effect.pure(10) >> (_ + 5) >> (_ * 2)
        assert effect.run() == 30

    def test_effect_deferred_side_effects(self) -> None:
        """Side-effect lambdas must stay — they capture mutable state."""
        log: list[str] = []

        e1 = Effect.defer(lambda: log.append("step1") or 10)
        e2 = e1 >> (lambda x: (log.append("step2"), x * 2)[1])

        assert log == []  # nothing executed yet
        result = e2.run()
        assert result == 20
        assert log == ["step1", "step2"]

    def test_effect_bind_chain(self) -> None:
        effect = (
            Effect.pure(5)
            .bind(compose(_ + 10, Effect.pure))
            .bind(compose(_ * 3, Effect.pure))
        )
        assert effect.run() == 45

    def test_effect_re_run_produces_fresh_result(self) -> None:
        counter = [0]

        def increment() -> int:
            counter[0] += 1
            return counter[0]

        effect = Effect(increment)
        assert effect.run() == 1
        assert effect.run() == 2

    def test_as_effect_decorator(self) -> None:
        @as_effect
        def compute(x: int, y: int) -> int:
            return x + y

        effect = compute(3, 4)
        assert isinstance(effect, Effect)
        assert effect.run() == 7


# ── Validated accumulation tests ────────────────────────────────────────────


class TestValidatedAccumulation:
    """Validated collects all errors instead of short-circuiting."""

    def _validate_name(self, name: str) -> Valid[str] | Invalid[str]:
        if len(name) >= 2:
            return Valid(name)
        return Invalid("Name too short")

    def _validate_email(self, email: str) -> Valid[str] | Invalid[str]:
        if "@" in email:
            return Valid(email)
        return Invalid("Missing @")

    def _validate_age(self, age: int) -> Valid[int] | Invalid[str]:
        if age >= 18:
            return Valid(age)
        return Invalid("Must be 18+")

    def test_all_valid_combines(self) -> None:
        result = (
            self._validate_name("Alice")
            .combine(self._validate_email("alice@test.com"))
            .combine(self._validate_age(30))
        )
        assert isinstance(result, Valid)

    def test_single_invalid(self) -> None:
        result = (
            self._validate_name("Alice")
            .combine(self._validate_email("no_at"))
            .combine(self._validate_age(30))
        )
        assert isinstance(result, Invalid)
        assert "Missing @" in result.errors

    def test_multiple_errors_accumulated(self) -> None:
        result = (
            self._validate_name("A")
            .combine(self._validate_email("bad"))
            .combine(self._validate_age(15))
        )
        assert isinstance(result, Invalid)
        assert len(result.errors) == 3
        assert "Name too short" in result.errors
        assert "Missing @" in result.errors
        assert "Must be 18+" in result.errors

    def test_valid_pipeline_transform(self) -> None:
        result = Valid("hello") >> call("upper")
        assert isinstance(result, Valid)
        assert result.value == "HELLO"

    def test_invalid_pipeline_stops(self) -> None:
        result = Invalid("error") >> call("upper")
        assert isinstance(result, Invalid)
        assert result.errors == ("error",)

    def test_as_validated_decorator(self) -> None:
        @as_validated
        def parse_int(s: str) -> int:
            return int(s)

        assert isinstance(parse_int("42"), Valid)
        assert parse_int("42").value == 42
        assert isinstance(parse_int("abc"), Invalid)


# ── Many → Option/Result cross-type tests ───────────────────────────────────


class TestManyToOptionResult:
    """Many pipelines that terminate with Option or Result values."""

    def test_many_find_returns_option(self) -> None:
        users = Many(list(USERS_DB.values()))
        result = find(_.name == "Charlie")(users)
        assert isinstance(result, Some)
        assert result.value.email == "charlie@example.com"

    def test_many_find_not_found(self) -> None:
        users = Many(list(USERS_DB.values()))
        result = find(_.name == "Nobody")(users)
        assert result is Nothing

    def test_many_first_returns_option(self) -> None:
        result = Many([10, 20, 30]) >> first()
        assert isinstance(result, Some)
        assert result.value == 10

    def test_many_first_empty_returns_nothing(self) -> None:
        result = Many([]) >> first()
        assert result is Nothing

    def test_many_filter_then_find(self) -> None:
        users = Many(list(USERS_DB.values()))
        result = users >> where(_.age >= 18)
        found = find(_.name == "Alice")(result)
        assert isinstance(found, Some)

    def test_many_filter_then_check_first(self) -> None:
        """Many → filter → first → unwrap → check → Result."""
        users = Many(list(USERS_DB.values()))
        first_user = users >> where(_.age >= 18) >> first()
        assert isinstance(first_user, Some)
        result = Ok(first_user.unwrap()) >> check(
            compose(_.email, contains("@")), "Invalid email"
        )
        assert isinstance(result, Ok)


# ── Safe wrapper integration tests ──────────────────────────────────────────


class TestSafeWrapperIntegration:
    """as_result, as_option, as_many work in pipelines."""

    def test_as_result_success_in_pipeline(self) -> None:
        @as_result
        def divide(a: int, b: int) -> float:
            return a / b

        result = divide(10, 2)
        assert isinstance(result, Ok)
        assert result.value == 5.0

    def test_as_result_failure_in_pipeline(self) -> None:
        @as_result
        def divide(a: int, b: int) -> float:
            return a / b

        result = divide(10, 0)
        assert isinstance(result, Error)
        assert isinstance(result.error, ZeroDivisionError)

    def test_as_result_then_map(self) -> None:
        @as_result
        def parse(s: str) -> int:
            return int(s)

        result = parse("42") >> (_ * 2)
        assert isinstance(result, Ok)
        assert result.value == 84

    def test_as_result_error_stops_map(self) -> None:
        @as_result
        def parse(s: str) -> int:
            return int(s)

        result = parse("abc") >> (_ * 2)
        assert isinstance(result, Error)

    def test_as_option_some(self) -> None:
        @as_option
        def find_user(name: str) -> User | None:
            for u in USERS_DB.values():
                if u.name == name:
                    return u
            return None

        result = find_user("Alice")
        assert isinstance(result, Some)
        assert result.value.age == 30

    def test_as_option_nothing(self) -> None:
        @as_option
        def find_user(name: str) -> User | None:
            for u in USERS_DB.values():
                if u.name == name:
                    return u
            return None

        result = find_user("Nobody")
        assert result is Nothing

    def test_as_many_in_pipeline(self) -> None:
        @as_many
        def get_users() -> list[User]:
            return list(USERS_DB.values())

        result = get_users() >> where(_.age >= 18) >> apply(_.name)
        assert isinstance(result, Many)
        assert "Alice" in result.items
        assert "Charlie" in result.items


# ── Predicate combinators in cross-type pipelines ───────────────────────────


class TestPredicateCombinatorsCrossType:
    """both/either/negate with check, find, when across types."""

    def test_check_with_both(self) -> None:
        validator = check(both(_ > 0, _ < 100), "out of range")
        assert isinstance(validator(50), Ok)
        assert isinstance(validator(-1), Error)
        assert isinstance(validator(200), Error)

    def test_check_with_either(self) -> None:
        validator = check(either(_ == 0, _ == 1), "must be 0 or 1")
        assert isinstance(validator(0), Ok)
        assert isinstance(validator(1), Ok)
        assert isinstance(validator(2), Error)

    def test_check_with_negate(self) -> None:
        validator = check(negate(_ == 0), "must not be zero")
        assert isinstance(validator(5), Ok)
        assert isinstance(validator(0), Error)

    def test_find_with_both(self) -> None:
        users = Many(list(USERS_DB.values()))
        result = find(both(_.age >= 18, compose(_.email, contains("@"))))(users)
        assert isinstance(result, Some)
        assert result.value.name == "Alice"

    def test_when_with_predicates(self) -> None:
        classify = when(
            both(_ > 0, _ < 100),
            const("normal"),
            const("extreme"),
        )
        assert classify(50) == "normal"
        assert classify(-10) == "extreme"
        assert classify(200) == "extreme"

    def test_ok_pipeline_with_predicates(self) -> None:
        """Ok → check(both) → check(negate) → transform."""
        result = (
            Ok(42)
            >> check(both(_ > 0, _ < 100), "out of range")
            >> check(negate(_ == 13), "unlucky number")
            >> (_ * 2)
        )
        assert isinstance(result, Ok)
        assert result.value == 84


# ── Complex end-to-end scenarios ────────────────────────────────────────────


class TestComplexEndToEnd:
    """Multi-step realistic business scenarios."""

    def test_user_registration_flow(self) -> None:
        """Validate user fields → create user → return result."""

        def register(name: str, email: str, age: int) -> Ok[str] | Error[str]:
            return (
                Ok({"name": name, "email": email, "age": age})
                >> check(compose(_["name"], call("__len__"), _ >= 2), "Name too short")
                >> check(compose(_["email"], contains("@")), "Invalid email")
                >> check(_["age"] >= 18, "Must be adult")
                >> compose(_["name"], fmt("Welcome, {}!"))
            )

        assert register("Alice", "alice@test.com", 30) == Ok("Welcome, Alice!")
        assert register("A", "a@b.com", 30) == Error("Name too short")
        assert register("Bob", "bob", 30) == Error("Invalid email")
        assert register("Eve", "eve@test.com", 15) == Error("Must be adult")

    def test_product_search_pipeline(self) -> None:
        """Filter products → find first in stock → apply discount."""
        products = Many(list(PRODUCTS_DB.values()))
        result = (
            products
            >> where(both(_.in_stock, _.price > 0))
            >> apply(compose(_.price, _ * 0.9, round))
        )
        assert 899.9999999999999 in result.items or 900.0 in result.items
        assert 26.991 in result.items or 27.0 in result.items

    def test_effect_then_result_flow(self) -> None:
        """Effect defers fetch → run → validate with Result."""
        fetch_effect = Effect.defer(USERS_DB.get, 1)
        user = fetch_effect.run()
        assert user is not None
        result = Ok(user) >> check(_.age >= 18, "Must be adult") >> _.name
        assert isinstance(result, Ok)
        assert result.value == "Alice"

    def test_validated_form_then_result_pipeline(self) -> None:
        """Validated accumulates errors, then transitions to Result on success."""
        name_v = Valid("Alice")
        email_v = Valid("alice@test.com")
        age_v = Valid(30)

        combined = name_v.combine(email_v).combine(age_v)
        assert isinstance(combined, Valid)

        result = Ok(combined.value) >> fmt("Registered: {}")
        assert isinstance(result, Ok)

    def test_many_to_option_to_result(self) -> None:
        """Many → find → Option → unwrap → check → Result."""
        users = Many(list(USERS_DB.values()))
        found = find(_.name == "Charlie")(users)
        assert isinstance(found, Some)

        result = Ok(found.unwrap()) >> check(_.age >= 18, "Must be adult")
        assert isinstance(result, Ok)
        assert result.value.name == "Charlie"

    def test_many_to_option_to_result_fails(self) -> None:
        """Many → find → Option → unwrap → check → Error."""
        users = Many(list(USERS_DB.values()))
        found = find(_.name == "Diana")(users)
        assert isinstance(found, Some)

        result = Ok(found.unwrap()) >> check(_.age >= 18, "Must be adult")
        assert isinstance(result, Error)
        assert result.error == "Must be adult"

    def test_compose_cross_type_functions(self) -> None:
        """compose chains functions across types."""
        pipeline = compose(_ * 2, _ + 10, fmt("Result: {}"))
        assert pipeline(5) == "Result: 20"

    def test_when_branches_to_different_types(self) -> None:
        """when() with Ok/Error branches."""
        validate = when(
            _ > 0,
            wrap(Ok),
            const(Error("must be positive")),
        )
        assert isinstance(validate(5), Ok)
        assert isinstance(validate(-3), Error)


# ── Trait dispatch with monadic types ────────────────────────────────────────


class TestTraitWithMonadicTypes:
    """@trait dispatch integrates with Result, Option, and pipeline >>."""

    def test_trait_dispatches_ok_and_error(self) -> None:
        @trait
        def format_result(x: object) -> str:
            raise NotImplementedError

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

    def test_trait_dispatches_some_and_nothing(self) -> None:
        @trait
        def describe(x: object) -> str:
            raise NotImplementedError

        @describe.impl(Some)
        def describe_some(x: Some[int]) -> str:
            return f"Value: {x.value}"

        @describe.impl(_Nothing)
        def describe_nothing(x: _Nothing) -> str:
            return "Empty"

        assert describe(Some(42)) == "Value: 42"
        assert describe(Nothing) == "Empty"

    def test_trait_dispatches_valid_and_invalid(self) -> None:
        @trait
        def show_validation(x: object) -> str:
            raise NotImplementedError

        @show_validation.impl(Valid)
        def show_valid(x: Valid[str]) -> str:
            return f"OK: {x.value}"

        @show_validation.impl(Invalid)
        def show_invalid(x: Invalid[str]) -> str:
            return f"Errors: {', '.join(x.errors)}"

        assert show_validation(Valid("data")) == "OK: data"
        assert show_validation(Invalid(["a", "b"])) == "Errors: a, b"

    def test_trait_in_pipeline_with_result(self) -> None:
        """Pipeline produces Result, trait formats it."""

        @trait
        def to_message(x: object) -> str:
            raise NotImplementedError

        @to_message.impl(Ok)
        def msg_ok(x: Ok[str]) -> str:
            return f"Success: {x.value}"

        @to_message.impl(Error)
        def msg_err(x: Error[str]) -> str:
            return f"Failed: {x.error}"

        result = (
            Ok({"name": "Alice", "age": 30})
            >> check(_["age"] >= 18, "Too young")
            >> _["name"]
        )
        assert to_message(result) == "Success: Alice"

        result_fail = (
            Ok({"name": "Bob", "age": 15})
            >> check(_["age"] >= 18, "Too young")
            >> _["name"]
        )
        assert to_message(result_fail) == "Failed: Too young"

    def test_trait_with_many_pipeline_output(self) -> None:
        """Trait dispatches on Option from Many >> find."""

        @trait
        def user_label(x: object) -> str:
            raise NotImplementedError

        @user_label.impl(Some)
        def label_some(x: Some[User]) -> str:
            return f"Found: {x.value.name}"

        @user_label.impl(_Nothing)
        def label_nothing(x: _Nothing) -> str:
            return "Not found"

        users = Many(list(USERS_DB.values()))
        found = find(_.name == "Alice")(users)
        assert user_label(found) == "Found: Alice"

        missing = find(_.name == "Nobody")(users)
        assert user_label(missing) == "Not found"

    def test_trait_require_and_check(self) -> None:
        @trait
        def process(x: object) -> str:
            raise NotImplementedError

        @process.impl(Ok)
        def process_ok(x: Ok[int]) -> str:
            return str(x.value)

        assert process.require(Ok(1)) is True
        assert process.require(Error("e")) is False

        process.check(Ok(1))  # should not raise

        with pytest.raises(TypeError, match="No implementation"):
            process.check(Error("e"))

    def test_trait_types_property(self) -> None:
        @trait
        def render(x: object) -> str:
            raise NotImplementedError

        @render.impl(Ok)
        def render_ok(x: Ok[int]) -> str:
            return "ok"

        @render.impl(Error)
        def render_err(x: Error[str]) -> str:
            return "err"

        assert Ok in render.types
        assert Error in render.types

    def test_trait_with_struct(self) -> None:
        @trait
        def describe_item(x: object) -> str:
            raise NotImplementedError

        @describe_item.impl(User)
        def describe_user(x: User) -> str:
            return f"User({x.name}, age={x.age})"

        @describe_item.impl(Product)
        def describe_product(x: Product) -> str:
            stock = "in stock" if x.in_stock else "out of stock"
            return f"Product({x.name}, ${x.price}, {stock})"

        assert (
            describe_item(User(id=1, name="A", email="a@b", age=20))
            == "User(A, age=20)"
        )
        assert (
            describe_item(Product(id=1, name="X", price=9.99, in_stock=True))
            == "Product(X, $9.99, in stock)"
        )


# ── fmt helper tests ────────────────────────────────────────────────────────


class TestFmtHelper:
    """fmt() replaces f-string lambdas in pipelines."""

    def test_basic_formatting(self) -> None:
        assert fmt("Hello, {}!")(("World")) == "Hello, World!"

    def test_in_result_pipeline(self) -> None:
        result = Ok("Alice") >> fmt("Welcome, {}!")
        assert isinstance(result, Ok)
        assert result.value == "Welcome, Alice!"

    def test_in_compose(self) -> None:
        pipeline = compose(_ * 2, fmt("Result: {}"))
        assert pipeline(5) == "Result: 10"

    def test_with_attribute_via_compose(self) -> None:
        user = User(id=1, name="Alice", email="a@b", age=30)
        label = compose(_.name, fmt("{}: adult"))
        assert label(user) == "Alice: adult"

    def test_in_many_pipeline(self) -> None:
        result = Many([1, 2, 3]) >> apply(fmt("item_{}"))
        assert result.items == ("item_1", "item_2", "item_3")

    def test_map_err_with_fmt(self) -> None:
        result = Ok(-1) >> check(_ > 0, "negative")
        assert isinstance(result, Error)
        mapped = result.map_err(fmt("Validation failed: {}"))
        assert mapped.error == "Validation failed: negative"
