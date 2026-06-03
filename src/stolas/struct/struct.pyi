"""Type stubs for struct decorator."""

from typing import Callable, TypeVar, Type, overload
from typing_extensions import dataclass_transform

_T = TypeVar("_T")

@overload
@dataclass_transform(
    eq_default=True,
    order_default=False,
    kw_only_default=True,
    frozen_default=True,
    field_specifiers=(),
)
def struct(cls: Type[_T]) -> Type[_T]: ...
@overload
@dataclass_transform(
    eq_default=True,
    order_default=False,
    kw_only_default=True,
    frozen_default=True,
    field_specifiers=(),
)
def struct(*, open: bool = ...) -> Callable[[Type[_T]], Type[_T]]: ...
