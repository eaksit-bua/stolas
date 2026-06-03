"""Unit tests for the stolas.control module."""

import asyncio
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.control import (
    RetryPolicy,
    bracket,
    bracket_async,
    retry,
    retry_async,
    timeout,
)
from stolas.types import AsyncEffect, Effect
from stolas.types.result import Error, Ok


class TestBracketSuccess:
    """bracket acquires, uses, and releases a resource on success."""

    def test_returns_use_result(self) -> None:
        assert bracket(lambda: 10, lambda r: r + 1, lambda r: None) == 11

    def test_release_runs_after_use(self) -> None:
        events: list[str] = []
        bracket(
            lambda: events.append("acquire") or "res",
            lambda r: events.append("use"),
            lambda r: events.append("release"),
        )
        assert events == ["acquire", "use", "release"]

    def test_release_receives_acquired_resource(self) -> None:
        released: list[str] = []
        bracket(lambda: "handle", lambda r: r, lambda r: released.append(r))
        assert released == ["handle"]


class TestBracketFailure:
    """bracket releases the resource even when use raises."""

    def test_release_runs_when_use_raises(self) -> None:
        released: list[str] = []

        def use(_: str) -> int:
            raise ValueError("kaboom")

        with pytest.raises(ValueError):
            bracket(lambda: "res", use, lambda r: released.append(r))
        assert released == ["res"]

    def test_use_exception_propagates(self) -> None:
        def use(_: str) -> int:
            raise RuntimeError("nope")

        with pytest.raises(RuntimeError, match="nope"):
            bracket(lambda: "res", use, lambda r: None)


class TestBracketAsyncSuccess:
    """bracket_async awaits acquire/use/release on success."""

    def test_returns_use_result(self) -> None:
        async def acquire() -> int:
            return 2

        async def use(r: int) -> int:
            return r * 5

        async def release(r: int) -> None:
            return None

        assert asyncio.run(bracket_async(acquire, use, release)) == 10

    def test_release_runs_after_use(self) -> None:
        events: list[str] = []

        async def acquire() -> str:
            events.append("acquire")
            return "res"

        async def use(r: str) -> None:
            events.append("use")

        async def release(r: str) -> None:
            events.append("release")

        asyncio.run(bracket_async(acquire, use, release))
        assert events == ["acquire", "use", "release"]


class TestBracketAsyncFailure:
    """bracket_async awaits release even when use raises."""

    def test_release_runs_when_use_raises(self) -> None:
        released: list[str] = []

        async def acquire() -> str:
            return "res"

        async def use(r: str) -> None:
            raise ValueError("boom")

        async def release(r: str) -> None:
            released.append(r)

        with pytest.raises(ValueError):
            asyncio.run(bracket_async(acquire, use, release))
        assert released == ["res"]


class TestRetryPolicyConstruction:
    """RetryPolicy validates and stores its configuration."""

    def test_defaults(self) -> None:
        policy = RetryPolicy(3)
        assert (
            policy.attempts,
            policy.delay,
            policy.backoff,
            policy.retry_on_error,
        ) == (
            3,
            0.0,
            1.0,
            False,
        )

    def test_custom_values(self) -> None:
        policy = RetryPolicy(5, delay=0.5, backoff=2.0, retry_on_error=True)
        assert (
            policy.attempts,
            policy.delay,
            policy.backoff,
            policy.retry_on_error,
        ) == (
            5,
            0.5,
            2.0,
            True,
        )

    def test_zero_attempts_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="attempts must be >= 1"):
            RetryPolicy(0)


class TestRetryPolicyImmutability:
    """RetryPolicy is immutable and introspectable."""

    def test_setattr_raises(self) -> None:
        policy = RetryPolicy(1)
        with pytest.raises(AttributeError, match="RetryPolicy is immutable"):
            policy.attempts = 9  # type: ignore[misc]

    def test_delattr_raises(self) -> None:
        policy = RetryPolicy(1)
        with pytest.raises(AttributeError, match="RetryPolicy is immutable"):
            del policy._attempts

    def test_repr(self) -> None:
        assert repr(RetryPolicy(2, delay=0.1, backoff=3.0, retry_on_error=True)) == (
            "RetryPolicy(attempts=2, delay=0.1, backoff=3.0, retry_on_error=True)"
        )


