"""Fixture: @struct instance >> f reveals f(instance); .replace() reveals Self.

Consumed by tests/typing/test_typing_fixtures.py via a mypy subprocess. The
`reveal_type` lines below are matched against mypy's "Revealed type is ..." notes.
This file type-checks clean (no errors) ONLY when the stolas mypy plugin is active.
"""

from stolas.struct import struct


@struct
class Point:
    x: int
    y: int


def to_str(p: Point) -> str:
    return f"{p.x},{p.y}"


point = Point(x=1, y=2)

reveal_type(point >> to_str)
reveal_type(point.replace(x=5))
