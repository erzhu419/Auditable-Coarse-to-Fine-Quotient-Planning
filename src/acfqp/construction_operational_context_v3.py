"""Narrow execution context for construction-only no-full-replay paths.

The legacy V2 runner keeps its portable replay behavior by default. Contract
successors may activate this context around an owned, same-process execution
and select authorities that inspect the already-owned object graph instead of
repeating a complete planner replay. This module stores no totals and mints no
evidence; it is only a fail-closed routing signal.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator


class ConstructionOperationalContextV3Error(RuntimeError):
    """The scoped construction execution context was misused."""


_CONTEXT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _ConstructionOperationalContextV3:
    issuer: object
    no_full_replay: bool

    def __post_init__(self) -> None:
        if self.issuer is not _CONTEXT_ISSUER or self.no_full_replay is not True:
            raise ConstructionOperationalContextV3Error(
                "construction operational context is caller-minted"
            )


_ACTIVE: ContextVar[_ConstructionOperationalContextV3 | None] = ContextVar(
    "acfqp_construction_operational_context_v3",
    default=None,
)


@contextmanager
def _activate_owned_no_full_replay_v3() -> Iterator[None]:
    """Activate one non-nestable, same-context construction execution."""

    if _ACTIVE.get() is not None:
        raise ConstructionOperationalContextV3Error(
            "construction operational context cannot be nested"
        )
    token: Token[_ConstructionOperationalContextV3 | None] = _ACTIVE.set(
        _ConstructionOperationalContextV3(_CONTEXT_ISSUER, True)
    )
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def operational_no_full_replay_enabled_v3() -> bool:
    """Return true only inside the owned successor execution context."""

    active = _ACTIVE.get()
    return (
        type(active) is _ConstructionOperationalContextV3
        and active.issuer is _CONTEXT_ISSUER
        and active.no_full_replay is True
    )


__all__ = [
    "ConstructionOperationalContextV3Error",
    "operational_no_full_replay_enabled_v3",
]
