"""Certificate-guided robust planning from a reusable partial factor model.

The partial program proposes an action ordering entirely in its anonymous
projection.  It is never trusted for residual safety.  Whenever the robust
proof needs an unseen state-action support, a failed certificate is emitted
before the exact local transition is acquired.  Only those queried supports
enter the immutable overlay used by the all-branch reachability proof.
"""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)


class GenericCertificateGuidedPartialPlannerV16Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCertificateGuidedPartialPlannerV16Error(message)


def run_certificate_guided_partial_episode_v16(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
) -> dict[str, Any]:
    if maximum_abstract_depth <= 0 or maximum_execution_steps <= 0:
        _fail("V16 planning caps changed")
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
    planning_compute = 0
    abstract_plan_attempts = 0
    local_labels = 0

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal planning_compute, abstract_plan_attempts, local_labels
        raw = adapter.encode(state)
        legal = legal_by_raw.get(raw)
        if legal is None:
            failure_index = len(failed_certificates)
            failed_certificates.append(
                {
                    "failure_index": failure_index,
                    "failure_kind": "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT",
                    "raw_state": list(raw),
                    "action_key": None,
                    "ground_query_performed_before_failure": False,
                }
            )
            legal = tuple(adapter.action_key(action) for action in adapter.actions(state))
            legal_by_raw[raw] = legal
            local_labels += 1
            distinctions.append(
                {
                    "failure_index": failure_index,
                    "distinction_kind": "QUERY_LOCAL_LEGAL_ACTION_SET",
                    "raw_state": list(raw),
                    "legal_action_keys": list(legal),
                    "ground_support_labels": 1,
                    "query_after_failed_certificate": True,
                }
            )
        preferred: list[int] = []
        abstract_plan_attempts += 1
        try:
            plan = plan_partial_factor_observation_graph_v15(
                candidate, observed_rows, adapter.catalogue, raw
            )
            planning_compute += plan["projected_planning_compute_events"]
            preferred = plan["action_keys"][:1]
        except Exception:
            try:
                plan = plan_partial_factor_program_v15(
                    candidate,
                    observed_rows,
                    adapter.catalogue,
                    raw,
                    maximum_depth=maximum_abstract_depth,
                )
                planning_compute += plan["projected_planning_compute_events"]
                preferred = plan["action_keys"][:1]
            except Exception:
                preferred = []
        return tuple(
            [key for key in preferred if key in legal]
            + [key for key in legal if key not in preferred]
        )

    def query(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal local_labels
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        raw = adapter.encode(state)
        failure_index = len(failed_certificates)
        failed_certificates.append(
            {
                "failure_index": failure_index,
                "failure_kind": "UNKNOWN_RESIDUAL_PREVENTS_ALL_BRANCH_SAFETY_PROOF",
                "raw_state": list(raw),
                "action_key": key,
                "ground_query_performed_before_failure": False,
            }
        )
        action = adapter.action(key)
        outcomes = tuple(adapter.kernel.step(state, action))
        successors = tuple(outcome.next_state for outcome in outcomes)
        batch = []
        legal_before = legal_by_raw[raw]
        for successor in successors:
            raw_successor = adapter.encode(successor)
            legal_after = tuple(
                adapter.action_key(item) for item in adapter.actions(successor)
            )
            legal_by_raw[raw_successor] = legal_after
            batch.append(
                FlatRawTransitionV4(
                    0,
                    len(observed_rows) + len(local_rows) + len(batch),
                    raw,
                    legal_before,
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
                "failure_index": failure_index,
                "distinction_kind": "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT",
                "raw_state": list(raw),
                "action_key": key,
                "raw_transition_rows": [row.to_document() for row in batch],
                "ground_support_labels": 1,
                "query_after_failed_certificate": True,
            }
        )
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

    initial = adapter.initial()
    if not solve(initial):
        _fail("V16 local residual proof found no robust policy")
    state = initial
    action_keys = []
    outcome_tapes = []
    decision = 0
    while adapter.active(state):
        if decision >= maximum_execution_steps:
            _fail("V16 execution crossed its registered step cap")
        if state not in policy and not solve(state):
            _fail("V16 receding local residual proof did not close")
        key = policy[state]
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
        decision += 1
    if not adapter.success(state):
        _fail("V16 robust policy terminated outside success")
    if local_labels != sum(row["ground_support_labels"] for row in distinctions):
        _fail("V16 local-label accounting changed")
    if len(failed_certificates) != len(distinctions):
        _fail("V16 certificate/distinction pairing changed")
    return {
        "schema": "acfqp.generic_certificate_guided_partial_episode.v16",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "action_keys": action_keys,
        "outcome_tape_sha256": outcome_tapes,
        "execution_steps": len(action_keys),
        "local_ground_support_labels": local_labels,
        "queried_state_action_count": len(transition_cache),
        "abstract_plan_attempt_count": abstract_plan_attempts,
        "abstract_planning_compute_events": planning_compute,
        "failed_certificates": failed_certificates,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "all_ground_queries_followed_failed_certificates": True,
        "stream_prefix_residual_recovery_consumed": False,
        "complete_residual_world_model_synthesized": False,
        "query_local_exact_overlay_used": True,
        "robust_all_queried_branches_reachability_proved": True,
        "ground_transition_accessed_during_partial_abstract_action_proposal": False,
        "success": True,
    }


__all__ = ("run_certificate_guided_partial_episode_v16",)
