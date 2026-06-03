"""Fixture: errors mypy MUST report even WITH the plugin (not blanket-Any).

Proves the plugin tightens rather than loosens: a Point piped into a str-only
function, a .replace() result assigned to the wrong type, an unexpected ctor
keyword, and a wrong-typed field all error. Each `# error: [<code>]` comment
marks the expected error code on that line for the harness.
"""

from stolas.struct import struct


@struct
class Point:
    x: int
    y: int


def needs_str(s: str) -> str:
    return s


point = Point(x=1, y=2)

bad_pipe = point >> needs_str  # error: [operator]
wrong_replace: str = point.replace(x=3)  # error: [assignment]
extra_kwarg = Point(x=1, y=2, z=3)  # error: [call-arg]
wrong_field = Point(x="no", y=2)  # error: [arg-type]
