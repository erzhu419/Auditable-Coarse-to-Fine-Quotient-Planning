"""Persist an agreement-shielded online model across episodes."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_receipted_online_certificate_planner_v103 import (
    run_receipted_online_certificate_episode_v103,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.generic_post_dependency_residual_v97 import (
    plan_post_dependency_abstract_program_v97,
)
from acfqp.generic_receipted_preloaded_certificate_engine_v103 import (
    run_receipted_preloaded_certificate_episode_v103,
)
from acfqp.phase3e_ids import canonical_json_bytes


_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-receipted-sequence:v103\x00"


class GenericPersistentAgreementShieldedSequenceV99Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPersistentAgreementShieldedSequenceV99Error(message)


def _row(document: Mapping[str, Any]) -> FlatRawTransitionV4:
    selected = document.get("selected_action")
    if type(selected) is not dict:
        _fail("V99 persisted transition action changed")
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


def _partial_plan(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    raw: tuple[int, ...],
    maximum_depth: int,
) -> Mapping[str, Any] | None:
    try:
        return plan_partial_factor_observation_graph_v15(
            candidate, rows, adapter.catalogue, raw
        )
    except Exception as first_error:
        if not first_error.__class__.__module__.startswith("acfqp.generic_"):
            raise
    try:
        return plan_partial_factor_program_v15(
            candidate,
            rows,
            adapter.catalogue,
            raw,
            maximum_depth=maximum_depth,
        )
    except Exception as second_error:
        if not second_error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        return None


def _orderer(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    planning_rows: tuple[FlatRawTransitionV4, ...],
    acquisition: Mapping[str, Any],
    *,
    maximum_abstract_depth: int,
    maximum_support_branch_evaluations: int,
    support_feasible_beam_width: int,
):
    dependency_count = len(
        acquisition["retrospective_post_dependency_candidates"]
    )

    def order(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
        partial = _partial_plan(
            adapter,
            candidate,
            planning_rows,
            raw,
            maximum_abstract_depth,
        )
        partial_actions = (
            ()
            if partial is None or not partial.get("action_keys")
            else tuple(partial["action_keys"][:1])
        )
        abstract = None
        try:
            abstract = plan_post_dependency_abstract_program_v97(
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
        abstract_actions = (
            () if abstract is None else (abstract["initial_action_key"],)
        )
        legal = next(
            (row.legal_before for row in planning_rows if row.pre == raw), ()
        )
        if not legal:
            legal = tuple(dict.fromkeys((*partial_actions, *abstract_actions)))
        if not legal:
            return None
        shield = shield_abstract_action_order_v99(
            abstract_proposal=abstract_actions,
            partial_proposal=partial_actions,
            legal_action_keys=legal,
        )
        if shield["abstract_proposal_admitted_to_action_order"] is True:
            return {
                **copy.deepcopy(abstract),
                "persistent_online_model_used": True,
                "persistent_post_dependency_program_used": dependency_count > 0,
                "persistent_partial_fallback_used": False,
                "agreement_shield_receipt": shield,
            }
        if partial is None or not partial_actions:
            return None
        return {
            "schema": "acfqp.generic_persistent_agreement_shielded_fallback_plan.v99",
            "initial_action_key": partial_actions[0],
            "abstract_support_branch_evaluations": partial.get(
                "projected_planning_compute_events", 0
            ),
            "partial_plan": copy.deepcopy(partial),
            "persistent_online_model_used": False,
            "persistent_online_model_evaluated": abstract is not None,
            "persistent_post_dependency_program_used": False,
            "persistent_partial_fallback_used": True,
            "agreement_shield_receipt": shield,
            "ground_transition_accessed_during_abstract_search": False,
            "abstract_plan_used_as_safety_authority": False,
        }

    return order


def run_persistent_agreement_shielded_arm_v99(
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
        _fail("V99 persistent shielded arm inventory changed")
    first = run_receipted_online_certificate_episode_v103(
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
    if type(acquisition) is not dict:
        _fail("V99 first episode did not activate a persistent model")
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
        episode = run_receipted_preloaded_certificate_episode_v103(
            adapter,
            candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=_group_count(persistent_rows),
            arm="PERSISTENT_AGREEMENT_SHIELDED_POST_DEPENDENCY_TRANSFER",
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
    right_censored = (
        activation
        if activation_observed
        else first["local_ground_support_labels"] + 1
    )
    receipts = [
        receipt
        for episode in later
        for receipt in episode["abstract_plan_receipts"]
    ]
    agreement_receipts = [
        row
        for row in receipts
        if row["abstract_plan"]["agreement_shield_receipt"][
            "abstract_partial_agreement"
        ]
        is True
    ]
    disagreement_receipts = [
        row
        for row in receipts
        if row["abstract_plan"]["agreement_shield_receipt"][
            "abstract_disagreement_abstained"
        ]
        is True
    ]
    dependency_receipts = [
        row
        for row in agreement_receipts
        if row["abstract_plan"].get("persistent_post_dependency_program_used")
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
    execution_receipts = [
        *first["abstract_execution_receipts"],
        *(
            receipt
            for episode in later
            for receipt in episode["abstract_execution_receipts"]
        ),
    ]
    payload = {
        "schema": "acfqp.generic_persistent_receipted_sequence.v103",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "arm": first["arm"],
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "partial_acquisition_ground_support_labels_paid_once": (
            acquisition_ground_support_labels
        ),
        "first_agreement_shielded_online_episode": copy.deepcopy(first),
        "post_dependency_model_activation_observed": activation_observed,
        "post_dependency_model_activation_local_ground_support_label": activation,
        "post_dependency_model_activation_label_with_right_censoring": right_censored,
        "target_model_activation_ground_support_labels_with_right_censoring": (
            acquisition_ground_support_labels + right_censored
        ),
        "retained_active_post_dependency_acquisition": copy.deepcopy(acquisition),
        "later_persistent_episodes": later,
        "later_agreement_shield_accept_receipt_count": len(agreement_receipts),
        "later_agreement_shield_disagreement_abstention_count": len(
            disagreement_receipts
        ),
        "later_post_dependency_abstract_plan_receipt_count": len(
            dependency_receipts
        ),
        "later_execution_action_matches_abstract_proposal_count": sum(
            episode["execution_action_matches_abstract_proposal_count"]
            for episode in later
        ),
        "all_abstract_execution_receipts": execution_receipts,
        "abstract_execution_receipt_count": len(execution_receipts),
        "every_execution_action_has_content_addressed_receipt": (
            len(execution_receipts)
            == first["execution_steps"]
            + sum(episode["execution_steps"] for episode in later)
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
        "same_agreement_shield_applied_to_prior_and_no_prior_arms": True,
        "abstract_proposal_can_precede_partial_without_agreement": False,
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


run_persistent_receipted_arm_v103 = run_persistent_agreement_shielded_arm_v99


__all__ = ("run_persistent_receipted_arm_v103",)
