"""Online certificate planner driven by a compiled partial+residual model.

The combined V22 model supplies a multi-step abstract first action whenever a
currently calibrated action-conditioned residual proposal exists.  It remains
proposal-only: every unseen legality or transition support first produces a
failed certificate, then enters an occurrence-local exact overlay.  The exact
overlay alone closes the recursive all-ground-branch safety proof.
"""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp.generic_adaptive_residual_factor_acquisition_v19 import (
    GenericAdaptiveResidualFactorAcquisitionV19Error,
    acquire_adaptive_residual_factor_v19,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.generic_partial_residual_abstract_planner_v22 import (
    GenericPartialResidualAbstractPlannerV22Error,
    plan_partial_residual_abstract_program_v22,
)
from acfqp.generic_total_adaptive_residual_acquisition_v20 import (
    acquire_total_adaptive_residual_factor_v20,
    replay_total_adaptive_residual_factor_v20,
)


class GenericCombinedModelCertificatePlannerV23Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCombinedModelCertificatePlannerV23Error(message)


def run_combined_model_certificate_episode_v23(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    residual_prior_library: Mapping[str, Any] | None,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    confidence_denominator: int = 64,
    maximum_combined_support_branch_evaluations: int = 100_000,
    combined_support_feasible_beam_width: int = 32,
) -> dict[str, Any]:
    if maximum_abstract_depth <= 0 or maximum_execution_steps <= 0:
        _fail("V23 planning caps changed")
    candidate_document = candidate.public_document
    legal_by_raw: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in observed_rows:
        legal_by_raw[row.pre] = row.legal_before
        legal_by_raw[row.post] = row.legal_after
    transition_cache: dict[tuple[Any, int], tuple[Any, ...]] = {}
    policy: dict[Any, int] = {}
    visiting: set[Any] = set()
    failed_certificates: list[dict[str, Any]] = []
    distinctions: list[dict[str, Any]] = []
    local_rows: list[FlatRawTransitionV4] = []
    local_labels = 0
    partial_planning_compute = 0
    partial_plan_attempts = 0
    residual_synthesis_attempts = 0
    residual_candidate: dict[str, Any] | None = None
    residual_acquisition: dict[str, Any] | None = None
    residual_activations: list[dict[str, Any]] = []
    residual_invalidations = 0
    combined_attempts = 0
    combined_successes = 0
    combined_compute = 0
    combined_robust_closures = 0
    combined_resource_truncations = 0
    combined_plan_cache: dict[tuple[tuple[int, ...], str], dict[str, Any] | None] = {}

    def evidence() -> dict[str, Any]:
        return {
            "layout": candidate_document["layout"],
            "unknown_residual_target_columns": candidate_document[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": [row.to_document() for row in local_rows],
        }

    def update_residual() -> None:
        nonlocal residual_synthesis_attempts, residual_candidate
        nonlocal residual_acquisition, residual_invalidations
        if not local_rows:
            return
        residual_synthesis_attempts += 1
        before = None if residual_candidate is None else residual_candidate["candidate_id"]
        try:
            acquisition = acquire_adaptive_residual_factor_v19(
                evidence(),
                prior_library=residual_prior_library,
                confidence_denominator=confidence_denominator,
            )
        except GenericAdaptiveResidualFactorAcquisitionV19Error:
            if before is not None:
                residual_invalidations += 1
            residual_candidate = None
            residual_acquisition = None
            return
        residual_acquisition = acquisition
        proposed = acquisition["candidate"]
        residual_candidate = (
            proposed
            if type(proposed.get("action_field_binding")) is int
            and proposed.get("predictive_support_excess") == 0
            else None
        )
        if residual_candidate is None:
            if before is not None:
                residual_invalidations += 1
            return
        after = residual_candidate["candidate_id"]
        if before != after:
            combined_plan_cache.clear()
            residual_activations.append(
                {
                    "local_transition_query_count": len(transition_cache),
                    "candidate_id": after,
                    "acquisition_id": acquisition["acquisition_id"],
                }
            )

    def failure(kind: str, state: Any, key: int | None) -> int:
        index = len(failed_certificates)
        failed_certificates.append(
            {
                "failure_index": index,
                "failure_kind": kind,
                "raw_state": list(adapter.encode(state)),
                "action_key": key,
                "ground_query_performed_before_failure": False,
            }
        )
        return index

    def partial_preferred(raw: tuple[int, ...]) -> list[int]:
        nonlocal partial_plan_attempts, partial_planning_compute
        partial_plan_attempts += 1
        try:
            plan = plan_partial_factor_observation_graph_v15(
                candidate, observed_rows, adapter.catalogue, raw
            )
            partial_planning_compute += plan["projected_planning_compute_events"]
            return plan["action_keys"][:1]
        except Exception:
            try:
                plan = plan_partial_factor_program_v15(
                    candidate,
                    observed_rows,
                    adapter.catalogue,
                    raw,
                    maximum_depth=maximum_abstract_depth,
                )
                partial_planning_compute += plan["projected_planning_compute_events"]
                return plan["action_keys"][:1]
            except Exception:
                return []

    def combined_preferred(raw: tuple[int, ...]) -> list[int]:
        nonlocal combined_attempts, combined_successes, combined_compute
        nonlocal combined_robust_closures, combined_resource_truncations
        if residual_candidate is None:
            return []
        cache_key = (raw, residual_candidate["candidate_id"])
        if cache_key in combined_plan_cache:
            cached = combined_plan_cache[cache_key]
            return [] if cached is None else [cached["initial_action_key"]]
        combined_attempts += 1
        try:
            plan = plan_partial_residual_abstract_program_v22(
                candidate,
                observed_rows,
                adapter.catalogue,
                raw,
                residual_candidate,
                maximum_depth=maximum_abstract_depth,
                maximum_support_branch_evaluations=(
                    maximum_combined_support_branch_evaluations
                ),
                support_feasible_beam_width=combined_support_feasible_beam_width,
            )
        except GenericPartialResidualAbstractPlannerV22Error:
            combined_plan_cache[cache_key] = None
            return []
        combined_plan_cache[cache_key] = plan
        combined_successes += 1
        combined_compute += plan["abstract_support_branch_evaluations"]
        combined_robust_closures += plan["robust_all_modeled_branches_closed"] is True
        combined_resource_truncations += plan["robust_search_resource_cap_reached"] is True
        return [plan["initial_action_key"]]

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal local_labels
        raw = adapter.encode(state)
        legal = legal_by_raw.get(raw)
        if legal is None:
            index = failure("MISSING_QUERY_LOCAL_LEGALITY_SUPPORT", state, None)
            legal = tuple(adapter.action_key(action) for action in adapter.actions(state))
            legal_by_raw[raw] = legal
            local_labels += 1
            distinctions.append(
                {
                    "failure_index": index,
                    "distinction_kind": "QUERY_LOCAL_LEGAL_ACTION_SET",
                    "raw_state": list(raw),
                    "legal_action_keys": list(legal),
                    "ground_support_labels": 1,
                    "query_after_failed_certificate": True,
                }
            )
        combined = combined_preferred(raw)
        partial = partial_preferred(raw)
        ordered = []
        for key in (*combined, *partial, *legal):
            if key in legal and key not in ordered:
                ordered.append(key)
        return tuple(ordered)

    def query(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal local_labels
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        raw = adapter.encode(state)
        index = failure(
            "UNKNOWN_RESIDUAL_PREVENTS_ALL_BRANCH_SAFETY_PROOF", state, key
        )
        outcomes = tuple(adapter.kernel.step(state, adapter.action(key)))
        successors = tuple(outcome.next_state for outcome in outcomes)
        batch = []
        for successor in successors:
            raw_successor = adapter.encode(successor)
            legal_after = tuple(
                adapter.action_key(action) for action in adapter.actions(successor)
            )
            legal_by_raw[raw_successor] = legal_after
            batch.append(
                FlatRawTransitionV4(
                    0,
                    len(observed_rows) + len(local_rows) + len(batch),
                    raw,
                    legal_by_raw[raw],
                    adapter.catalogue[key],
                    raw_successor,
                    legal_after,
                    None if legal_after else adapter.success(successor),
                )
            )
        local_rows.extend(batch)
        local_labels += 1
        transition_cache[pair] = successors
        distinctions.append(
            {
                "failure_index": index,
                "distinction_kind": "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT",
                "raw_state": list(raw),
                "action_key": key,
                "raw_transition_rows": [row.to_document() for row in batch],
                "ground_support_labels": 1,
                "query_after_failed_certificate": True,
            }
        )
        update_residual()
        return successors

    def solve(state: Any) -> bool:
        if adapter.success(state):
            return True
        if not adapter.active(state) or state in visiting:
            return False
        visiting.add(state)
        for key in ordered_actions(state):
            if all(solve(successor) for successor in query(state, key)):
                policy[state] = key
                visiting.remove(state)
                return True
        visiting.remove(state)
        return False

    state = adapter.initial()
    if not solve(state):
        _fail("V23 exact query-local proof found no policy")
    action_keys = []
    outcome_tapes = []
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in policy and not solve(state):
            _fail("V23 receding exact query-local proof did not close")
        key = policy[state]
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V23 execution crossed its cap or terminated outside success")
    final_acquisition = acquire_total_adaptive_residual_factor_v20(
        evidence(),
        prior_library=residual_prior_library,
        confidence_denominator=confidence_denominator,
    )
    final_replay = replay_total_adaptive_residual_factor_v20(
        final_acquisition, evidence()
    )
    if local_labels != sum(row["ground_support_labels"] for row in distinctions):
        _fail("V23 local-label accounting changed")
    if len(failed_certificates) != len(distinctions):
        _fail("V23 certificate/distinction pairing changed")
    return {
        "schema": "acfqp.generic_combined_model_certificate_episode.v23",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "arm": (
            "RESIDUAL_FACTOR_PRIOR_ON"
            if residual_prior_library is not None
            else "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
        ),
        "partial_candidate_id": candidate_document["candidate_id"],
        "action_keys": action_keys,
        "outcome_tape_sha256": outcome_tapes,
        "execution_steps": len(action_keys),
        "local_ground_support_labels": local_labels,
        "queried_state_action_count": len(transition_cache),
        "partial_plan_attempt_count": partial_plan_attempts,
        "partial_planning_compute_events": partial_planning_compute,
        "residual_synthesis_attempt_count": residual_synthesis_attempts,
        "residual_proposal_activations": residual_activations,
        "residual_proposal_invalidation_count": residual_invalidations,
        "combined_abstract_plan_attempt_count": combined_attempts,
        "combined_abstract_plan_success_count": combined_successes,
        "combined_abstract_support_branch_evaluations": combined_compute,
        "combined_abstract_robust_closure_count": combined_robust_closures,
        "combined_abstract_robust_resource_truncation_count": (
            combined_resource_truncations
        ),
        "final_total_residual_acquisition": final_acquisition,
        "final_total_residual_replay": final_replay,
        "failed_certificates": failed_certificates,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "combined_partial_residual_model_used_for_multistep_abstract_search": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "combined_abstract_plan_used_as_safety_authority": False,
        "complete_residual_world_model_synthesized": False,
        "success": True,
    }


__all__ = ("run_combined_model_certificate_episode_v23",)
