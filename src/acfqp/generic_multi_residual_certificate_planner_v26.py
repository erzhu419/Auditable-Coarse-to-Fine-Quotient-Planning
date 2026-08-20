"""Certificate-local planning with a jointly compiled multi-residual model.

All residual targets reuse one physical query pool.  Whenever at least two
calibrated proposals are compilable, V25 proposes the next abstract action.
The proposal never discharges safety: an unseen state-action support first
fails certification, is queried exactly once, enters an occurrence-local
overlay, and triggers synthesis plus replanning.
"""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_multi_residual_abstract_planner_v25 import (
    GenericMultiResidualAbstractPlannerV25Error,
    plan_multi_residual_abstract_program_v25,
)
from acfqp.generic_multi_residual_acquisition_v24 import (
    GenericMultiResidualAcquisitionV24Error,
    acquire_multi_residual_factors_v24,
    replay_multi_residual_factors_v24,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)


class GenericMultiResidualCertificatePlannerV26Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericMultiResidualCertificatePlannerV26Error(message)


def run_multi_residual_certificate_episode_v26(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    residual_prior_library: Mapping[str, Any] | None,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    confidence_denominator: int = 64,
    maximum_joint_support_branch_evaluations: int = 1_000_000,
    joint_support_feasible_beam_width: int = 16,
) -> dict[str, Any]:
    if maximum_abstract_depth <= 0 or maximum_execution_steps <= 0:
        _fail("V26 planning caps changed")
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
    multi_synthesis_attempts = 0
    multi_acquisition: dict[str, Any] | None = None
    multi_activations: list[dict[str, Any]] = []
    multi_invalidations = 0
    joint_attempts = 0
    joint_successes = 0
    joint_compute = 0
    joint_robust_closures = 0
    joint_resource_truncations = 0
    maximum_compilable_proposal_count = 0
    joint_plan_cache: dict[tuple[tuple[int, ...], str], dict[str, Any] | None] = {}

    def evidence() -> dict[str, Any]:
        return {
            "layout": candidate_document["layout"],
            "unknown_residual_target_columns": candidate_document[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": [row.to_document() for row in local_rows],
        }

    def update_multi_residual() -> None:
        nonlocal multi_synthesis_attempts, multi_acquisition, multi_invalidations
        nonlocal maximum_compilable_proposal_count
        if not local_rows:
            return
        multi_synthesis_attempts += 1
        before = (
            None
            if multi_acquisition is None
            else tuple(
                row["candidate_id"]
                for row in multi_acquisition["compilable_candidates"]
            )
        )
        try:
            acquisition = acquire_multi_residual_factors_v24(
                evidence(),
                prior_library=residual_prior_library,
                confidence_denominator=confidence_denominator,
            )
        except GenericMultiResidualAcquisitionV24Error:
            if before:
                multi_invalidations += 1
            multi_acquisition = None
            return
        after = tuple(
            row["candidate_id"] for row in acquisition["compilable_candidates"]
        )
        maximum_compilable_proposal_count = max(
            maximum_compilable_proposal_count, len(after)
        )
        multi_acquisition = acquisition if len(after) >= 2 else None
        if len(after) < 2:
            if before:
                multi_invalidations += 1
            return
        if before != after:
            joint_plan_cache.clear()
            multi_activations.append(
                {
                    "local_transition_query_count": len(transition_cache),
                    "multi_residual_acquisition_id": acquisition[
                        "multi_residual_acquisition_id"
                    ],
                    "candidate_ids": list(after),
                    "target_columns": acquisition["compilable_target_columns"],
                    "proposal_count": len(after),
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

    def joint_preferred(raw: tuple[int, ...]) -> list[int]:
        nonlocal joint_attempts, joint_successes, joint_compute
        nonlocal joint_robust_closures, joint_resource_truncations
        if multi_acquisition is None:
            return []
        cache_key = (raw, multi_acquisition["multi_residual_acquisition_id"])
        if cache_key in joint_plan_cache:
            cached = joint_plan_cache[cache_key]
            return [] if cached is None else [cached["initial_action_key"]]
        joint_attempts += 1
        try:
            plan = plan_multi_residual_abstract_program_v25(
                candidate,
                observed_rows,
                adapter.catalogue,
                raw,
                multi_acquisition,
                maximum_depth=maximum_abstract_depth,
                maximum_support_branch_evaluations=(
                    maximum_joint_support_branch_evaluations
                ),
                support_feasible_beam_width=joint_support_feasible_beam_width,
            )
        except GenericMultiResidualAbstractPlannerV25Error:
            joint_plan_cache[cache_key] = None
            return []
        joint_plan_cache[cache_key] = plan
        joint_successes += 1
        joint_compute += plan["abstract_support_branch_evaluations"]
        joint_robust_closures += plan["robust_all_modeled_branches_closed"] is True
        joint_resource_truncations += plan["robust_search_resource_cap_reached"] is True
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
        joint = joint_preferred(raw)
        partial = partial_preferred(raw)
        ordered = []
        for key in (*joint, *partial, *legal):
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
        update_multi_residual()
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
        _fail("V26 exact query-local proof found no policy")
    action_keys = []
    outcome_tapes = []
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in policy and not solve(state):
            _fail("V26 receding exact query-local proof did not close")
        key = policy[state]
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V26 execution crossed its cap or terminated outside success")
    final_acquisition = acquire_multi_residual_factors_v24(
        evidence(),
        prior_library=residual_prior_library,
        confidence_denominator=confidence_denominator,
    )
    final_replay = replay_multi_residual_factors_v24(
        final_acquisition,
        evidence(),
        prior_library=residual_prior_library,
        confidence_denominator=confidence_denominator,
    )
    if local_labels != sum(row["ground_support_labels"] for row in distinctions):
        _fail("V26 local-label accounting changed")
    if len(failed_certificates) != len(distinctions):
        _fail("V26 certificate/distinction pairing changed")
    return {
        "schema": "acfqp.generic_multi_residual_certificate_episode.v26",
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
        "multi_residual_synthesis_attempt_count": multi_synthesis_attempts,
        "multi_residual_proposal_activations": multi_activations,
        "multi_residual_proposal_invalidation_count": multi_invalidations,
        "maximum_simultaneously_compilable_residual_proposal_count": (
            maximum_compilable_proposal_count
        ),
        "joint_abstract_plan_attempt_count": joint_attempts,
        "joint_abstract_plan_success_count": joint_successes,
        "joint_abstract_support_branch_evaluations": joint_compute,
        "joint_abstract_robust_closure_count": joint_robust_closures,
        "joint_abstract_robust_resource_truncation_count": (
            joint_resource_truncations
        ),
        "final_multi_residual_acquisition": final_acquisition,
        "final_multi_residual_replay": final_replay,
        "failed_certificates": failed_certificates,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "shared_query_pool_reused_across_residual_targets": True,
        "multiple_residual_proposals_jointly_compiled_when_available": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "joint_abstract_plan_used_as_safety_authority": False,
        "complete_residual_world_model_synthesized": False,
        "success": True,
    }


__all__ = ("run_multi_residual_certificate_episode_v26",)
