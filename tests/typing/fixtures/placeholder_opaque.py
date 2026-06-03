"""Fixture: the `_` placeholder is intentionally OPAQUE (north star).

Milestone 5 tightens types only where the runtime is single-valued; the
stolas.logic `_` placeholder is left opaque. Attribute access and comparison
both produce PlaceholderExpression[Any, ...] -- the payload stays Any rather
than being narrowed. This fixture pins that the placeholder was NOT over-typed.
"""

from stolas.logic import _

reveal_type(_.name)
