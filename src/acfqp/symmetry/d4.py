"""Thin accessors for the project's single authoritative :math:`D_4` registry.

The frozen element IDs, ordering, composition convention and inverse operation
live in :mod:`acfqp.domains.g2048`.  The generic quotient layer accepts group
operations as callables; this module merely re-exports that registry so callers
never have to translate between competing D4 element types.
"""

from __future__ import annotations

from typing import Iterable, TypeVar

from acfqp.domains.g2048 import (
    D4_ELEMENTS,
    D4Transform,
    compose_d4,
    inverse_d4,
    transform_board,
    transform_cell,
)


ValueT = TypeVar("ValueT")


def transform_square_values(
    values: Iterable[ValueT],
    size: int,
    transform: D4Transform,
) -> tuple[ValueT, ...]:
    """Transform arbitrary row-major payloads using the authoritative IDs."""

    source = tuple(values)
    if len(source) != size * size:
        raise ValueError("value count does not match square size")
    destination: list[ValueT | None] = [None] * len(source)
    for old_index, value in enumerate(source):
        destination[transform_cell(old_index, size, transform)] = value
    if any(value is None for value in destination):  # pragma: no cover - defensive
        raise AssertionError("D4 index transform did not form a permutation")
    return tuple(destination)  # type: ignore[arg-type]


__all__ = [
    "D4Transform",
    "D4_ELEMENTS",
    "compose_d4",
    "inverse_d4",
    "transform_board",
    "transform_cell",
    "transform_square_values",
]

