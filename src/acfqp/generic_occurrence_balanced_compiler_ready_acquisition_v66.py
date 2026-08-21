"""Compiler-ready acquisition under the V66 occurrence-balanced schedule."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_compiler_ready_acquisition_v52 import (
    acquire_compiler_ready_terminal_program_v52,
)
from acfqp.generic_occurrence_balanced_relation_schedule_v66 import (
    schedule_occurrence_balanced_relation_queries_v66,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericOccurrenceBalancedCompilerReadyAcquisitionV66Error(ValueError):
    pass


_BUNDLE_DOMAIN = b"acfqp:generic-occurrence-balanced-compiler-ready-bundle:v66\x00"


def _fail(message: str) -> NoReturn:
    raise GenericOccurrenceBalancedCompilerReadyAcquisitionV66Error(message)


def run_occurrence_balanced_compiler_ready_acquisition_v66(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    if type(source_complete_evidence) is not dict:
        _fail("V66 source evidence changed")
    schedule = schedule_occurrence_balanced_relation_queries_v66(
        source_complete_evidence
    )
    ordered = copy.deepcopy(source_complete_evidence)
    ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    acquisition = acquire_compiler_ready_terminal_program_v52(
        ordered,
        role_free_template_library=role_free_template_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.occurrence_balanced_compiler_ready_acquisition.v66",
        "query_schedule": schedule,
        "compiler_ready_acquisition": acquisition,
        "query_schedule_id": schedule["occurrence_balanced_query_schedule_id"],
        "compiler_ready_acquisition_id": acquisition[
            "compiler_ready_acquisition_id"
        ],
        "confidence_denominator": confidence_denominator,
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "occurrence_identity_used_only_for_source_schedule_balance": True,
        "residual_successor_consensus_used_as_acquisition_gate": False,
        "nonempty_residual_version_space_used_as_readiness_gate": True,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "occurrence_balanced_compiler_ready_acquisition_id": hashlib.sha256(
            _BUNDLE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_occurrence_balanced_compiler_ready_acquisition_v66",)
