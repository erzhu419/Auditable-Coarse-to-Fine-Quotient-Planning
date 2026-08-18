"""Occurrence-bound proof-overlay reuse for partial abstract planning.

The reusable partial model only orders candidate actions.  Exact legality and
residual supports enter an immutable occurrence-local overlay after a failed
certificate.  Multiple stochastic episodes share that overlay and its robust
policy; no fact is transferred across occurrence identities.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericPersistentCertificateOverlayPlannerV17Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPersistentCertificateOverlayPlannerV17Error(message)


def run_persistent_certificate_overlay_episodes_v17(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
) -> dict[str, Any]:
    if (
        type(episode_indices) is not tuple
        or not episode_indices
        or len(set(episode_indices)) != len(episode_indices)
        or any(type(index) is not int or index < 0 for index in episode_indices)
        or maximum_abstract_depth <= 0
        or maximum_execution_steps <= 0
    ):
        _fail("V17 persistent episode contract changed")
    legal_by_raw: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in observed_rows:
        legal_by_raw[row.pre] = row.legal_before
        legal_by_raw[row.post] = row.legal_after
    transition_cache: dict[tuple[Any, int], tuple[Any, ...]] = {}
    policy: dict[Any, int] = {}
    visiting: set[Any] = set()
    overlay_rows: list[FlatRawTransitionV4] = []
    all_failures: list[dict[str, Any]] = []
    all_distinctions: list[dict[str, Any]] = []
    current_failures: list[dict[str, Any]] = []
    current_distinctions: list[dict[str, Any]] = []
    planning_compute = 0
    abstract_plan_attempts = 0

    def failure(kind: str, state: Any, key: int | None) -> int:
        index = len(all_failures)
        row = {
            "failure_index": index,
            "failure_kind": kind,
            "raw_state": list(adapter.encode(state)),
            "action_key": key,
            "ground_query_performed_before_failure": False,
        }
        all_failures.append(row)
        current_failures.append(row)
        return index

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal planning_compute, abstract_plan_attempts
        raw = adapter.encode(state)
        legal = legal_by_raw.get(raw)
        if legal is None:
            index = failure("MISSING_QUERY_LOCAL_LEGALITY_SUPPORT", state, None)
            legal = tuple(adapter.action_key(action) for action in adapter.actions(state))
            legal_by_raw[raw] = legal
            row = {
                "failure_index": index,
                "distinction_kind": "QUERY_LOCAL_LEGAL_ACTION_SET",
                "raw_state": list(raw),
                "action_key": None,
                "legal_action_keys": list(legal),
                "ground_support_labels": 1,
                "query_after_failed_certificate": True,
            }
            all_distinctions.append(row)
            current_distinctions.append(row)
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
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        raw = adapter.encode(state)
        index = failure(
            "UNKNOWN_RESIDUAL_PREVENTS_ALL_BRANCH_SAFETY_PROOF", state, key
        )
        action = adapter.action(key)
        successors = tuple(outcome.next_state for outcome in adapter.kernel.step(state, action))
        batch = []
        for successor in successors:
            raw_successor = adapter.encode(successor)
            legal_after = tuple(
                adapter.action_key(item) for item in adapter.actions(successor)
            )
            legal_by_raw[raw_successor] = legal_after
            batch.append(
                FlatRawTransitionV4(
                    0,
                    len(observed_rows) + len(overlay_rows) + len(batch),
                    raw,
                    legal_by_raw[raw],
                    adapter.catalogue[key],
                    raw_successor,
                    legal_after,
                    None if legal_after else adapter.success(successor),
                )
            )
        overlay_rows.extend(batch)
        transition_cache[pair] = successors
        row = {
            "failure_index": index,
            "distinction_kind": "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT",
            "raw_state": list(raw),
            "action_key": key,
            "raw_transition_rows": [item.to_document() for item in batch],
            "ground_support_labels": 1,
            "query_after_failed_certificate": True,
        }
        all_distinctions.append(row)
        current_distinctions.append(row)
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

    episodes = []
    previous_labels = 0
    for episode_index in episode_indices:
        current_failures.clear()
        current_distinctions.clear()
        planning_before = planning_compute
        attempts_before = abstract_plan_attempts
        state = adapter.initial()
        if state not in policy and not solve(state):
            _fail("V17 persistent robust proof did not close")
        action_keys = []
        outcome_tapes = []
        decision = 0
        while adapter.active(state):
            if decision >= maximum_execution_steps:
                _fail("V17 persistent execution crossed its registered cap")
            if state not in policy and not solve(state):
                _fail("V17 receding persistent proof did not close")
            key = policy[state]
            outcome, tape = adapter.select_outcome(
                state, key, episode_index, decision
            )
            state = outcome.next_state
            action_keys.append(key)
            outcome_tapes.append(tape)
            decision += 1
        if not adapter.success(state):
            _fail("V17 persistent episode terminated outside success")
        new_labels = sum(row["ground_support_labels"] for row in current_distinctions)
        cumulative = previous_labels + new_labels
        if cumulative != len(all_distinctions):
            _fail("V17 persistent label ledger changed")
        episode = {
            "schema": "acfqp.generic_persistent_certificate_overlay_episode.v17",
            "family": adapter.family,
            "seed": adapter.seed,
            "episode_index": episode_index,
            "partial_candidate_id": candidate.public_document["candidate_id"],
            "action_keys": action_keys,
            "outcome_tape_sha256": outcome_tapes,
            "execution_steps": len(action_keys),
            "new_local_ground_support_labels": new_labels,
            "cumulative_local_ground_support_labels": cumulative,
            "new_failed_certificates": list(current_failures),
            "new_local_distinctions": list(current_distinctions),
            "new_abstract_plan_attempt_count": abstract_plan_attempts - attempts_before,
            "new_abstract_planning_compute_events": planning_compute - planning_before,
            "persistent_overlay_reused": previous_labels > 0,
            "ground_query_free_after_overlay_closure": new_labels == 0,
            "all_ground_queries_followed_failed_certificates": True,
            "success": True,
        }
        episodes.append(episode)
        previous_labels = cumulative
    overlay_documents = [row.to_document() for row in overlay_rows]
    overlay_payload = {
        "family": adapter.family,
        "seed": adapter.seed,
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "raw_transition_rows": overlay_documents,
        "legality_state_count": len(legal_by_raw),
        "exact_state_action_support_count": len(transition_cache),
    }
    overlay_id = hashlib.sha256(canonical_json_bytes(overlay_payload)).hexdigest()
    return {
        "schema": "acfqp.generic_persistent_certificate_overlay_run.v17",
        "family": adapter.family,
        "seed": adapter.seed,
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "episode_indices": list(episode_indices),
        "episodes": episodes,
        "failed_certificates": all_failures,
        "local_distinctions": all_distinctions,
        "overlay_raw_transition_rows": overlay_documents,
        "persistent_overlay_id": overlay_id,
        "total_local_ground_support_labels": len(all_distinctions),
        "cold_repeated_query_label_counterfactual": len(all_distinctions) * len(episode_indices),
        "amortized_query_label_reduction": len(all_distinctions) * (len(episode_indices) - 1),
        "later_episode_ground_query_count": sum(
            row["new_local_ground_support_labels"] for row in episodes[1:]
        ),
        "occurrence_identity_bound": True,
        "cross_occurrence_ground_fact_reuse_allowed": False,
        "all_ground_queries_followed_failed_certificates": True,
        "partial_model_used_only_for_abstract_action_order": True,
        "query_local_exact_overlay_used_for_safety": True,
        "complete_residual_world_model_synthesized": False,
        "stream_prefix_residual_recovery_consumed": False,
        "success": all(row["success"] for row in episodes),
    }


__all__ = ("run_persistent_certificate_overlay_episodes_v17",)
