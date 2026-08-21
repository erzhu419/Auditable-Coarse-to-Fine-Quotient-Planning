"""Retain branch projections only under an exact derived dependency receipt."""

from __future__ import annotations

import copy
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v117 as domains
from acfqp import generic_incremental_abstract_successor_v113 as successor
from acfqp import generic_incremental_abstract_successor_sequence_v113 as v113
from acfqp import generic_cross_epoch_program_branch_sequence_v116 as previous
from acfqp.generic_incremental_abstract_successor_v113 import (
    IncrementalAbstractSuccessorStateV113,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15


class GenericDependencyDerivedProgramBranchSequenceV117Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericDependencyDerivedProgramBranchSequenceV117Error(message)


def _receipt_payload(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[Any, ...],
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(catalogue) is not tuple
        or not catalogue
    ):
        _fail("V117 branch dependency input changed")
    public = candidate.public_document
    canonical_actions = successor._canonical_actions(  # noqa: SLF001
        candidate, catalogue
    )
    action_rows = [
        {
            "action_key": action.key,
            "canonical_anonymous_fields": list(action.fields),
        }
        for action in canonical_actions
    ]
    if len({row["action_key"] for row in action_rows}) != len(action_rows):
        _fail("V117 branch dependency action keys changed")
    return {
        "schema": "acfqp.program_branch_dependency_receipt.v117",
        "partial_candidate_id": public["candidate_id"],
        "layout_id": public["layout"]["layout_id"],
        "compiled_factor_assignments": copy.deepcopy(
            public["compiled_factor_assignments"]
        ),
        "canonical_action_catalogue": action_rows,
        "successor_operator": "PARTIAL_FACTOR_SUCCESSOR_PROJECTIONS_V15",
        "minimal_semantic_dependencies": [
            "COMPILED_FACTOR_ASSIGNMENTS",
            "CANONICAL_ACTION_FIELDS",
            "PROJECTED_STATE",
            "ACTION_KEY",
        ],
        "excluded_model_epoch_fields": [
            "OBSERVATION_QUOTIENT_GRAPH_ID",
            "RAW_ROW_IDENTITY_SHA256",
            "TERMINAL_PROJECTION_RULE",
        ],
        "dependency_set_derived_from_compiled_operator_arguments": True,
        "model_epoch_identity_used_as_dependency": False,
        "ground_transition_rows_used_as_dependency": False,
        "cache_or_receipt_used_as_safety_authority": False,
    }


def derive_program_branch_dependency_receipt_v117(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[Any, ...],
) -> dict[str, Any]:
    payload = _receipt_payload(candidate, catalogue)
    return {
        **payload,
        "dependency_receipt_id": domains.extension_content_id_v117(
            domains.CONSTRUCTION_K7_PROGRAM_BRANCH_DEPENDENCY_RECEIPT_V117_DOMAIN,
            payload,
        ),
    }


def verify_program_branch_dependency_receipt_v117(
    receipt: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[Any, ...],
) -> dict[str, Any]:
    expected = derive_program_branch_dependency_receipt_v117(candidate, catalogue)
    if type(receipt) is not dict or receipt != expected:
        _fail("V117 branch dependency receipt changed")
    return copy.deepcopy(expected)


def program_branch_cache_retention_decision_v117(
    prior_receipt: Mapping[str, Any] | None,
    current_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if type(current_receipt) is not dict:
        _fail("V117 current dependency receipt changed")
    payload = {
        key: value
        for key, value in current_receipt.items()
        if key != "dependency_receipt_id"
    }
    if current_receipt.get("dependency_receipt_id") != domains.extension_content_id_v117(
        domains.CONSTRUCTION_K7_PROGRAM_BRANCH_DEPENDENCY_RECEIPT_V117_DOMAIN,
        payload,
    ):
        _fail("V117 current dependency receipt identity changed")
    retain = (
        prior_receipt is not None
        and type(prior_receipt) is dict
        and prior_receipt == current_receipt
    )
    return {
        "schema": "acfqp.program_branch_cache_retention_decision.v117",
        "prior_dependency_receipt_id": (
            None if prior_receipt is None else prior_receipt.get("dependency_receipt_id")
        ),
        "current_dependency_receipt_id": current_receipt["dependency_receipt_id"],
        "retain_program_branch_cache": retain,
        "invalidate_program_branch_cache": prior_receipt is not None and not retain,
        "decision_derived_only_from_exact_dependency_receipt_equality": True,
        "model_epoch_identity_used_as_retention_key": False,
        "cache_used_as_safety_authority": False,
    }


def _dependency_derived_orderer(
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
    current = derive_program_branch_dependency_receipt_v117(
        candidate, adapter.catalogue
    )
    prior = stats.get("_program_branch_dependency_receipt")
    decision = program_branch_cache_retention_decision_v117(prior, current)
    if decision["invalidate_program_branch_cache"]:
        stats.setdefault("_program_branch_cache", {}).clear()
    stats["_program_branch_dependency_receipt"] = copy.deepcopy(current)
    return previous._cross_epoch_orderer(  # noqa: SLF001
        adapter,
        candidate,
        state,
        cache,
        entries,
        reverse_index,
        stats,
        maximum_abstract_depth=maximum_abstract_depth,
    )


def _run_dependency_derived_base_sequence(
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
    namespace["_incremental_indexed_orderer"] = _dependency_derived_orderer
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


def run_dependency_derived_program_branch_sequence_v117(
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
    receipt = derive_program_branch_dependency_receipt_v117(
        candidate, adapter.catalogue
    )
    base = _run_dependency_derived_base_sequence(
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
    dependency_derivation_events = len(episode_indices) * (
        len(receipt["compiled_factor_assignments"])
        + len(receipt["canonical_action_catalogue"])
    )
    payload = {
        "schema": "acfqp.generic_dependency_derived_program_branch_sequence.v117",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "program_branch_dependency_receipt": receipt,
        "program_branch_dependency_receipt_id": receipt["dependency_receipt_id"],
        "dependency_derived_program_branch_base_sequence": base,
        "dependency_derived_program_branch_base_sequence_id": base["sequence_id"],
        "dependency_receipt_rederivation_count": len(episode_indices),
        "dependency_derivation_compute_events": dependency_derivation_events,
        "model_epoch_transition_count": len(base["model_epoch_transition_receipts"]),
        "dependency_receipt_stable_across_model_epochs": True,
        "program_branch_cache_retained_only_after_exact_dependency_match": True,
        "program_branch_cache_hit_count": branch_hits,
        "actual_new_abstract_planning_compute_events": base[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_uncached_abstract_planning_compute_events": uncached_compute,
        "planning_compute_events_avoided_against_uncached": uncached_compute
        - base["actual_new_abstract_planning_compute_events"],
        "ground_transition_accessed_during_dependency_derivation": False,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v117(
            domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_SEQUENCE_V117_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "derive_program_branch_dependency_receipt_v117",
    "program_branch_cache_retention_decision_v117",
    "run_dependency_derived_program_branch_sequence_v117",
    "verify_program_branch_dependency_receipt_v117",
)
