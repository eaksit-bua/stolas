from typing import Any, TypeVar

_T = TypeVar("_T")

def replace(instance: _T, **changes: Any) -> _T: ...
