"""Mypy plugin for stolas.

This module provides mypy integration for stolas. The actual type checking
is primarily handled through stub files (.pyi) and PEP 681 dataclass_transform.

This plugin provides additional support where stub files are insufficient,
particularly for @cases which transforms class annotations into variant constructors.
"""

from typing import Callable, Type as TypingType

from mypy.plugin import ClassDefContext, Plugin
from mypy.plugins.common import add_attribute_to_class
from mypy.types import AnyType, TypeOfAny


CASES_DECORATOR = "stolas.operand.cases.cases"
CASES_DECORATOR_SHORT = "stolas.operand.cases"


def _cases_class_callback(ctx: ClassDefContext) -> None:
    """Transform @cases class annotations into Any-typed attributes.

    @cases transforms annotations like `Digital: str` into callable variant
    constructors. Since the actual type is dynamically created, we use Any.
    """
    cls = ctx.cls

    for name, node in list(cls.info.names.items()):
        if name.startswith("_"):
            continue
        if node.node is None:
            continue
        # Replace the type annotation with Any to allow calling
        add_attribute_to_class(
            ctx.api,
            cls,
            name,
            AnyType(TypeOfAny.special_form),
            override_allow_incompatible=True,
        )


class StolasPlugin(Plugin):
    """Mypy plugin for stolas.

    Handles:
    - @cases: Transforms class annotations into callable variant constructors
    """

    def get_class_decorator_hook(
        self, fullname: str
    ) -> Callable[[ClassDefContext], None] | None:
        """Hook for class decorators."""
        if fullname in (CASES_DECORATOR, CASES_DECORATOR_SHORT, "stolas.operand.cases"):
            return _cases_class_callback
        return None


def plugin(version: str) -> TypingType[Plugin]:
    """Entry point for mypy plugin system."""
    return StolasPlugin
