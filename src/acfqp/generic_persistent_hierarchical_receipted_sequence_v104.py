"""Persistent V103 execution with explicit full-versus-partial V104 receipts."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping

from acfqp.generic_hierarchical_abstract_execution_receipt_v104 import (
    build_hierarchical_abstract_execution_receipt_v104,
)
from acfqp.generic_persistent_receipted_sequence_v103 import (
    run_persistent_receipted_arm_v103,
)
from acfqp.phase3e_ids import canonical_json_bytes

_DOMAIN = b"acfqp:generic-persistent-hierarchical-receipted-sequence:v104\x00"


def run_persistent_hierarchical_receipted_arm_v104(
    adapter: Any,
    candidate: Any,
    observed_rows: tuple[Any, ...],
    acquisition_ground_support_labels: int,
    *,
    residual_prior_library: Mapping[str, Any],
    structural_prior_library: Mapping[str, Any] | None,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    confidence_denominator: int,
    maximum_support_branch_evaluations: int,
    support_feasible_beam_width: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    predecessor = run_persistent_receipted_arm_v103(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        residual_prior_library=residual_prior_library,
        structural_prior_library=structural_prior_library,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        confidence_denominator=confidence_denominator,
        maximum_support_branch_evaluations=maximum_support_branch_evaluations,
        support_feasible_beam_width=support_feasible_beam_width,
        maximum_incremental_certificate_ground_support_labels=(
            maximum_incremental_certificate_ground_support_labels
        ),
    )
    episodes = [
        predecessor["first_agreement_shielded_online_episode"],
        *predecessor["later_persistent_episodes"],
    ]
    receipts = [
        build_hierarchical_abstract_execution_receipt_v104(
            episode_index=episode["episode_index"], base_receipt=receipt
        )
        for episode in episodes
        for receipt in episode["abstract_execution_receipts"]
    ]
    full = sum(
        row["abstract_ordering_source"] == "FULL_POST_DEPENDENCY_WORLD_MODEL"
        for row in receipts
    )
    partial = sum(
        row["abstract_ordering_source"]
        == "COMPILED_PARTIAL_WORLD_MODEL_FALLBACK"
        for row in receipts
    )
    exact = sum(
        row["abstract_ordering_source"] == "EXACT_CERTIFICATE_POLICY_ONLY"
        for row in receipts
    )
    payload = {
        "schema": "acfqp.generic_persistent_hierarchical_receipted_sequence.v104",
        "family": predecessor["family"],
        "seed": predecessor["seed"],
        "episode_indices": list(episode_indices),
        "arm": predecessor["arm"],
        "v103_receipted_sequence": copy.deepcopy(predecessor),
        "v103_receipted_sequence_id": predecessor["sequence_id"],
        "hierarchical_abstract_execution_receipts": receipts,
        "hierarchical_receipt_count": len(receipts),
        "execution_step_count": sum(episode["execution_steps"] for episode in episodes),
        "full_post_dependency_world_model_match_count": full,
        "compiled_partial_world_model_fallback_match_count": partial,
        "exact_certificate_policy_only_count": exact,
        "abstract_model_ordered_execution_count": full + partial,
        "every_action_classified_into_exactly_one_ordering_source": (
            full + partial + exact == len(receipts)
        ),
        "full_model_match_not_inferred_from_partial_fallback": True,
        "partial_world_model_incompleteness_explicit": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": hashlib.sha256(
            _DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_persistent_hierarchical_receipted_arm_v104",)
