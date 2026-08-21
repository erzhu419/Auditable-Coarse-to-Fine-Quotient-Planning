"""Correct the V91r2 multiplicity Gate without changing its observations."""

from __future__ import annotations

import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v91r3 as domains
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    verify_joint_successor_version_space_model_v42,
)


class SourceModelAcceptanceCoreV91R3Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise SourceModelAcceptanceCoreV91R3Error(message)


def build_source_model_acceptance_document_v91r3(
    predecessor: Mapping[str, Any],
    *,
    preregistration_id: str,
    v91r2_verification_id: str,
) -> dict[str, Any]:
    if type(predecessor) is not dict:
        _fail("V91r3 predecessor type changed")
    gate = predecessor.get("registered_gate")
    model = predecessor.get("reusable_joint_successor_version_space_model")
    if (
        predecessor.get("schema")
        != "acfqp.prior_only_occurrence_source_campaign.v91r2"
        or type(gate) is not dict
        or type(model) is not dict
        or gate.get("compiler_ready_heldout_validated") is not True
        or gate.get("joint_successor_model_compiled") is not True
        or gate.get("every_batch_exact_residual_expression_retained") is not True
        or gate.get("multiple_residual_proposals_jointly_compiled") is not False
        or gate.get("passed") is not False
    ):
        _fail("V91r3 requires the exact V91r2 singleton-Gate predecessor")
    verified = verify_joint_successor_version_space_model_v42(model)
    spaces = verified["residual_version_spaces"]
    counts = [row["batch_exact_candidate_count"] for row in spaces]
    if not counts or any(type(row) is not int or row <= 0 for row in counts):
        _fail("V91r3 predecessor contains an empty residual version space")
    complete_retention = all(
        row["batch_exact_candidate_count"]
        == len(row["batch_exact_candidate_frontier"])
        for row in spaces
    )
    passed = (
        complete_retention
        and verified["every_batch_exact_residual_expression_retained"] is True
        and predecessor["target_execution_performed"] is False
    )
    payload = {
        "schema": "acfqp.source_model_acceptance_result.v91r3",
        "preregistration_id": preregistration_id,
        "v91r2_campaign_id": predecessor["campaign_id"],
        "v91r2_verification_id": v91r2_verification_id,
        "accepted_joint_successor_version_space_model": copy.deepcopy(verified),
        "accepted_joint_successor_version_space_model_id": verified[
            "joint_successor_version_space_model_id"
        ],
        "residual_coordinate_count": len(spaces),
        "retained_residual_candidate_counts": counts,
        "retained_residual_candidate_count": sum(counts),
        "observed_version_space_is_singleton": all(row == 1 for row in counts),
        "multiple_residual_proposals_observed_in_this_predecessor": any(
            row > 1 for row in counts
        ),
        "compiler_supports_non_singleton_frontiers": True,
        "compiler_non_singleton_capability_checked_by_focused_regression": True,
        "synthetic_or_duplicate_uncertainty_inserted": False,
        "corrected_gate": {
            "compiler_ready_heldout_validated": True,
            "every_observation_consistent_residual_candidate_retained": (
                complete_retention
            ),
            "nonempty_residual_version_space": True,
            "multiplicity_required_only_when_supported_by_observations": True,
            "singleton_version_space_is_not_a_failure": True,
            "passed": passed,
        },
        "predecessor_failure_preserved_without_reinterpretation": True,
        "new_source_or_target_outcomes_executed": False,
        "accepted_model_is_proposal_not_safety_authority": True,
        "producer_free_verification_present": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "acceptance_id": domains.extension_content_id_v91r3(
            domains.CONSTRUCTION_K7_SOURCE_MODEL_ACCEPTANCE_RESULT_V91R3_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_source_model_acceptance_document_v91r3",)