class TestRetryPolicyEquality:
    """RetryPolicy equality and hashing compare all fields."""

    def test_equal_policies(self) -> None:
        assert RetryPolicy(2, delay=0.1) == RetryPolicy(2, delay=0.1)

    def test_unequal_policies(self) -> None:
        assert RetryPolicy(2) != RetryPolicy(3)

    def test_eq_with_non_policy(self) -> None:
        assert RetryPolicy(1) != 7

    def test_equal_policies_hash_equal(self) -> None:
        assert hash(RetryPolicy(2, delay=0.1)) == hash(RetryPolicy(2, delay=0.1))


class TestRetrySuccess:
    """retry returns the first successful value."""

    def test_succeeds_first_attempt(self) -> None:
        tries = {"n": 0}

        def thunk() -> int:
            tries["n"] += 1
            return 42

        assert retry(RetryPolicy(3), Effect(thunk)).run() == 42
        assert tries["n"] == 1

    def test_succeeds_after_failures(self) -> None:
        tries = {"n": 0}

        def thunk() -> int:
            tries["n"] += 1
            if tries["n"] < 3:
                raise ValueError("retry me")
            return 99

        assert retry(RetryPolicy(3), Effect(thunk)).run() == 99
        assert tries["n"] == 3


class TestRetryExhaustion:
    """retry re-raises the last exception after exhausting attempts."""

    def test_exhausts_and_reraises(self) -> None:
        tries = {"n": 0}
        last = RuntimeError("final")

        def thunk() -> int:
            tries["n"] += 1
            raise last if tries["n"] == 2 else ValueError("early")

        with pytest.raises(RuntimeError, match="final"):
            retry(RetryPolicy(2), Effect(thunk)).run()
        assert tries["n"] == 2


class TestRetryDelayAndBackoff:
    """retry applies the configured delay growing by the backoff multiplier."""

    def test_applies_delay_and_backoff(self) -> None:
        sleeps: list[float] = []
        import stolas.control as control

        original = control.time.sleep
        control.time.sleep = lambda s: sleeps.append(s)  # type: ignore[assignment]
        try:

            def thunk() -> int:
                raise ValueError("always")

            with pytest.raises(ValueError):
                retry(RetryPolicy(3, delay=1.0, backoff=2.0), Effect(thunk)).run()
        finally:
            control.time.sleep = original  # type: ignore[assignment]
        assert sleeps == [1.0, 2.0]


class TestRetryOnError:
    """retry treats Error values as failures only when retry_on_error is True."""

    def test_default_does_not_retry_error_value(self) -> None:
        tries = {"n": 0}

        def thunk() -> Error[str]:
            tries["n"] += 1
            return Error("bad")

        result = retry(RetryPolicy(3), Effect(thunk)).run()
        assert result == Error("bad")
        assert tries["n"] == 1

    def test_retries_error_value_when_enabled(self) -> None:
        tries = {"n": 0}

        def thunk() -> Ok[int] | Error[str]:
            tries["n"] += 1
            if tries["n"] < 2:
                return Error("bad")
            return Ok(7)

        result = retry(RetryPolicy(3, retry_on_error=True), Effect(thunk)).run()
        assert result == Ok(7)
        assert tries["n"] == 2

    def test_exhausts_returning_last_error_value(self) -> None:
        tries = {"n": 0}

        def thunk() -> Error[str]:
            tries["n"] += 1
            return Error(f"bad-{tries['n']}")

        result = retry(RetryPolicy(2, retry_on_error=True), Effect(thunk)).run()
        assert result == Error("bad-2")
        assert tries["n"] == 2


class TestRetryBaseExceptionPropagates:
    """retry never catches BaseException."""

    def test_keyboard_interrupt_propagates(self) -> None:
        tries = {"n": 0}

        def thunk() -> int:
            tries["n"] += 1
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            retry(RetryPolicy(3), Effect(thunk)).run()
        assert tries["n"] == 1  # propagates immediately; never caught or retried


