"""One exact certificate engine with an optional abstract action orderer."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


class GenericCertificateLocalRecedingEngineV71Error(ValueError):
    pass


_EPISODE_DOMAIN = b"acfqp:generic-certificate-local-receding-episode:v71\x00"


def _fail(message: str) -> NoReturn:
    raise GenericCertificateLocalRecedingEngineV71Error(message)


def _identifier(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_EPISODE_DOMAIN + canonical_json_bytes(payload)).hexdigest()


def run_certificate_local_receding_episode_v71(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    arm: str,
    abstract_orderer: Callable[[tuple[int, ...]], Mapping[str, Any] | None]
    | None,
    episode_index: int,
    maximum_execution_steps: int,
    maximum_target_ground_support_labels: int,
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or type(arm) is not str
        or not arm
        or (abstract_orderer is not None and not callable(abstract_orderer))
        or type(episode_index) is not int
        or type(maximum_execution_steps) is not int
        or maximum_execution_steps <= 0
        or type(maximum_target_ground_support_labels) is not int
        or maximum_target_ground_support_labels <= 0
    ):
        _fail("V71 episode inventory changed")
    legal_by_raw: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in observed_rows:
        legal_by_raw[row.pre] = row.legal_before
        legal_by_raw[row.post] = row.legal_after
    transition_cache: dict[tuple[Any, int], tuple[Any, ...]] = {}
    exact_policy: dict[Any, int] = {}
    visiting: set[Any] = set()
    failed_certificates: list[dict[str, Any]] = []
    distinctions: list[dict[str, Any]] = []
    local_rows: list[FlatRawTransitionV4] = []
    local_labels = 0
    abstract_attempts = 0
    abstract_successes = 0
    abstract_abstentions = 0
    abstract_compute = 0
    abstract_robust_closures = 0
    abstract_resource_truncations = 0
    abstract_proposal_by_raw: dict[tuple[int, ...], int] = {}
    abstract_plan_receipts: list[dict[str, Any]] = []
    plan_cache: dict[tuple[int, ...], Mapping[str, Any] | None] = {}

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

    def abstract_preferred(
        raw: tuple[int, ...], legal: tuple[int, ...]
    ) -> list[int]:
        nonlocal abstract_attempts, abstract_successes, abstract_abstentions
        nonlocal abstract_compute, abstract_robust_closures
        nonlocal abstract_resource_truncations
        if abstract_orderer is None:
            return []
        if raw not in plan_cache:
            abstract_attempts += 1
            plan_cache[raw] = abstract_orderer(raw)
        plan = plan_cache[raw]
        if plan is None:
            abstract_abstentions += 1
            return []
        if type(plan) is not dict:
            plan = dict(plan)
        if raw not in abstract_proposal_by_raw:
            abstract_plan_receipts.append(
                {"raw_state": list(raw), "abstract_plan": copy.deepcopy(plan)}
            )
            abstract_successes += 1
            abstract_compute += plan.get("abstract_support_branch_evaluations", 0)
            abstract_robust_closures += (
                plan.get("robust_all_version_space_branches_closed") is True
            )
            abstract_resource_truncations += (
                plan.get("robust_search_resource_cap_reached") is True
            )
        key = plan.get("initial_action_key")
        if type(key) is not int or key not in legal:
            abstract_abstentions += 1
            return []
        abstract_proposal_by_raw[raw] = key
        return [key]

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal local_labels
        raw = adapter.encode(state)
        legal = legal_by_raw.get(raw)
        if legal is None:
            if local_labels >= maximum_target_ground_support_labels:
                _fail("V71 label cap reached before legality query")
            index = failure("MISSING_QUERY_LOCAL_LEGALITY_SUPPORT", state, None)
            legal = tuple(
                sorted(adapter.action_key(action) for action in adapter.actions(state))
            )
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
        ordered = []
        for key in (*abstract_preferred(raw, legal), *legal):
            if key in legal and key not in ordered:
                ordered.append(key)
        return tuple(ordered)

    def query(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal local_labels
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        if local_labels >= maximum_target_ground_support_labels:
            _fail("V71 label cap reached before transition query")
        raw = adapter.encode(state)
        index = failure(
            "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF", state, key
        )
        outcomes = tuple(adapter.kernel.step(state, adapter.action(key)))
        if not outcomes:
            _fail("V71 target ground kernel returned empty support")
        successors = tuple(outcome.next_state for outcome in outcomes)
        batch = []
        for successor in successors:
            raw_successor = adapter.encode(successor)
            legal_after = tuple(
                sorted(
                    adapter.action_key(action)
                    for action in adapter.actions(successor)
                )
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
                "distinction_kind": "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT",
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
                exact_policy[state] = key
                visiting.remove(state)
                return True
        visiting.remove(state)
        return False

    state = adapter.initial()
    if not solve(state):
        _fail("V71 exact query-local proof found no policy")
    action_keys = []
    outcome_tapes = []
    execution_abstract_matches = []
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in exact_policy and not solve(state):
            _fail("V71 receding exact query-local proof did not close")
        raw = adapter.encode(state)
        key = exact_policy[state]
        execution_abstract_matches.append(
            abstract_orderer is not None
            and abstract_proposal_by_raw.get(raw) == key
        )
        outcome, tape = adapter.select_outcome(
            state, key, episode_index, decision
        )
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V71 execution crossed its cap or terminated outside success")
    if (
        local_labels
        != sum(row["ground_support_labels"] for row in distinctions)
        or len(failed_certificates) != len(distinctions)
        or any(
            row["query_after_failed_certificate"] is not True
            for row in distinctions
        )
    ):
        _fail("V71 certificate-local accounting changed")
    payload = {
        "schema": "acfqp.generic_certificate_local_receding_episode.v71",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "arm": arm,
        "target_candidate_id": candidate.public_document["candidate_id"],
        "action_keys": action_keys,
        "outcome_tape_sha256": outcome_tapes,
        "execution_steps": len(action_keys),
        "target_certificate_local_ground_support_labels": local_labels,
        "queried_state_action_count": len(transition_cache),
        "abstract_plan_attempt_count": abstract_attempts,
        "abstract_plan_success_count": abstract_successes,
        "abstract_plan_abstention_count": abstract_abstentions,
        "abstract_planning_compute_events": abstract_compute,
        "abstract_robust_closure_count": abstract_robust_closures,
        "abstract_robust_resource_truncation_count": (
            abstract_resource_truncations
        ),
        "abstract_plan_receipts": abstract_plan_receipts,
        "execution_action_matches_abstract_proposal": (
            execution_abstract_matches
        ),
        "execution_action_matches_abstract_proposal_count": sum(
            execution_abstract_matches
        ),
        "failed_certificates": failed_certificates,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "abstract_model_used_only_for_action_ordering": (
            abstract_orderer is not None
        ),
        "model_alignment_or_terminal_overlay_used_as_safety_authority": False,
        "target_episode_outcomes_used_to_refit_model_alignment_or_overlay": False,
        "same_exact_engine_implementation_for_matched_and_strict_arms": True,
        "complete_world_model_synthesized": False,
        "success": True,
    }
    return {**payload, "episode_id": _identifier(payload)}


__all__ = ("run_certificate_local_receding_episode_v71",)
