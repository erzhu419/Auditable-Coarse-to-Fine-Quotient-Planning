"""Public Phase-3E accounting boundary.

Only strict, non-official preconstruction APIs are exported here.  The retired
``PHASE3E_PRECONSTRUCTION_MECHANICS_PASS`` label remains private because the
current accepted boundary is explicitly partial and all official Gates are
still NOT_RUN.
"""

from __future__ import annotations

from typing import Any, Mapping

from acfqp import _phase3e_accounting_boundary as _boundary


COUNTER_COMPLETENESS_NOT_RUN = _boundary.COUNTER_COMPLETENESS_NOT_RUN
ECONOMICS_NOT_RUN = _boundary.ECONOMICS_NOT_RUN
LEGACY_PROJECTION_LABEL = _boundary.LEGACY_PROJECTION_LABEL
NATIVE_REGISTRY_DRAFT = _boundary.NATIVE_REGISTRY_DRAFT
ROUTING_MECHANICS_ONLY = _boundary.ROUTING_MECHANICS_ONLY
UNRESOLVED = _boundary.UNRESOLVED

PRECONSTRUCTION_CORE_PARTIAL = "PHASE3E_PRECONSTRUCTION_CORE_MECHANICS_PARTIAL"


def phase3e_native_registry_draft():
    return _boundary.phase3e_native_registry_draft()


def legacy_phase3b_registry():
    return _boundary.legacy_phase3b_registry()


def legacy_phase3b_projection(document: Mapping[str, Any]) -> dict[str, Any]:
    return _boundary.legacy_phase3b_projection(document)


def phase3e_preregistration_skeleton() -> dict[str, Any]:
    return _boundary.phase3e_preregistration_skeleton()


__all__ = [
    "COUNTER_COMPLETENESS_NOT_RUN",
    "ECONOMICS_NOT_RUN",
    "LEGACY_PROJECTION_LABEL",
    "NATIVE_REGISTRY_DRAFT",
    "PRECONSTRUCTION_CORE_PARTIAL",
    "ROUTING_MECHANICS_ONLY",
    "UNRESOLVED",
    "legacy_phase3b_projection",
    "legacy_phase3b_registry",
    "phase3e_native_registry_draft",
    "phase3e_preregistration_skeleton",
]
