"""Inactive-by-default phase labels for adaptive K7 native event emission."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from enum import Enum
from typing import Iterator


class AdaptiveAccountingPhaseV1(str, Enum):
    COMMON_PREFIX = "COMMON_PREFIX"
    LOCAL_RECOVERY = "LOCAL_RECOVERY"
    ABSTRACT_CERTIFICATE = "ABSTRACT_CERTIFICATE"


_ACTIVE_PHASE: ContextVar[AdaptiveAccountingPhaseV1] = ContextVar(
    "acfqp_k7_adaptive_accounting_phase_v1",
    default=AdaptiveAccountingPhaseV1.COMMON_PREFIX,
)


def current_adaptive_accounting_phase_v1() -> AdaptiveAccountingPhaseV1:
    return _ACTIVE_PHASE.get()


@contextmanager
def adaptive_accounting_phase_v1(
    phase: AdaptiveAccountingPhaseV1 | str,
) -> Iterator[None]:
    selected = AdaptiveAccountingPhaseV1(phase)
    token = _ACTIVE_PHASE.set(selected)
    try:
        yield
    finally:
        _ACTIVE_PHASE.reset(token)


__all__ = (
    "AdaptiveAccountingPhaseV1",
    "adaptive_accounting_phase_v1",
    "current_adaptive_accounting_phase_v1",
)
