"""Amortize target acquisition and exact overlay rows across query episodes."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_applicability_conditioned_planner_v58 import (
    GenericApplicabilityConditionedPlannerV58Error,
    plan_applicability_conditioned_model_v58,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_coordinate_aligned_certificate_planner_v60 import _projection
from acfqp.generic_coordinate_alignment_v60 import compile_coordinate_alignment_v60
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_preloaded_certificate_receding_engine_v74 import (
    run_preloaded_certificate_receding_episode_v74,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericProjectedPersistentSequenceV78Error(ValueError):
    pass


_SEQUENCE_DOMAIN = b"acfqp:generic-projected-persistent-sequence:v78\x00"
_OVERLAY_DOMAIN = b"acfqp:generic-persistent-exact-overlay-epoch:v78\x00"


def _fail(message: str) -> NoReturn:
    raise GenericProjectedPersistentSequenceV78Error(message)


def _group_count(rows: tuple[FlatRawTransitionV4, ...]) -> int:
    return len({(row.pre, row.action.key) for row in rows})


def _row(document: Mapping[str, Any]) -> FlatRawTransitionV4:
    selected = document.get("selected_action")
    if type(selected) is not dict:
        _fail("V78 persisted transition action changed")
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


def _overlay(
    rows: tuple[FlatRawTransitionV4, ...],
    *,
    acquisition_labels: int,
    persisted_certificate_labels: int,
    epoch: int,
) -> dict[str, Any]:
    documents = [row.to_document() for row in rows]
    payload = {
        "schema": "acfqp.generic_persistent_exact_overlay_epoch.v78",
        "overlay_epoch": epoch,
        "acquisition_ground_support_labels_paid_once": acquisition_labels,
        "persisted_certificate_ground_support_labels_paid_once": (
            persisted_certificate_labels
        ),
        "total_unique_ground_support_labels_paid": _group_count(rows),
        "exact_transition_rows": documents,
        "exact_transition_sha256": hashlib.sha256(
            canonical_json_bytes(documents)
        ).hexdigest(),
        "immutable_append_only": True,
        "future_query_safety_authority_claimed": False,
        "query_local_exact_evidence_only": True,
    }
    return {
        **payload,
        "overlay_epoch_id": hashlib.sha256(
            _OVERLAY_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_projected_persistent_sequence_v78(
    adapter: Any,
    target_candidate: PartialFactorCandidateV15,
    acquisition_rows: tuple[FlatRawTransitionV4, ...],
    acquisition_ground_support_labels: int,
    model: Mapping[str, Any],
    applicability_program: Mapping[str, Any],
    *,
    model_source_episode_index: int,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
    maximum_abstract_support_branch_evaluations: int,
    abstract_support_feasible_beam_width: int,
) -> dict[str, Any]:
    if (
        type(target_candidate) is not PartialFactorCandidateV15
        or type(acquisition_rows) is not tuple
        or not acquisition_rows
        or type(acquisition_ground_support_labels) is not int
        or acquisition_ground_support_labels <= 0
        or type(episode_indices) is not tuple
        or not episode_indices
        or len(set(episode_indices)) != len(episode_indices)
        or any(type(value) is not int for value in episode_indices)
    ):
        _fail("V78 persistent sequence inventory changed")
    alignment = compile_coordinate_alignment_v60(
        model,
        applicability_program,
        target_candidate,
        acquisition_rows,
        adapter.catalogue,
    )
    projected_adapter, projected_candidate, projected_rows = _projection(
        adapter,
        target_candidate,
        acquisition_rows,
        model,
        alignment,
    )
    if _group_count(projected_rows) != acquisition_ground_support_labels:
        _fail("V78 acquisition group accounting changed")

    def orderer(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
        try:
            return plan_applicability_conditioned_model_v58(
                model,
                applicability_program,
                projected_candidate,
                projected_adapter.catalogue,
                raw,
                maximum_depth=maximum_abstract_depth,
                maximum_support_branch_evaluations=(
                    maximum_abstract_support_branch_evaluations
                ),
                support_feasible_beam_width=abstract_support_feasible_beam_width,
            )
        except GenericApplicabilityConditionedPlannerV58Error:
            return None

    persistent_rows = projected_rows
    persisted_certificate_labels = 0
    overlay_epochs = [
        _overlay(
            persistent_rows,
            acquisition_labels=acquisition_ground_support_labels,
            persisted_certificate_labels=0,
            epoch=0,
        )
    ]
    transfer_episodes = []
    strict_episodes = []
    for offset, episode_index in enumerate(episode_indices, 1):
        paid_before = _group_count(persistent_rows)
        transfer = run_preloaded_certificate_receding_episode_v74(
            projected_adapter,
            projected_candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=paid_before,
            arm="PROJECTED_PERSISTENT_LOW_LABEL_TRANSFER",
            abstract_orderer=orderer,
            episode_index=episode_index,
            maximum_execution_steps=maximum_execution_steps,
            maximum_incremental_certificate_ground_support_labels=(
                maximum_incremental_certificate_ground_support_labels
            ),
        )
        strict = run_preloaded_certificate_receding_episode_v74(
            projected_adapter,
            projected_candidate,
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
        new_rows = tuple(
            _row(document)
            for document in transfer["raw_incremental_transition_rows"]
        )
        combined = (*persistent_rows, *new_rows)
        unique: dict[tuple[tuple[int, ...], int, tuple[int, ...]], FlatRawTransitionV4] = {}
        for row in combined:
            unique[(row.pre, row.action.key, row.post)] = row
        persistent_rows = tuple(unique[key] for key in sorted(unique))
        incremental = transfer[
            "incremental_certificate_local_ground_support_labels"
        ]
        persisted_certificate_labels += incremental
        cumulative = acquisition_ground_support_labels + persisted_certificate_labels
        if (
            _group_count(persistent_rows) != cumulative
            or transfer["total_target_ground_support_labels"] != cumulative
            or any(
                row["distinction_kind"] != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT"
                for row in transfer["local_distinctions"]
            )
        ):
            _fail("V78 persistent exact-overlay accounting changed")
        overlay = _overlay(
            persistent_rows,
            acquisition_labels=acquisition_ground_support_labels,
            persisted_certificate_labels=persisted_certificate_labels,
            epoch=offset,
        )
        transfer_episodes.append(
            {
                **copy.deepcopy(transfer),
                "preexisting_persistent_exact_support_labels": paid_before,
                "new_certificate_labels_charged_this_episode": incremental,
                "cumulative_unique_target_labels_after_episode": cumulative,
                "resulting_overlay_epoch_id": overlay["overlay_epoch_id"],
            }
        )
        strict_episodes.append(copy.deepcopy(strict))
        overlay_epochs.append(overlay)
    transfer_lifetime = acquisition_ground_support_labels + persisted_certificate_labels
    strict_lifetime = sum(
        row["total_target_ground_support_labels"] for row in strict_episodes
    )
    payload = {
        "schema": "acfqp.generic_projected_persistent_sequence.v78",
        "family": adapter.family,
        "seed": adapter.seed,
        "model_source_episode_index": model_source_episode_index,
        "target_episode_indices": list(episode_indices),
        "source_model_id": model[
            "projected_disagreement_successor_model_id"
        ],
        "source_applicability_program_id": applicability_program[
            "action_applicability_program_id"
        ],
        "target_candidate_id": target_candidate.public_document["candidate_id"],
        "projected_target_candidate_id": projected_candidate.public_document[
            "candidate_id"
        ],
        "coordinate_alignment": copy.deepcopy(alignment),
        "coordinate_alignment_id": alignment["coordinate_alignment_id"],
        "overlay_epochs": overlay_epochs,
        "transfer_episodes": transfer_episodes,
        "strict_cold_direct_episodes": strict_episodes,
        "acquisition_ground_support_labels_paid_once": (
            acquisition_ground_support_labels
        ),
        "persistent_certificate_ground_support_labels_paid_once": (
            persisted_certificate_labels
        ),
        "transfer_lifetime_unique_target_ground_support_labels": transfer_lifetime,
        "strict_cold_direct_lifetime_target_ground_support_labels": strict_lifetime,
        "strict_minus_transfer_lifetime_target_labels": (
            strict_lifetime - transfer_lifetime
        ),
        "lifetime_target_sample_reduction_observed": transfer_lifetime
        < strict_lifetime,
        "acquisition_and_certificate_rows_immutable_and_reused_across_queries": True,
        "every_new_ground_query_followed_a_failed_certificate": True,
        "no_ground_query_repeated_across_transfer_episodes": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "model_alignment_or_applicability_used_as_safety_authority": False,
        "sample_labels_execution_steps_derivation_certificate_and_planning_compute_separate": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "sequence_id": hashlib.sha256(
            _SEQUENCE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_projected_persistent_sequence_v78",)