class TestRetryAsyncSuccess:
    """retry_async returns the first successful value."""

    def test_succeeds_first_attempt(self) -> None:
        tries = {"n": 0}

        async def factory() -> int:
            tries["n"] += 1
            return 42

        assert (
            asyncio.run(retry_async(RetryPolicy(3), AsyncEffect(factory)).run()) == 42
        )
        assert tries["n"] == 1

    def test_succeeds_after_failures(self) -> None:
        tries = {"n": 0}

        async def factory() -> int:
            tries["n"] += 1
            if tries["n"] < 3:
                raise ValueError("retry me")
            return 99

        result = asyncio.run(retry_async(RetryPolicy(3), AsyncEffect(factory)).run())
        assert result == 99
        assert tries["n"] == 3


class TestRetryAsyncExhaustion:
    """retry_async re-raises the last exception after exhausting attempts."""

    def test_exhausts_and_reraises(self) -> None:
        async def factory() -> int:
            raise RuntimeError("final")

        with pytest.raises(RuntimeError, match="final"):
            asyncio.run(retry_async(RetryPolicy(2), AsyncEffect(factory)).run())


class TestRetryAsyncDelayAndBackoff:
    """retry_async applies asyncio.sleep delays growing by the backoff multiplier."""

    def test_applies_delay_and_backoff(self) -> None:
        sleeps: list[float] = []
        import stolas.control as control

        async def fake_sleep(s: float) -> None:
            sleeps.append(s)

        original = control.asyncio.sleep
        control.asyncio.sleep = fake_sleep  # type: ignore[assignment]
        try:

            async def factory() -> int:
                raise ValueError("always")

            with pytest.raises(ValueError):
                asyncio.run(
                    retry_async(
                        RetryPolicy(3, delay=1.0, backoff=2.0), AsyncEffect(factory)
                    ).run()
                )
        finally:
            control.asyncio.sleep = original  # type: ignore[assignment]
        assert sleeps == [1.0, 2.0]


class TestRetryAsyncOnError:
    """retry_async treats Error values as failures only when enabled."""

    def test_default_does_not_retry_error_value(self) -> None:
        tries = {"n": 0}

        async def factory() -> Error[str]:
            tries["n"] += 1
            return Error("bad")

        result = asyncio.run(retry_async(RetryPolicy(3), AsyncEffect(factory)).run())
        assert result == Error("bad")
        assert tries["n"] == 1

    def test_retries_error_value_when_enabled(self) -> None:
        tries = {"n": 0}

        async def factory() -> Ok[int] | Error[str]:
            tries["n"] += 1
            if tries["n"] < 2:
                return Error("bad")
            return Ok(7)

        result = asyncio.run(
            retry_async(RetryPolicy(3, retry_on_error=True), AsyncEffect(factory)).run()
        )
        assert result == Ok(7)
        assert tries["n"] == 2

    def test_exhausts_returning_last_error_value(self) -> None:
        tries = {"n": 0}

        async def factory() -> Error[str]:
            tries["n"] += 1
            return Error(f"bad-{tries['n']}")

        result = asyncio.run(
            retry_async(RetryPolicy(2, retry_on_error=True), AsyncEffect(factory)).run()
        )
        assert result == Error("bad-2")
        assert tries["n"] == 2


class TestRetryAsyncCancelledPropagates:
    """retry_async never catches asyncio.CancelledError."""

    def test_cancelled_error_propagates(self) -> None:
        tries = {"n": 0}

        async def factory() -> int:
            tries["n"] += 1
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            asyncio.run(retry_async(RetryPolicy(3), AsyncEffect(factory)).run())
        assert tries["n"] == 1  # propagates immediately; never caught or retried


class TestTimeoutFast:
    """timeout passes through a value when the effect finishes in time."""

    def test_returns_value_when_fast(self) -> None:
        assert asyncio.run(timeout(1.0, AsyncEffect.pure(33)).run()) == 33


class TestTimeoutExceeded:
    """timeout raises TimeoutError when the effect runs too long."""

    def test_raises_timeout_error(self) -> None:
        async def slow() -> int:
            await asyncio.sleep(1.0)
            return 1

        with pytest.raises(TimeoutError):
            asyncio.run(timeout(0.01, AsyncEffect(slow)).run())
