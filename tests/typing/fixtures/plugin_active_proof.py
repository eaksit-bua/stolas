"""Fixture: code that type-checks clean ONLY when the stolas plugin is ACTIVE.

This is the registration proof. With the plugin OFF (mypy_path but no
`plugins=`), `instance >> f` is `[operator]` ("Unsupported left operand type for
>>") and `.replace(...)` is `[attr-defined]` ("Point" has no attribute
"replace"), and `Format.Digital(...)` is `[operator]` ("str" not callable). With
the plugin ON, all three are clean. No reveal_type here -- the harness asserts
"Success: no issues found" with the plugin and the matching errors without it.
"""

from stolas.operand.cases import cases
from stolas.struct import struct


@struct
class Point:
    x: int
    y: int


def to_str(p: Point) -> str:
    return f"{p.x},{p.y}"


@cases
class Format:
    Digital: str


point = Point(x=1, y=2)
piped = point >> to_str
copied = point.replace(x=5)
variant = Format.Digital("dvd")
