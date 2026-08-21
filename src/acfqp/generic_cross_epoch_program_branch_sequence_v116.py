"""Retain factor-program successor projections across model epochs."""

from __future__ import annotations

from types import FunctionType
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v116 as domains
from acfqp import generic_incremental_abstract_successor_sequence_v113 as v113
from acfqp import generic_projected_program_memo_sequence_v115 as previous
from acfqp.generic_incremental_abstract_successor_v113 import (
    IncrementalAbstractSuccessorStateV113,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15


def _cross_epoch_orderer(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    state: IncrementalAbstractSuccessorStateV113,
    cache: dict[tuple[Any, ...], list[dict[str, Any]]],
    entries: dict[str, dict[str, Any]],
    reverse_index: dict[tuple[int, ...], set[str]],
    stats: dict[str, Any],
    *,
    maximum_abstract_depth: int,
):
    prior_state_id = stats.get("_program_cache_successor_state_id")
    if prior_state_id is not None and prior_state_id != state.state_id:
        stats.setdefault("_program_cache", {}).clear()
        stats["_cross_epoch_retained_branch_entry_count"] = (
            stats.get("_cross_epoch_retained_branch_entry_count", 0)
            + len(stats.setdefault("_program_branch_cache", {}))
        )
    stats["_program_cache_successor_state_id"] = state.state_id
    return previous._projected_program_memo_orderer(  # noqa: SLF001
        adapter,
        candidate,
        state,
        cache,
        entries,
        reverse_index,
        stats,
        maximum_abstract_depth=maximum_abstract_depth,
    )


def _run_cross_epoch_base_sequence(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[Any, ...],
    acquisition_ground_support_labels: int,
    *,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    namespace = dict(v113.__dict__)
    namespace["_incremental_indexed_orderer"] = _cross_epoch_orderer
    function = v113.run_incremental_abstract_successor_sequence_v113
    cloned = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    cloned.__kwdefaults__ = function.__kwdefaults__
    return cloned(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_incremental_certificate_ground_support_labels=(
            maximum_incremental_certificate_ground_support_labels
        ),
    )


def run_cross_epoch_program_branch_sequence_v116(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[Any, ...],
    acquisition_ground_support_labels: int,
    *,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    base = _run_cross_epoch_base_sequence(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_incremental_certificate_ground_support_labels=(
            maximum_incremental_certificate_ground_support_labels
        ),
    )
    plans = [
        row["abstract_plan"]
        for episode in base["episodes"]
        for row in episode["abstract_plan_receipts"]
    ]
    branch_hits = sum(
        row.get("embedded_projected_plan", {}).get(
            "projected_branch_cache_hit_count", 0
        )
        for row in plans
    )
    uncached_compute = sum(
        row.get("embedded_projected_plan", {}).get(
            "matched_uncached_projected_planning_compute_events",
            row["abstract_support_branch_evaluations"],
        )
        for row in plans
    )
    payload = {
        "schema": "acfqp.generic_cross_epoch_program_branch_sequence.v116",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "cross_epoch_program_branch_base_sequence": base,
        "cross_epoch_program_branch_base_sequence_id": base["sequence_id"],
        "cross_epoch_program_branch_cache_hit_count": branch_hits,
        "actual_new_abstract_planning_compute_events": base[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_uncached_abstract_planning_compute_events": uncached_compute,
        "planning_compute_events_avoided_against_uncached": uncached_compute
        - base["actual_new_abstract_planning_compute_events"],
        "factor_successor_projection_cache_retained_across_model_epochs": True,
        "whole_program_plan_cache_still_invalidated_on_model_epoch_change": True,
        "factor_successor_projection_independent_of_observation_graph_and_terminal_rule": True,
        "ground_transition_accessed_during_cross_epoch_reuse": False,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_model_or_cache_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v116(
            domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_SEQUENCE_V116_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_cross_epoch_program_branch_sequence_v116",)
