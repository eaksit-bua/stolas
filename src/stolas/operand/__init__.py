"""Operand module: function decorators and composition."""

import asyncio

from stolas.operand.arity import binary, quaternary, ternary, unary
from stolas.operand.cases import cases
from stolas.operand.concurrent import concurrent
from stolas.operand.ops import ops
from stolas.operand.safe import as_effect, as_many, as_option, as_result, as_validated

__all__ = [
    # Arity
    "unary",
    "binary",
    "ternary",
    "quaternary",
    # Cases
    "cases",
    # Concurrent
    "concurrent",
    "asyncio",  # Re-export for convenience
    # Ops
    "ops",
    # Safe
    "as_result",
    "as_option",
    "as_validated",
    "as_many",
    "as_effect",
]
