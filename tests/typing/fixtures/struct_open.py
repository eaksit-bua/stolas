"""Fixture: @struct(open=True) keeps the plugin firing and stays kw-only/frozen.

Consumed by tests/typing/test_typing_fixtures.py via a mypy subprocess. The
call-form decorator must resolve to the same callee the plugin matches, so
``>>`` reveals the target function's return type and ``.replace()`` reveals the
struct type. Positional construction is still rejected (kw-only): mypy reports
"Too many positional arguments" [misc].
This file type-checks clean ONLY when the stolas mypy plugin is active.
"""

from stolas.struct import struct


@struct(open=True)
class Open:
    x: int
    y: int


def to_str(o: Open) -> str:
    return f"{o.x},{o.y}"


inst = Open(x=1, y=2)

reveal_type(inst >> to_str)
reveal_type(inst.replace(x=5))

positional = Open(1, 2)  # error: [misc] Too many positional arguments
