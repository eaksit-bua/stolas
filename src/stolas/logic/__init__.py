"""Logic module: functional utilities and helpers."""

from stolas.logic.access import at, call, get
from stolas.logic.collection import (
    apply,
    chain,
    combine_all,
    count,
    find,
    first,
    last,
    pair,
    partition,
    sequence,
    sort,
    traverse,
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
    "sequence",
    "traverse",
    "partition",
    "combine_all",
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
