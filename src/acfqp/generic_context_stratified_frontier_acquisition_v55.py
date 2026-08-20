"""Run V54 joint frontier acquisition on the V55 context-stratified schedule."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping

from acfqp.generic_context_stratified_schedule_v55 import (
    schedule_context_stratified_queries_v55,
)
from acfqp.generic_contextual_ordinal_frontier_acquisition_v54 import (
    acquire_contextual_ordinal_frontiers_v54,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


_BUNDLE_DOMAIN = b"acfqp:context-stratified-contextual-ordinal-acquisition:v55\x00"


def run_context_stratified_frontier_acquisition_v55(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    schedule = schedule_context_stratified_queries_v55(source_complete_evidence)
    ordered = copy.deepcopy(source_complete_evidence)
    ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    acquisition = acquire_contextual_ordinal_frontiers_v54(
        ordered,
        role_free_template_library=role_free_template_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.context_stratified_contextual_ordinal_acquisition.v55",
        "query_schedule": schedule,
        "contextual_ordinal_frontier_acquisition": acquisition,
        "context_stratified_query_schedule_id": schedule[
            "context_stratified_query_schedule_id"
        ],
        "contextual_ordinal_frontier_acquisition_id": acquisition[
            "contextual_ordinal_frontier_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "context_and_relation_round_robin": True,
        "all_terminal_and_residual_frontier_candidates_checked_prequentially": True,
        "contextual_action_supports_derived_from_catalogue_only": True,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "context_stratified_contextual_ordinal_acquisition_id": hashlib.sha256(
            _BUNDLE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_context_stratified_frontier_acquisition_v55",)
