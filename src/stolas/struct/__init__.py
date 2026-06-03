"""S: Struct module."""

from .replace import replace
from .struct import struct
from .trait import MissingImplementationWarning, trait

__all__ = ["struct", "trait", "MissingImplementationWarning", "replace"]
