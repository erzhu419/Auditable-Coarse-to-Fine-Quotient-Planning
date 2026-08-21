"""Deterministically audit V89 ground certificates against abstract proposals."""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v90 as domains
from acfqp.generic_abstract_proposal_primary_audit_v63 import (
    audit_abstract_proposal_primary_v63,
)
from acfqp.generic_portable_coordinate_aligned_inputs_v64 import (
    reconstruct_coordinate_aligned_planning_inputs_v64,
)


class AbstractPlanningPrimaryAuditCoreV90Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AbstractPlanningPrimaryAuditCoreV90Error(message)


def build_abstract_planning_primary_audit_document_v90(
    campaign: Mapping[str, Any],
    preregistration_id: str,
    v89_verification_id: str,
    model: Mapping[str, Any],
    applicability_program: Mapping[str, Any],
    *,
    maximum_abstract_depth: int,
    maximum_abstract_support_branch_evaluations: int,
    abstract_support_feasible_beam_width: int,
) -> dict[str, Any]:
    if (
        type(campaign) is not dict
        or campaign.get("schema")
        != "acfqp.permutation_matched_sample_tax_campaign.v89"
        or campaign.get("sample_tax_reduction_verified") is not True
        or campaign.get("registered_gate", {}).get("passed") is not True
        or type(campaign.get("target_occurrences")) is not list
    ):
        _fail("V90 frozen V89 input changed")
    occurrences = []
    for source in campaign["target_occurrences"]:
        candidate, _rows, catalogue = reconstruct_coordinate_aligned_planning_inputs_v64(
            model,
            source["coordinate_alignment"],
            source["target_common_partial_acquisition"]["candidate"],
            source["target_common_partial_raw_transition_rows"],
            source["target_common_partial_action_catalogue"],
        )
        episode = source["matched_ablation"]["arms"][
            "APPLICABILITY_CONDITIONED_WORLD_MODEL"
        ]
        audit = audit_abstract_proposal_primary_v63(
            episode,
            model,
            applicability_program,
            candidate,
            catalogue,
            maximum_abstract_depth=maximum_abstract_depth,
            maximum_abstract_support_branch_evaluations=(
                maximum_abstract_support_branch_evaluations
            ),
            abstract_support_feasible_beam_width=(
                abstract_support_feasible_beam_width
            ),
        )
        if (
            audit["audited_exact_transition_state_count"]
            != episode["queried_state_action_count"]
            or audit["replayed_abstract_planning_compute_events"]
            != episode["abstract_planning_compute_events"]
        ):
            _fail("V90 replayed proposal audit and frozen episode diverged")
        payload = {
            "schema": "acfqp.abstract_planning_primary_occurrence.v90",
            "source_v89_occurrence_id": source["occurrence_id"],
            "target_seed": source["target_seed"],
            "coordinate_alignment_id": source["coordinate_alignment_id"],
            "action_key_permutation_id": source[
                "outcome_blind_action_key_permutation"
            ]["permutation_id"],
            "source_episode_id": episode["episode_id"],
            "proposal_primary_audit": audit,
            "proposal_primary_audit_id": audit["audit_id"],
            "target_episode_outcome_reexecution_performed": False,
            "ground_kernel_accessed_by_v90_audit": False,
            "abstract_model_used_as_safety_authority": False,
            "exact_query_local_certificate_remained_only_safety_authority": True,
        }
        occurrences.append(
            {
                **payload,
                "occurrence_audit_id": domains.extension_content_id_v90(
                    domains.CONSTRUCTION_K7_ABSTRACT_PRIMARY_OCCURRENCE_V90_DOMAIN,
                    payload,
                ),
            }
        )
    every_primary = bool(occurrences) and all(
        row["proposal_primary_audit"][
            "ground_queries_used_only_to_certify_abstractly_proposed_policy"
        ]
        is True
        and row["proposal_primary_audit"]["proposal_mismatch_count"] == 0
        and row["proposal_primary_audit"][
            "non_proposed_alternative_action_query_count"
        ]
        == 0
        for row in occurrences
    )
    audited_states = sum(
        row["proposal_primary_audit"]["audited_exact_transition_state_count"]
        for row in occurrences
    )
    replay_compute = sum(
        row["proposal_primary_audit"]["replayed_abstract_planning_compute_events"]
        for row in occurrences
    )
    passed = (
        len(occurrences) == 6
        and every_primary
        and audited_states
        == campaign["accounting"]["derived_queried_state_action_count"]
        and replay_compute
        == campaign["accounting"]["derived_abstract_planning_compute_events"]
    )
    payload = {
        "schema": "acfqp.abstract_planning_primary_audit.v90",
        "preregistration_id": preregistration_id,
        "v89_campaign_id": campaign["campaign_id"],
        "v89_verification_id": v89_verification_id,
        "source_model_id": model["projected_disagreement_successor_model_id"],
        "action_applicability_program_id": applicability_program[
            "action_applicability_program_id"
        ],
        "occurrence_audits": occurrences,
        "registered_gate": {
            "required_occurrence_audit_count": 6,
            "actual_occurrence_audit_count": len(occurrences),
            "every_exactly_certified_action_abstractly_proposed_first": every_primary,
            "non_proposed_ground_action_query_count": sum(
                row["proposal_primary_audit"][
                    "non_proposed_alternative_action_query_count"
                ]
                for row in occurrences
            ),
            "proposal_mismatch_count": sum(
                row["proposal_primary_audit"]["proposal_mismatch_count"]
                for row in occurrences
            ),
            "audited_exact_transition_state_count": audited_states,
            "replayed_abstract_planning_compute_events": replay_compute,
            "frozen_v89_accounting_exactly_reproduced": (
                audited_states
                == campaign["accounting"]["derived_queried_state_action_count"]
                and replay_compute
                == campaign["accounting"][
                    "derived_abstract_planning_compute_events"
                ]
            ),
            "passed": passed,
        },
        "multi_step_planning_primarily_in_abstract_model_verified": passed,
        "claim_scope": "FROZEN_V89_PERMUTATION_MATCHED_BALANCED_BATCH_WORKLOAD_ONLY",
        "ground_queries_used_only_for_exact_policy_certificate": every_primary,
        "certificate_failure_only_local_ground_recovery_preserved": True,
        "target_episode_outcome_reexecution_performed": False,
        "ground_kernel_accessed_by_v90_audit": False,
        "sample_tax_reduction_inherited_from_independently_verified_v89": True,
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
        "audit_id": domains.extension_content_id_v90(
            domains.CONSTRUCTION_K7_ABSTRACT_PRIMARY_AUDIT_V90_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_abstract_planning_primary_audit_document_v90",)
