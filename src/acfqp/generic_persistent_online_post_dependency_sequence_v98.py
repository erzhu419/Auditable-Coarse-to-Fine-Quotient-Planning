"""Persist a post-dependency model activated inside certificate search."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_online_post_dependency_certificate_planner_v98 import (
    run_online_post_dependency_certificate_episode_v98,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.generic_post_dependency_residual_v97 import (
    plan_post_dependency_abstract_program_v97,
)
from acfqp.generic_preloaded_certificate_receding_engine_v74 import (
    run_preloaded_certificate_receding_episode_v74,
)
from acfqp.phase3e_ids import canonical_json_bytes


_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-online-post-dependency-sequence:v98\x00"


class GenericPersistentOnlinePostDependencySequenceV98Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPersistentOnlinePostDependencySequenceV98Error(message)


def _row(document: Mapping[str, Any]) -> FlatRawTransitionV4:
    selected = document.get("selected_action")
    if type(selected) is not dict:
        _fail("V98 persisted transition action changed")
    return FlatRawTransitionV4(
        document["occurrence"],
        document["transition_index"],
        tuple(document["pre_vector"]),
        tuple(document["legal_action_keys_before"]),
        FlatRawActionV4(
            selected["action_key"], tuple(selected["anonymous_fields"])
        ),
        tuple(document["post_vector"]),
        tuple(document["legal_action_keys_after"]),
        document["terminal_acceptance_after"],
        document.get("outcome_tape_sha256"),
    )


def _deduplicate(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[FlatRawTransitionV4, ...]:
    unique = {}
    for row in rows:
        unique[(row.pre, row.action.key, row.post)] = row
    return tuple(unique[key] for key in sorted(unique))


def _group_count(rows: tuple[FlatRawTransitionV4, ...]) -> int:
    return len({(row.pre, row.action.key) for row in rows})


def _orderer(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    planning_rows: tuple[FlatRawTransitionV4, ...],
    acquisition: Mapping[str, Any] | None,
    *,
    maximum_abstract_depth: int,
    maximum_support_branch_evaluations: int,
    support_feasible_beam_width: int,
):
    dependency_count = (
        0
        if acquisition is None
        else len(acquisition["retrospective_post_dependency_candidates"])
    )

    def order(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
        if acquisition is not None:
            try:
                plan = plan_post_dependency_abstract_program_v97(
                    candidate,
                    planning_rows,
                    adapter.catalogue,
                    raw,
                    acquisition,
                    maximum_depth=maximum_abstract_depth,
                    maximum_support_branch_evaluations=(
                        maximum_support_branch_evaluations
                    ),
                    support_feasible_beam_width=support_feasible_beam_width,
                )
            except Exception as error:
                if not error.__class__.__module__.startswith("acfqp.generic_"):
                    raise
            else:
                return {
                    **copy.deepcopy(plan),
                    "persistent_online_model_used": True,
                    "persistent_post_dependency_program_used": dependency_count > 0,
                    "persistent_partial_fallback_used": False,
                }
        try:
            partial = plan_partial_factor_observation_graph_v15(
                candidate, planning_rows, adapter.catalogue, raw
            )
        except Exception as first_error:
            if not first_error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            try:
                partial = plan_partial_factor_program_v15(
                    candidate,
                    planning_rows,
                    adapter.catalogue,
                    raw,
                    maximum_depth=maximum_abstract_depth,
                )
            except Exception as second_error:
                if not second_error.__class__.__module__.startswith("acfqp.generic_"):
                    raise
                return None
        actions = partial.get("action_keys")
        if type(actions) is not list or not actions:
            return None
        return {
            "schema": "acfqp.generic_persistent_online_partial_fallback_plan.v98",
            "initial_action_key": actions[0],
            "abstract_support_branch_evaluations": partial.get(
                "projected_planning_compute_events", 0
            ),
            "partial_plan": copy.deepcopy(partial),
            "persistent_online_model_used": False,
            "persistent_post_dependency_program_used": False,
            "persistent_partial_fallback_used": True,
            "ground_transition_accessed_during_abstract_search": False,
            "abstract_plan_used_as_safety_authority": False,
        }

    return order


def run_persistent_online_post_dependency_arm_v98(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
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
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or type(episode_indices) is not tuple
        or len(episode_indices) < 2
        or len(set(episode_indices)) != len(episode_indices)
        or _group_count(observed_rows) != acquisition_ground_support_labels
    ):
        _fail("V98 persistent online arm inventory changed")
    first = run_online_post_dependency_certificate_episode_v98(
        adapter,
        candidate,
        observed_rows,
        residual_prior_library=residual_prior_library,
        structural_prior_library=structural_prior_library,
        episode_index=episode_indices[0],
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        confidence_denominator=confidence_denominator,
        maximum_support_branch_evaluations=maximum_support_branch_evaluations,
        support_feasible_beam_width=support_feasible_beam_width,
    )
    local_rows = tuple(_row(row) for row in first["raw_local_transition_rows"])
    persistent_rows = _deduplicate((*observed_rows, *local_rows))
    acquisition = first["active_post_dependency_acquisition"]
    orderer = _orderer(
        adapter,
        candidate,
        persistent_rows,
        acquisition,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_support_branch_evaluations=maximum_support_branch_evaluations,
        support_feasible_beam_width=support_feasible_beam_width,
    )
    paid_certificate_labels = first["local_ground_support_labels"]
    later = []
    for episode_index in episode_indices[1:]:
        episode = run_preloaded_certificate_receding_episode_v74(
            adapter,
            candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=_group_count(persistent_rows),
            arm="PERSISTENT_ONLINE_POST_DEPENDENCY_TRANSFER",
            abstract_orderer=orderer,
            episode_index=episode_index,
            maximum_execution_steps=maximum_execution_steps,
            maximum_incremental_certificate_ground_support_labels=(
                maximum_incremental_certificate_ground_support_labels
            ),
        )
        incremental = episode[
            "incremental_certificate_local_ground_support_labels"
        ]
        paid_certificate_labels += incremental
        new_rows = tuple(
            _row(document) for document in episode["raw_incremental_transition_rows"]
        )
        persistent_rows = _deduplicate((*persistent_rows, *new_rows))
        later.append(
            {
                **copy.deepcopy(episode),
                "new_certificate_labels_charged_this_episode": incremental,
                "paid_certificate_labels_cumulative": paid_certificate_labels,
                "persistent_exact_support_group_count": _group_count(
                    persistent_rows
                ),
            }
        )
    activation = first["candidate_activated_at_ground_support_label"]
    activation_observed = type(activation) is int
    right_censored_activation_label = (
        activation
        if activation_observed
        else first["local_ground_support_labels"] + 1
    )
    receipts = [
        receipt
        for episode in later
        for receipt in episode["abstract_plan_receipts"]
        if receipt["abstract_plan"].get("persistent_online_model_used") is True
    ]
    dependency_receipts = [
        receipt
        for receipt in receipts
        if receipt["abstract_plan"].get(
            "persistent_post_dependency_program_used"
        )
        is True
    ]
    failures = [
        *first["failed_certificates"],
        *(row for episode in later for row in episode["failed_certificates"]),
    ]
    distinctions = [
        *first["local_distinctions"],
        *(row for episode in later for row in episode["local_distinctions"]),
    ]
    overlay = [row.to_document() for row in persistent_rows]
    payload = {
        "schema": "acfqp.generic_persistent_online_post_dependency_sequence.v98",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "arm": first["arm"],
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "partial_acquisition_ground_support_labels_paid_once": (
            acquisition_ground_support_labels
        ),
        "first_online_post_dependency_episode": copy.deepcopy(first),
        "post_dependency_model_activation_observed": activation_observed,
        "post_dependency_model_activation_local_ground_support_label": activation,
        "post_dependency_model_activation_label_with_right_censoring": (
            right_censored_activation_label
        ),
        "target_model_activation_ground_support_labels_with_right_censoring": (
            acquisition_ground_support_labels + right_censored_activation_label
        ),
        "retained_active_post_dependency_acquisition": copy.deepcopy(acquisition),
        "later_persistent_episodes": later,
        "later_online_model_abstract_plan_receipt_count": len(receipts),
        "later_post_dependency_abstract_plan_receipt_count": len(
            dependency_receipts
        ),
        "later_execution_action_matches_abstract_proposal_count": sum(
            episode["execution_action_matches_abstract_proposal_count"]
            for episode in later
        ),
        "later_query_ground_support_labels": sum(
            episode["new_certificate_labels_charged_this_episode"]
            for episode in later
        ),
        "persistent_exact_overlay_rows": overlay,
        "persistent_exact_overlay_sha256": hashlib.sha256(
            canonical_json_bytes(overlay)
        ).hexdigest(),
        "persistent_exact_support_group_count": _group_count(persistent_rows),
        "certificate_ground_support_labels_paid_once": paid_certificate_labels,
        "lifetime_target_ground_support_labels": (
            acquisition_ground_support_labels + paid_certificate_labels
        ),
        "all_failed_certificates": failures,
        "all_local_distinctions": distinctions,
        "every_new_ground_query_followed_a_failed_certificate": all(
            row.get("ground_query_performed_before_failure") is False
            for row in failures
        )
        and all(
            row.get("query_after_failed_certificate") is True
            for row in distinctions
        ),
        "post_dependency_model_is_fallible_action_ordering_heuristic": True,
        "persistent_exact_overlay_exclusively_discharges_safety": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": hashlib.sha256(
            _SEQUENCE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_persistent_online_post_dependency_arm_v98",)
