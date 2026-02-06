"""Concurrent helper: parallel execution in functional pipelines."""

import asyncio
from typing import Awaitable, Callable, TypeVar

from stolas.types.effect import Effect

T = TypeVar("T")
U = TypeVar("U")


def concurrent(
    *funcs: Callable[[T], Awaitable[U]],
) -> Callable[[T], Effect[Awaitable[tuple[U, ...]]]]:
    """Run multiple async functions in parallel on the same input.

    Returns a function that takes input x, runs all funcs on x in parallel,
    and returns an Effect containing the tuple of results.

    Usage:
        Ok(val) >> concurrent(async_f1, async_f2)
        # Result is Ok(Effect(...)), user must unwrap/run it
    """

    def wrapper(x: T) -> Effect[Awaitable[tuple[U, ...]]]:
        async def run_parallel() -> tuple[U, ...]:
            return tuple(await asyncio.gather(*(f(x) for f in funcs)))

        return Effect(run_parallel)

    return wrapper
