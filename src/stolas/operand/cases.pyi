"""Type stubs for @cases decorator.

@cases transforms class annotations into callable variant constructors.
Example:
    @cases
    class Format:
        Digital: str       # becomes Format.Digital(value: str) -> Format.Digital
        Print: int         # becomes Format.Print(value: int) -> Format.Print
        Empty: None        # becomes Format.Empty singleton

After decoration, attribute access returns variant types that are callable.
"""

from typing import Any

# @cases transforms type annotations into variant classes/constructors
# The decorated class has dynamic attributes that are variant types
# Using Any return to allow dynamic variant access (Format.Digital, Format.Print, etc.)
def cases(cls: type) -> Any: ...
