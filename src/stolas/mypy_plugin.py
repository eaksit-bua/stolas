"""Mypy plugin for stolas.

This module provides mypy integration for stolas. The actual type checking
is primarily handled through stub files (.pyi) and PEP 681 dataclass_transform.

This plugin provides additional support where stub files are insufficient:

- ``@cases`` (``stolas.operand.cases.cases``) transforms class annotations into
  callable variant constructors; the annotated attributes are retyped to ``Any``
  so they may be *called* (e.g. ``Format.Digital("x")``).
- ``@struct`` (``stolas.struct.struct.struct``) is modelled statically via
  ``dataclass_transform`` in ``struct.pyi``, so its synthesized class has no
  place to declare the runtime-only ``>>`` pipeline operator or the
  ``.replace()`` copy-with-changes method. This plugin injects both onto every
  ``@struct``-decorated class with precise, single-valued signatures:

    * ``instance >> func`` type-checks as ``func(instance)`` -- the operator's
      return type is the return type of ``func``.
    * ``instance.replace(**changes)`` returns ``Self`` (a re-validated copy).

The plugin is referenced from ``[tool.mypy]`` in ``pyproject.toml`` by file
path (stolas is not installed in the venv), and the project gate
``mypy src/stolas --strict`` must stay green with it active.
"""

from typing import Callable, Type as TypingType

from mypy.nodes import ARG_POS, ARG_STAR2, Argument, Var
from mypy.plugin import ClassDefContext, Plugin
from mypy.plugins import dataclasses as _dataclasses_plugin
from mypy.plugins.common import add_attribute_to_class, add_method_to_class
from mypy.typevars import fill_typevars
from mypy.types import (
    AnyType,
    CallableType,
    Type,
    TypeOfAny,
    TypeVarId,
    TypeVarType,
)


CASES_DECORATOR = "stolas.operand.cases.cases"
CASES_DECORATOR_SHORT = "stolas.operand.cases"
STRUCT_DECORATOR = "stolas.struct.struct.struct"
STRUCT_DECORATOR_SHORT = "stolas.struct.struct"


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


def _struct_tag_callback(ctx: ClassDefContext) -> None:
    """Main-pass tagging for @struct so dataclass base-class detection works.

    ``@struct`` is itself decorated with ``dataclass_transform`` (struct.pyi).
    Registering our own decorator hook would normally *suppress* mypy's built-in
    dataclass handling (mypy only falls back to the dataclasses plugin when no
    hook is registered), so we forward to it explicitly to keep the synthesized
    ``__init__`` / fields / ``__eq__`` intact.
    """
    _dataclasses_plugin.dataclass_tag_callback(ctx)


def _struct_class_callback(ctx: ClassDefContext) -> bool:
    """Synthesize the dataclass, then inject ``>>`` and ``.replace()``.

    ``dataclass_transform`` (struct.pyi) provides the synthesized ``__init__``,
    fields, ``__eq__`` and friends -- run via the forwarded dataclasses maker
    callback -- but it cannot express the runtime-only pipeline operator or the
    copy-with-changes method, so they are added on top.

    Runs from ``get_class_decorator_hook_2`` (placeholders resolved); both
    additions go through ``add_method_to_class``, which is idempotent.
    """
    # Forward to mypy's dataclass maker (it would otherwise be skipped because a
    # decorator hook is registered for @struct -- see semanal_main.apply_hooks).
    ok = _dataclasses_plugin.dataclass_class_maker_callback(ctx)

    api = ctx.api
    cls = ctx.cls
    info = cls.info
    self_type = fill_typevars(info)

    # instance >> func  ==>  func(instance) : R
    #   __rshift__(self, func: Callable[[Self], R]) -> R
    rshift_tvar = TypeVarType(
        "R",
        f"{info.fullname}.__rshift__.R",
        id=TypeVarId(-1, namespace=f"{info.fullname}.__rshift__"),
        values=[],
        upper_bound=api.named_type("builtins.object"),
        default=AnyType(TypeOfAny.from_omitted_generics),
    )
    func_type = CallableType(
        arg_types=[self_type],
        arg_kinds=[ARG_POS],
        arg_names=[None],
        ret_type=rshift_tvar,
        fallback=api.named_type("builtins.function"),
    )
    add_method_to_class(
        api,
        cls,
        "__rshift__",
        args=[Argument(Var("func", func_type), func_type, None, ARG_POS)],
        return_type=rshift_tvar,
        tvar_def=rshift_tvar,
    )

    # instance.replace(**changes) -> Self  (re-validated copy-with-changes)
    changes_type: Type = AnyType(TypeOfAny.special_form)
    add_method_to_class(
        api,
        cls,
        "replace",
        args=[Argument(Var("changes", changes_type), changes_type, None, ARG_STAR2)],
        return_type=self_type,
    )
    return ok


class StolasPlugin(Plugin):
    """Mypy plugin for stolas.

    Handles:
    - @cases: Transforms class annotations into callable variant constructors.
    - @struct: Injects the ``>>`` pipeline operator and ``.replace()`` method.
    """

    def get_class_decorator_hook(
        self, fullname: str
    ) -> Callable[[ClassDefContext], None] | None:
        """Main-pass hook: @cases retyping, @struct dataclass tagging."""
        if fullname in (CASES_DECORATOR, CASES_DECORATOR_SHORT):
            return _cases_class_callback
        if fullname in (STRUCT_DECORATOR, STRUCT_DECORATOR_SHORT):
            return _struct_tag_callback
        return None

    def get_class_decorator_hook_2(
        self, fullname: str
    ) -> Callable[[ClassDefContext], bool] | None:
        """Later-pass hook for @struct (adds methods once symbols resolve)."""
        if fullname in (STRUCT_DECORATOR, STRUCT_DECORATOR_SHORT):
            return _struct_class_callback
        return None


def plugin(version: str) -> TypingType[Plugin]:
    """Entry point for mypy plugin system."""
    return StolasPlugin
