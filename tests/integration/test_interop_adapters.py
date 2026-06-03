"""Interop adapter integration tests (recipe-level, via stolas.serde only).

Milestone 6 ships NO heavy adapters and NO ``stolas[pydantic]`` extra: interop
is a few lines through the existing free functions ``to_dict``/``from_dict``.
These tests demonstrate round-tripping a ``@struct``/``@cases`` value through
third-party libraries using ONLY ``stolas.serde``.

Each library is gated by ``pytest.importorskip`` so the file collects-but-skips
cleanly when the dependency is absent (it IS absent in this venv). Crucially the
tests touch only ``stolas.serde`` (already 100%-covered product code) plus the
third-party library, so skipping them does NOT drop product coverage.
"""

import os
import sys
from typing import Any

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from stolas.operand import cases
from stolas.serde import from_dict, to_dict
from stolas.struct import struct


@struct
class Point:
    x: int
    y: int


@cases
class Box:
    Item: Any
    Empty: None


class TestPydanticInterop:
    """A stolas @struct round-trips through a pydantic BaseModel via serde."""

    def test_struct_round_trips_through_pydantic_model(self) -> None:
        pydantic = pytest.importorskip("pydantic")

        class PointModel(pydantic.BaseModel):
            x: int
            y: int

        original = Point(x=1, y=2)
        model = PointModel(**to_dict(original))
        restored = from_dict(Point, model.model_dump())
        assert restored == original

    def test_cases_value_variant_round_trips_through_pydantic(self) -> None:
        pydantic = pytest.importorskip("pydantic")

        class Tagged(pydantic.BaseModel):
            tag: str = pydantic.Field(alias="__tag__")
            value: int

        original = Box.Item(7)
        model = Tagged(**to_dict(original))
        restored = from_dict(Box, model.model_dump(by_alias=True))
        assert restored == original


class TestSqlAlchemyInterop:
    """A stolas @struct round-trips through a SQLAlchemy row mapping via serde."""

    def test_struct_round_trips_through_sqlalchemy(self) -> None:
        sa = pytest.importorskip("sqlalchemy")
        engine = sa.create_engine("sqlite:///:memory:")
        metadata = sa.MetaData()
        table = sa.Table(
            "points",
            metadata,
            sa.Column("x", sa.Integer),
            sa.Column("y", sa.Integer),
        )
        metadata.create_all(engine)

        original = Point(x=3, y=4)
        with engine.begin() as conn:
            conn.execute(sa.insert(table).values(**to_dict(original)))
        with engine.connect() as conn:
            row = conn.execute(sa.select(table)).mappings().one()
        restored = from_dict(Point, dict(row))
        assert restored == original


class TestMsgspecInterop:
    """A stolas @struct round-trips through msgspec JSON via serde."""

    def test_struct_round_trips_through_msgspec(self) -> None:
        msgspec = pytest.importorskip("msgspec")
        original = Point(x=5, y=6)
        encoded = msgspec.json.encode(to_dict(original))
        decoded = msgspec.json.decode(encoded)
        restored = from_dict(Point, decoded)
        assert restored == original

    def test_cases_value_variant_round_trips_through_msgspec(self) -> None:
        msgspec = pytest.importorskip("msgspec")
        original = Box.Item(11)
        encoded = msgspec.json.encode(to_dict(original))
        restored = from_dict(Box, msgspec.json.decode(encoded))
        assert restored == original
