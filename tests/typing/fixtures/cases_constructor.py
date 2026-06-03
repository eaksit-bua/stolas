"""Fixture: @cases value-variant constructor is callable and reveals Any.

The plugin retypes @cases-annotated attributes to Any so `Format.Digital("dvd")`
type-checks as a call. The runtime distinguishes alias/value/unit variants, so the
constructor result is deliberately left Any (opaque) rather than over-promised.
"""

from stolas.operand.cases import cases


@cases
class Format:
    Digital: str
    Print: int


reveal_type(Format.Digital("dvd"))
