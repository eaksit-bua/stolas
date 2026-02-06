"""Logic module: functional utilities and helpers."""

from stolas.logic.access import at, call, get
from stolas.logic.collection import (
    apply,
    chain,
    count,
    find,
    first,
    last,
    pair,
    sort,
    where,
)
from stolas.logic.common import const, fmt, identity, tap, tee
from stolas.logic.predicates import both, contains, either, negate
from stolas.logic.flow import check, strict
from stolas.logic.placeholder import _
from stolas.logic.utils import alt, compose, when, wrap

__all__ = [
    # Access
    "get",
    "at",
    "call",
    # Collection
    "chain",
    "where",
    "apply",
    "count",
    "first",
    "last",
    "pair",
    "find",
    "sort",
    # Flow
    "check",
    "strict",
    # Placeholder
    "_",
    # Utils
    "identity",
    "const",
    "tap",
    "tee",
    "fmt",
    "wrap",
    "when",
    "compose",
    "alt",
    # Predicates
    "contains",
    "negate",
    "both",
    "either",
]
