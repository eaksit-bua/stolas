"""Serialization codec for stolas types (zero-dependency, type-directed)."""

from stolas.serde.codec import from_dict, from_json, to_dict, to_json

__all__ = ["to_dict", "from_dict", "to_json", "from_json"]
