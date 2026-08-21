"""Persist a jointly compiled residual proposal beside exact query evidence."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_multi_residual_abstract_planner_v25 import (
    plan_multi_residual_abstract_program_v25,
)
from acfqp.generic_multi_residual_acquisition_v24 import (
    acquire_multi_residual_factors_v24,
)
from acfqp.generic_multi_residual_certificate_planner_v26 import (
    run_multi_residual_certificate_episode_v26,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.generic_preloaded_certificate_receding_engine_v74 import (
    run_preloaded_certificate_receding_episode_v74,
)
from acfqp.phase3e_ids import canonical_json_bytes


_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-multi-residual-sequence:v96\x00"


class GenericPersistentMultiResidualSequenceV96Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPersistentMultiResidualSequenceV96Error(message)


def _row(document: Mapping[str, Any]) -> FlatRawTransitionV4:
    selected = document.get("selected_action")
    if type(selected) is not dict:
        _fail("V96 persisted transition action changed")
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
    assignments = (
        program.get("compiled_assignments") if type(program) is dict else None
    )
    if (
        type(public) is not dict
        or type(public.get("candidate_id")) is not str
        or assignments is None
    ):
        _fail("V96 no-prior candidate cannot enter the exact engine")
    return PartialFactorCandidateV15(
        copy.deepcopy(public), layout, tuple(assignments), observed_rows
    )


def _deduplicate(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[FlatRawTransitionV4, ...]:
    unique: dict[
        tuple[tuple[int, ...], int, tuple[int, ...]], FlatRawTransitionV4
    ] = {}
    for row in rows:
        unique[(row.pre, row.action.key, row.post)] = row
    return tuple(unique[key] for key in sorted(unique))


def _prefix_by_query_count(
    rows: tuple[FlatRawTransitionV4, ...], count: int
) -> tuple[FlatRawTransitionV4, ...]:
    if type(count) is not int or count <= 0:
        _fail("V96 activation query count changed")
    seen = set()
    result = []
    for row in rows:
        key = (row.pre, row.action.key)
        if key not in seen:
            if len(seen) == count:
                break
            seen.add(key)
        result.append(row)
    if len(seen) != count:
        _fail("V96 activation prefix did not replay")
    return tuple(result)


def _retained_joint_acquisition(
    first: Mapping[str, Any],
    candidate: Any,
    residual_prior_library: Mapping[str, Any] | None,
    confidence_denominator: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    activations = [
        row
        for row in first["multi_residual_proposal_activations"]
        if row["proposal_count"] >= 2
    ]
    if not activations:
        return None, None
    activation = activations[-1]
    all_rows = tuple(_row(row) for row in first["raw_local_transition_rows"])
    prefix = _prefix_by_query_count(
        all_rows, activation["local_transition_query_count"]
    )
    evidence = {
        "layout": candidate.public_document["layout"],
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": [row.to_document() for row in prefix],
    }
    acquisition = acquire_multi_residual_factors_v24(
        evidence,
        prior_library=residual_prior_library,
        confidence_denominator=confidence_denominator,
    )
    if (
        acquisition["multi_residual_acquisition_id"]
        != activation["multi_residual_acquisition_id"]
        or [row["candidate_id"] for row in acquisition["compilable_candidates"]]
        != activation["candidate_ids"]
        or acquisition["compilable_target_columns"]
        != activation["target_columns"]
        or len(acquisition["compilable_candidates"]) < 2
    ):
        _fail("V96 retained joint acquisition did not replay its activation")
    return acquisition, copy.deepcopy(activation)


def _abstract_orderer(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    retained: Mapping[str, Any] | None,
    *,
    maximum_abstract_depth: int,
    maximum_joint_support_branch_evaluations: int,
    joint_support_feasible_beam_width: int,
):
    def order(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
        if retained is not None:
            try:
                plan = plan_multi_residual_abstract_program_v25(
                    candidate,
                    observed_rows,
                    adapter.catalogue,
                    raw,
                    retained,
                    maximum_depth=maximum_abstract_depth,
                    maximum_support_branch_evaluations=(
                        maximum_joint_support_branch_evaluations
                    ),
                    support_feasible_beam_width=(
                        joint_support_feasible_beam_width
                    ),
                )
            except Exception as error:
                if not error.__class__.__module__.startswith("acfqp.generic_"):
                    raise
            else:
                return {
                    **copy.deepcopy(plan),
                    "persistent_joint_multi_residual_proposal_used": True,
                    "persistent_partial_fallback_used": False,
                }
        try:
            partial = plan_partial_factor_observation_graph_v15(
                candidate, observed_rows, adapter.catalogue, raw
            )
        except Exception as first_error:
            if not first_error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            try:
                partial = plan_partial_factor_program_v15(
                    candidate,
                    observed_rows,
                    adapter.catalogue,
                    raw,
                    maximum_depth=maximum_abstract_depth,
                )
            except Exception as second_error:
                if not second_error.__class__.__module__.startswith(
                    "acfqp.generic_"
                ):
                    raise
                return None
        actions = partial.get("action_keys")
        if type(actions) is not list or not actions:
            return None
        return {
            "schema": "acfqp.generic_persistent_partial_fallback_plan.v96",
            "initial_action_key": actions[0],
            "abstract_support_branch_evaluations": partial.get(
                "projected_planning_compute_events", 0
            ),
            "partial_plan": copy.deepcopy(partial),
            "persistent_joint_multi_residual_proposal_used": False,
            "persistent_partial_fallback_used": True,
            "ground_transition_accessed_during_abstract_search": False,
            "abstract_plan_used_as_safety_authority": False,
        }

    return order


def run_persistent_multi_residual_arm_v96(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    acquisition_ground_support_labels: int,
    *,
    residual_prior_library: Mapping[str, Any] | None,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    confidence_denominator: int,
    maximum_joint_support_branch_evaluations: int,
    joint_support_feasible_beam_width: int,
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
        _fail("V96 persistent multi-residual arm inventory changed")
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
            maximum_joint_support_branch_evaluations
        ),
        joint_support_feasible_beam_width=joint_support_feasible_beam_width,
    )
    retained, activation = _retained_joint_acquisition(
        first, candidate, residual_prior_library, confidence_denominator
    )
    residual_rows = tuple(
        _row(document) for document in first["raw_local_transition_rows"]
    )
    paid_certificate_labels = first["local_ground_support_labels"]
    persistent_rows = _deduplicate((*observed_rows, *residual_rows))
    exact_candidate = _certificate_candidate(candidate, observed_rows)
    later = []
    orderer = _abstract_orderer(
        adapter,
        candidate,
        observed_rows,
        retained,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_joint_support_branch_evaluations=(
            maximum_joint_support_branch_evaluations
        ),
        joint_support_feasible_beam_width=joint_support_feasible_beam_width,
    )
    for episode_index in episode_indices[1:]:
        episode = run_preloaded_certificate_receding_episode_v74(
            adapter,
            exact_candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=_group_count(
                persistent_rows
            ),
            arm="PERSISTENT_JOINT_MULTI_RESIDUAL_TRANSFER",
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
    all_failures = [
        *first["failed_certificates"],
        *(failure for episode in later for failure in episode["failed_certificates"]),
    ]
    all_distinctions = [
        *first["local_distinctions"],
        *(row for episode in later for row in episode["local_distinctions"]),
    ]
    lifetime = acquisition_ground_support_labels + paid_certificate_labels
    joint_receipts = [
        receipt
        for episode in later
        for receipt in episode["abstract_plan_receipts"]
        if receipt["abstract_plan"].get(
            "persistent_joint_multi_residual_proposal_used"
        )
        is True
    ]
    # The per-step match vector does not retain plan kind.  Count joint-plan
    # use and total executed proposal matches separately and never promote the
    # heuristic to certificate authority.
    total_matches = sum(
        episode["execution_action_matches_abstract_proposal_count"]
        for episode in later
    )
    overlay_documents = [row.to_document() for row in persistent_rows]
    payload = {
        "schema": "acfqp.generic_persistent_multi_residual_sequence.v96",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "arm": (
            "RESIDUAL_FACTOR_META_PRIOR_ON"
            if residual_prior_library is not None
            else "STRICT_NO_RESIDUAL_FACTOR_META_PRIOR"
        ),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "partial_acquisition_ground_support_labels_paid_once": (
            acquisition_ground_support_labels
        ),
        "first_online_multi_residual_episode": copy.deepcopy(first),
        "retained_joint_activation": activation,
        "retained_joint_multi_residual_acquisition": copy.deepcopy(retained),
        "later_persistent_episodes": later,
        "persistent_exact_overlay_rows": overlay_documents,
        "persistent_exact_overlay_sha256": hashlib.sha256(
            canonical_json_bytes(overlay_documents)
        ).hexdigest(),
        "persistent_exact_support_group_count": _group_count(persistent_rows),
        "certificate_ground_support_labels_paid_once": paid_certificate_labels,
        "lifetime_target_ground_support_labels": lifetime,
        "retained_joint_proposal_count": (
            0 if retained is None else len(retained["compilable_candidates"])
        ),
        "later_joint_abstract_plan_receipt_count": len(joint_receipts),
        "later_execution_action_matches_any_abstract_proposal_count": total_matches,
        "later_joint_match_lower_bound": min(total_matches, len(joint_receipts)),
        "all_failed_certificates": all_failures,
        "all_local_distinctions": all_distinctions,
        "every_new_ground_query_followed_a_failed_certificate": all(
            row.get("ground_query_performed_before_failure") is False
            for row in all_failures
        )
        and all(
            row.get("query_after_failed_certificate") is True
            for row in all_distinctions
        ),
        "later_query_ground_support_labels": sum(
            episode["new_certificate_labels_charged_this_episode"]
            for episode in later
        ),
        "retained_joint_model_is_fallible_action_ordering_heuristic": True,
        "persistent_exact_overlay_exclusively_discharges_safety": True,
        "multiple_residual_proposals_jointly_compiled_into_one_abstract_successor": (
            retained is not None and len(retained["compilable_candidates"]) >= 2
        ),
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": hashlib.sha256(
            _SEQUENCE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_strict_cold_direct_sequence_v96(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    *,
    episode_indices: tuple[int, ...],
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    episodes = [
        run_preloaded_certificate_receding_episode_v74(
            adapter,
            candidate,
            (),
            preloaded_acquisition_ground_support_labels=0,
            arm="STRICT_COLD_DIRECT_GROUND",
            abstract_orderer=None,
            episode_index=episode_index,
            maximum_execution_steps=maximum_execution_steps,
            maximum_incremental_certificate_ground_support_labels=(
                maximum_incremental_certificate_ground_support_labels
            ),
        )
        for episode_index in episode_indices
    ]
    return {
        "schema": "acfqp.generic_strict_cold_direct_sequence.v96",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "episodes": episodes,
        "lifetime_target_ground_support_labels": sum(
            episode["total_target_ground_support_labels"]
            for episode in episodes
        ),
        "abstract_planning_compute_events": 0,
        "free_target_rows_received": False,
    }


__all__ = (
    "run_persistent_multi_residual_arm_v96",
    "run_strict_cold_direct_sequence_v96",
)
