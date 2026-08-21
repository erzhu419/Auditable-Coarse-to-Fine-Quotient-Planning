"""Dependency-derived branch reuse with an explicit same-epoch genesis case.

V115 assumed every quotient-plan cache hit followed an epoch transition.  A
repeated projected state can instead hit while the source quotient graph is
still current.  This additive successor authorizes that zero-transition case
only by exact equality of source, authorized, and current graph identities.
"""

from __future__ import annotations

import copy
import hashlib
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v119 as domains
from acfqp import generic_dependency_derived_program_branch_sequence_v117 as v117
from acfqp import generic_incremental_abstract_successor_sequence_v113 as v113
from acfqp import generic_projected_program_memo_sequence_v115 as v115
from acfqp.generic_incremental_abstract_successor_v113 import (
    IncrementalAbstractSuccessorStateV113,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_quotient_plan_dependency_receipt_v109 import (
    build_quotient_plan_dependency_receipt_v109,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericGenesisAuthorizedProgramBranchSequenceV119Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericGenesisAuthorizedProgramBranchSequenceV119Error(message)


def _genesis_authorized_orderer(
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
    v109 = v115.previous.v110.previous
    model = state.model
    rules = state.terminal_rules
    rule_sha = hashlib.sha256(canonical_json_bytes(list(rules))).hexdigest()
    program_cache = stats.setdefault("_program_cache", {})
    branch_cache = stats.setdefault("_program_branch_cache", {})
    prior_state_id = stats.get("_program_cache_successor_state_id")
    if prior_state_id is not None and prior_state_id != state.state_id:
        program_cache.clear()
        stats["_cross_epoch_retained_branch_entry_count"] = (
            stats.get("_cross_epoch_retained_branch_entry_count", 0)
            + len(branch_cache)
        )
    stats["_program_cache_successor_state_id"] = state.state_id

    current_receipt = v117.derive_program_branch_dependency_receipt_v117(
        candidate, adapter.catalogue
    )
    prior_receipt = stats.get("_program_branch_dependency_receipt")
    decision = v117.program_branch_cache_retention_decision_v117(
        prior_receipt, current_receipt
    )
    if decision["invalidate_program_branch_cache"]:
        branch_cache.clear()
    stats["_program_branch_dependency_receipt"] = copy.deepcopy(current_receipt)

    def order(
        raw: tuple[int, ...],
        legal: tuple[int, ...],
        legality_support_source: str,
        legality_failure_index: int | None,
    ) -> Mapping[str, Any] | None:
        stats["calls"] += 1
        key = v109._stable_key(candidate, raw, legal)  # noqa: SLF001
        cached = cache.get(key, [])
        if cached:
            entry = cached[0]
            if entry["authorized_quotient_graph_id"] != model["quotient_graph_id"]:
                _fail("V119 graph cache entry lacks current authorization")
            stats["hits"] += 1
            chain = copy.deepcopy(entry["epoch_authorization_chain"])
            if not chain:
                if (
                    entry["dependency"]["source_quotient_graph_id"]
                    != model["quotient_graph_id"]
                    or entry["source_successor_state_id"] != state.state_id
                ):
                    _fail("V119 zero-transition cache hit lacks genesis identity")
                stats["_same_epoch_genesis_authorized_hit_count"] = (
                    stats.get("_same_epoch_genesis_authorized_hit_count", 0) + 1
                )
                return v115._memoized_program_plan(  # noqa: SLF001
                    source_plan=entry["source_plan"],
                    source_successor_state_id=entry["source_successor_state_id"],
                    current_successor_state_id=state.state_id,
                    quotient_graph_id=model["quotient_graph_id"],
                    terminal_rule_sha256=rule_sha,
                    legal=legal,
                    legality_support_source=legality_support_source,
                    legality_failure_index=legality_failure_index,
                )
            validation = {
                "dependency_receipt_id": entry["dependency"]["dependency_receipt_id"],
                "source_quotient_graph_id": entry["dependency"][
                    "source_quotient_graph_id"
                ],
                "current_quotient_graph_id": model["quotient_graph_id"],
                "dependency_validation_check_count": 0,
                "source_action_path_remains_valid_under_current_dependency_slice": True,
                "full_current_quotient_graph_identity_required": False,
                "epoch_transition_receipt_id": chain[-1][
                    "epoch_transition_receipt_id"
                ],
                "epoch_authorization_chain": chain,
                "per_hit_dependency_rescan_performed": False,
            }
            return v109._revalidated_plan(  # noqa: SLF001
                source_plan=entry["source_plan"],
                dependency_receipt=entry["dependency"],
                validation=validation,
                current_model=model,
                legal=legal,
                legality_support_source=legality_support_source,
                legality_failure_index=legality_failure_index,
            )
        program_entry = program_cache.get(key)
        if program_entry is not None:
            if (
                program_entry["successor_state_id"] != state.state_id
                or program_entry["terminal_rule_sha256"] != rule_sha
            ):
                _fail("V119 program memo lacks exact compiled-state authorization")
            stats["hits"] += 1
            return v115._memoized_program_plan(  # noqa: SLF001
                source_plan=program_entry["source_plan"],
                source_successor_state_id=program_entry["successor_state_id"],
                current_successor_state_id=state.state_id,
                quotient_graph_id=model["quotient_graph_id"],
                terminal_rule_sha256=rule_sha,
                legal=legal,
                legality_support_source=legality_support_source,
                legality_failure_index=legality_failure_index,
            )
        stats["misses"] += 1
        try:
            plan = v115._plan_with_branch_cache(  # noqa: SLF001
                state,
                candidate,
                adapter.catalogue,
                raw,
                legal,
                branch_cache,
                legality_support_source=legality_support_source,
                legality_failure_index=legality_failure_index,
                maximum_depth=maximum_abstract_depth,
            )
        except Exception as error:
            if not error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            return None
        stats["actual_new_compute_events"] += plan[
            "abstract_support_branch_evaluations"
        ]
        if plan["planning_source"] == "OBSERVATION_QUOTIENT_GRAPH":
            dependency = build_quotient_plan_dependency_receipt_v109(
                source_model=model,
                source_plan=plan,
                initial_projected_state=v109._projected_state(candidate, raw),  # noqa: SLF001
            )
            identity = dependency["dependency_receipt_id"]
            entry = {
                "source_plan": copy.deepcopy(plan),
                "dependency": dependency,
                "authorized_quotient_graph_id": model["quotient_graph_id"],
                "source_successor_state_id": state.state_id,
                "epoch_authorization_chain": [],
            }
            cache.setdefault(key, []).append(entry)
            entries[identity] = entry
            for row in dependency["ordered_bfs_dependency_rows"]:
                reverse_index[tuple(row["projected_state"])].add(identity)
        elif plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK":
            program_cache[key] = {
                "source_plan": copy.deepcopy(plan),
                "successor_state_id": state.state_id,
                "terminal_rule_sha256": rule_sha,
            }
        return copy.deepcopy(plan)

    return order


def _run_base(
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
    namespace["_incremental_indexed_orderer"] = _genesis_authorized_orderer
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


def run_genesis_authorized_program_branch_sequence_v119(
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
    receipt = v117.derive_program_branch_dependency_receipt_v117(
        candidate, adapter.catalogue
    )
    base = _run_base(
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
    uncached_compute = sum(
        row.get("embedded_projected_plan", {}).get(
            "matched_uncached_projected_planning_compute_events",
            row["abstract_support_branch_evaluations"],
        )
        for row in plans
    )
    branch_hits = sum(
        row.get("embedded_projected_plan", {}).get(
            "projected_branch_cache_hit_count", 0
        )
        for row in plans
    )
    genesis_hits = sum(
        row["planning_source"] == "COMPILED_FACTOR_PROGRAM_MEMOIZED"
        and row.get("source_successor_state_id")
        == row.get("current_successor_state_id")
        for row in plans
    )
    dependency_compute = len(episode_indices) * (
        len(receipt["compiled_factor_assignments"])
        + len(receipt["canonical_action_catalogue"])
    )
    payload = {
        "schema": "acfqp.generic_genesis_authorized_program_branch_sequence.v119",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "program_branch_dependency_receipt": receipt,
        "program_branch_dependency_receipt_id": receipt["dependency_receipt_id"],
        "genesis_authorized_base_sequence": base,
        "genesis_authorized_base_sequence_id": base["sequence_id"],
        "dependency_receipt_rederivation_count": len(episode_indices),
        "dependency_derivation_compute_events": dependency_compute,
        "same_epoch_genesis_authorized_cache_hit_count": genesis_hits,
        "program_branch_cache_hit_count": branch_hits,
        "actual_new_abstract_planning_compute_events": base[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_uncached_abstract_planning_compute_events": uncached_compute,
        "planning_compute_events_avoided_against_uncached": uncached_compute
        - base["actual_new_abstract_planning_compute_events"],
        "zero_transition_reuse_requires_source_authorized_and_current_graph_identity": True,
        "cross_epoch_reuse_requires_epoch_authorization_chain": True,
        "dependency_receipt_stable_across_model_epochs": True,
        "ground_transition_accessed_during_dependency_derivation": False,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v119(
            domains.CONSTRUCTION_K7_GENESIS_AUTHORIZED_BRANCH_SEQUENCE_V119_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_genesis_authorized_program_branch_sequence_v119",)
