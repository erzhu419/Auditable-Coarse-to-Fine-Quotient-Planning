"""Persist a post-coordinate dependency program beside an exact overlay."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_multi_residual_certificate_planner_v26 import (
    run_multi_residual_certificate_episode_v26,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.generic_post_dependency_residual_v97 import (
    plan_post_dependency_abstract_program_v97,
    synthesize_post_dependency_multi_residual_v97,
)
from acfqp.generic_preloaded_certificate_receding_engine_v74 import (
    run_preloaded_certificate_receding_episode_v74,
)
from acfqp.phase3e_ids import canonical_json_bytes


_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-post-dependency-sequence:v97\x00"


class GenericPersistentPostDependencySequenceV97Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPersistentPostDependencySequenceV97Error(message)


def _row(document: Mapping[str, Any]) -> FlatRawTransitionV4:
    selected = document.get("selected_action")
    if type(selected) is not dict:
        _fail("V97 persisted transition action changed")
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


def _certificate_candidate(
    candidate: Any,
    observed_rows: tuple[FlatRawTransitionV4, ...],
) -> PartialFactorCandidateV15:
    if type(candidate) is PartialFactorCandidateV15:
        return candidate
    public = getattr(candidate, "public_document", None)
    layout = getattr(candidate, "layout", None)
    program = getattr(candidate, "program", None)
    assignments = program.get("compiled_assignments") if type(program) is dict else None
    if type(public) is not dict or layout is None or assignments is None:
        _fail("V97 partial candidate cannot enter the exact engine")
    return PartialFactorCandidateV15(
        copy.deepcopy(public), layout, tuple(assignments), observed_rows
    )


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
    dependency_candidate_count = len(
        acquisition["retrospective_post_dependency_candidates"]
    )

    def order(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
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
                "persistent_joint_successor_program_used": True,
                "persistent_post_dependency_program_used": (
                    dependency_candidate_count > 0
                ),
                "post_dependency_candidate_count": dependency_candidate_count,
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
            "schema": "acfqp.generic_persistent_partial_fallback_plan.v97",
            "initial_action_key": actions[0],
            "abstract_support_branch_evaluations": partial.get(
                "projected_planning_compute_events", 0
            ),
            "partial_plan": copy.deepcopy(partial),
            "persistent_post_dependency_program_used": False,
            "persistent_joint_successor_program_used": False,
            "post_dependency_candidate_count": dependency_candidate_count,
            "persistent_partial_fallback_used": True,
            "ground_transition_accessed_during_abstract_search": False,
            "abstract_plan_used_as_safety_authority": False,
        }

    return order


def run_persistent_post_dependency_arm_v97(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    acquisition_ground_support_labels: int,
    *,
    residual_prior_library: Mapping[str, Any] | None,
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
        type(observed_rows) is not tuple
        or not observed_rows
        or type(episode_indices) is not tuple
        or len(episode_indices) < 2
        or len(set(episode_indices)) != len(episode_indices)
        or _group_count(observed_rows) != acquisition_ground_support_labels
    ):
        _fail("V97 persistent dependency arm inventory changed")
    first = run_multi_residual_certificate_episode_v26(
        adapter,
        candidate,
        observed_rows,
        residual_prior_library=residual_prior_library,
        episode_index=episode_indices[0],
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        confidence_denominator=confidence_denominator,
        maximum_joint_support_branch_evaluations=(
            maximum_support_branch_evaluations
        ),
        joint_support_feasible_beam_width=support_feasible_beam_width,
    )
    residual_rows = tuple(_row(row) for row in first["raw_local_transition_rows"])
    evidence = {
        "layout": candidate.public_document["layout"],
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": [row.to_document() for row in residual_rows],
    }
    dependency_acquisition = synthesize_post_dependency_multi_residual_v97(
        evidence,
        first["final_multi_residual_acquisition"],
        structural_prior_library=structural_prior_library,
    )
    if dependency_acquisition[
        "all_residual_targets_have_compilable_proposals"
    ] is not True:
        _fail("V97 post-dependency synthesis left a residual target unmodeled")
    paid_certificate_labels = first["local_ground_support_labels"]
    persistent_rows = _deduplicate((*observed_rows, *residual_rows))
    planning_rows = persistent_rows
    exact_candidate = _certificate_candidate(candidate, observed_rows)
    orderer = _orderer(
        adapter,
        exact_candidate,
        planning_rows,
        dependency_acquisition,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_support_branch_evaluations=maximum_support_branch_evaluations,
        support_feasible_beam_width=support_feasible_beam_width,
    )
    later = []
    for episode_index in episode_indices[1:]:
        episode = run_preloaded_certificate_receding_episode_v74(
            adapter,
            exact_candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=_group_count(persistent_rows),
            arm="PERSISTENT_POST_DEPENDENCY_TRANSFER",
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
    failures = [
        *first["failed_certificates"],
        *(row for episode in later for row in episode["failed_certificates"]),
    ]
    distinctions = [
        *first["local_distinctions"],
        *(row for episode in later for row in episode["local_distinctions"]),
    ]
    dependency_receipts = [
        receipt
        for episode in later
        for receipt in episode["abstract_plan_receipts"]
        if receipt["abstract_plan"].get("persistent_post_dependency_program_used")
        is True
    ]
    joint_receipts = [
        receipt
        for episode in later
        for receipt in episode["abstract_plan_receipts"]
        if receipt["abstract_plan"].get("persistent_joint_successor_program_used")
        is True
    ]
    matches = sum(
        episode["execution_action_matches_abstract_proposal_count"]
        for episode in later
    )
    overlay = [row.to_document() for row in persistent_rows]
    payload = {
        "schema": "acfqp.generic_persistent_post_dependency_sequence.v97",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "arm": (
            "POST_DEPENDENCY_STRUCTURE_META_PRIOR_ON"
            if structural_prior_library is not None
            else "STRICT_NO_POST_DEPENDENCY_STRUCTURE_META_PRIOR"
        ),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "partial_acquisition_ground_support_labels_paid_once": (
            acquisition_ground_support_labels
        ),
        "first_online_multi_residual_episode": copy.deepcopy(first),
        "retained_post_dependency_acquisition": dependency_acquisition,
        "retained_post_dependency_candidate_count": len(
            dependency_acquisition["retrospective_post_dependency_candidates"]
        ),
        "retained_joint_residual_candidate_count": dependency_acquisition[
            "compilable_candidate_count"
        ],
        "later_persistent_episodes": later,
        "persistent_exact_overlay_rows": overlay,
        "persistent_exact_overlay_sha256": hashlib.sha256(
            canonical_json_bytes(overlay)
        ).hexdigest(),
        "persistent_exact_support_group_count": _group_count(persistent_rows),
        "certificate_ground_support_labels_paid_once": paid_certificate_labels,
        "lifetime_target_ground_support_labels": (
            acquisition_ground_support_labels + paid_certificate_labels
        ),
        "later_post_dependency_abstract_plan_receipt_count": len(
            dependency_receipts
        ),
        "later_joint_abstract_plan_receipt_count": len(joint_receipts),
        "later_execution_action_matches_any_abstract_proposal_count": matches,
        "later_query_ground_support_labels": sum(
            episode["new_certificate_labels_charged_this_episode"]
            for episode in later
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
        "post_dependency_program_is_fallible_action_ordering_heuristic": True,
        "persistent_exact_overlay_exclusively_discharges_safety": True,
        "successor_coordinate_dependency_jointly_compiled": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": hashlib.sha256(
            _SEQUENCE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_persistent_post_dependency_arm_v97",)
