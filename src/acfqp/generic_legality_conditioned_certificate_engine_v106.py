"""Exact certificate engine exposing certified legality to a fallible orderer."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_abstract_execution_receipt_v103 import (
    build_abstract_execution_receipt_v103,
)
from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


_EPISODE_DOMAIN = b"acfqp:generic-legality-conditioned-certificate-episode:v106\x00"


class GenericLegalityConditionedCertificateEngineV106Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericLegalityConditionedCertificateEngineV106Error(message)


def _group_count(rows: tuple[FlatRawTransitionV4, ...]) -> int:
    return len({(row.pre, row.action.key) for row in rows})


def run_legality_conditioned_certificate_episode_v106(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    preloaded_rows: tuple[FlatRawTransitionV4, ...],
    *,
    preloaded_acquisition_ground_support_labels: int,
    arm: str,
    abstract_orderer: Callable[
        [tuple[int, ...], tuple[int, ...], str, int | None],
        Mapping[str, Any] | None,
    ],
    episode_index: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(preloaded_rows) is not tuple
        or _group_count(preloaded_rows)
        != preloaded_acquisition_ground_support_labels
        or type(arm) is not str
        or not arm
        or not callable(abstract_orderer)
        or type(episode_index) is not int
        or type(maximum_execution_steps) is not int
        or maximum_execution_steps <= 0
        or type(maximum_incremental_certificate_ground_support_labels) is not int
        or maximum_incremental_certificate_ground_support_labels <= 0
    ):
        _fail("V106 episode inventory changed")
    legal_by_raw: dict[tuple[int, ...], tuple[int, ...]] = {}
    legality_provenance: dict[tuple[int, ...], tuple[str, int | None]] = {}
    staged: dict[tuple[tuple[int, ...], int], list[tuple[int, ...]]] = {}
    for row in preloaded_rows:
        for raw, legal in ((row.pre, row.legal_before), (row.post, row.legal_after)):
            old = legal_by_raw.setdefault(raw, legal)
            if old != legal:
                _fail("V106 preloaded legality support is inconsistent")
            legality_provenance.setdefault(
                raw, ("PRELOADED_EXACT_LEGALITY_SUPPORT", None)
            )
        staged.setdefault((row.pre, row.action.key), []).append(row.post)
    preloaded_by_pair = {
        pair: tuple(sorted(set(successors))) for pair, successors in staged.items()
    }
    transition_cache: dict[tuple[Any, int], tuple[Any, ...]] = {}
    exact_policy: dict[Any, int] = {}
    visiting: set[Any] = set()
    failures: list[dict[str, Any]] = []
    distinctions: list[dict[str, Any]] = []
    local_rows: list[FlatRawTransitionV4] = []
    incremental_labels = 0
    preloaded_transition_support_hits = 0
    abstract_attempts = 0
    abstract_successes = 0
    abstract_abstentions = 0
    abstract_compute = 0
    plan_cache: dict[tuple[int, ...], Mapping[str, Any] | None] = {}
    plan_receipts: list[dict[str, Any]] = []

    def failed(kind: str, state: Any, key: int | None) -> int:
        index = len(failures)
        failures.append(
            {
                "failure_index": index,
                "failure_kind": kind,
                "raw_state": list(adapter.encode(state)),
                "action_key": key,
                "ground_query_performed_before_failure": False,
            }
        )
        return index

    def preferred(raw: tuple[int, ...], legal: tuple[int, ...]) -> list[int]:
        nonlocal abstract_attempts, abstract_successes, abstract_abstentions
        nonlocal abstract_compute
        if raw not in plan_cache:
            abstract_attempts += 1
            source, failure_index = legality_provenance[raw]
            plan_cache[raw] = abstract_orderer(
                raw, legal, source, failure_index
            )
        plan = plan_cache[raw]
        if plan is None:
            abstract_abstentions += 1
            return []
        if type(plan) is not dict:
            plan = dict(plan)
        key = plan.get("initial_action_key")
        if (
            type(key) is not int
            or key not in legal
            or plan.get("exact_legal_action_keys_at_initial_state") != list(legal)
        ):
            abstract_abstentions += 1
            return []
        if not any(row["raw_state"] == list(raw) for row in plan_receipts):
            abstract_successes += 1
            abstract_compute += plan.get("abstract_support_branch_evaluations", 0)
            plan_receipts.append(
                {"raw_state": list(raw), "abstract_plan": copy.deepcopy(plan)}
            )
        return [key]

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal incremental_labels
        raw = adapter.encode(state)
        legal = legal_by_raw.get(raw)
        if legal is None:
            if incremental_labels >= maximum_incremental_certificate_ground_support_labels:
                _fail("V106 label cap reached before legality query")
            index = failed("MISSING_QUERY_LOCAL_LEGALITY_SUPPORT", state, None)
            legal = tuple(
                sorted(adapter.action_key(action) for action in adapter.actions(state))
            )
            legal_by_raw[raw] = legal
            legality_provenance[raw] = (
                "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
                index,
            )
            incremental_labels += 1
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
        result = []
        for key in (*preferred(raw, legal), *legal):
            if key in legal and key not in result:
                result.append(key)
        return tuple(result)

    def exact_successors(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal incremental_labels, preloaded_transition_support_hits
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        raw = adapter.encode(state)
        outcomes = tuple(adapter.kernel.step(state, adapter.action(key)))
        if not outcomes:
            _fail("V106 target ground kernel returned empty support")
        successors = tuple(outcome.next_state for outcome in outcomes)
        raw_successors = tuple(sorted({adapter.encode(row) for row in successors}))
        preloaded = preloaded_by_pair.get((raw, key))
        if preloaded is not None:
            if raw_successors != preloaded:
                _fail("V106 preloaded transition support changed")
            preloaded_transition_support_hits += 1
            transition_cache[pair] = successors
            return successors
        if incremental_labels >= maximum_incremental_certificate_ground_support_labels:
            _fail("V106 label cap reached before transition query")
        index = failed(
            "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF", state, key
        )
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
            legality_provenance[raw_successor] = (
                "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
                index,
            )
            batch.append(
                FlatRawTransitionV4(
                    0,
                    len(preloaded_rows) + len(local_rows) + len(batch),
                    raw,
                    legal_by_raw[raw],
                    adapter.catalogue[key],
                    raw_successor,
                    legal_after,
                    None if legal_after else adapter.success(successor),
                )
            )
        local_rows.extend(batch)
        incremental_labels += 1
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
        transition_cache[pair] = successors
        return successors

    def solve(state: Any) -> bool:
        if adapter.success(state):
            return True
        if not adapter.active(state) or state in visiting:
            return False
        visiting.add(state)
        for key in ordered_actions(state):
            if all(solve(row) for row in exact_successors(state, key)):
                exact_policy[state] = key
                visiting.remove(state)
                return True
        visiting.remove(state)
        return False

    state = adapter.initial()
    if not solve(state):
        _fail("V106 exact query-local proof found no policy")
    action_keys = []
    tapes = []
    matches = []
    execution_receipts = []
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in exact_policy and not solve(state):
            _fail("V106 receding exact query-local proof did not close")
        raw = adapter.encode(state)
        key = exact_policy[state]
        plan = plan_cache.get(raw)
        shield = (
            plan.get("agreement_shield_receipt")
            if type(plan) is dict
            else shield_abstract_action_order_v99(
                abstract_proposal=(),
                partial_proposal=(),
                legal_action_keys=legal_by_raw[raw],
            )
        )
        receipt = build_abstract_execution_receipt_v103(
            decision_index=decision,
            raw_state=raw,
            chosen_action_key=key,
            abstract_proposal=tuple(shield["abstract_proposal"]),
            partial_proposal=tuple(shield["partial_proposal"]),
            legal_action_keys=tuple(shield["legal_action_keys"]),
            shield_receipt=shield,
        )
        execution_receipts.append(receipt)
        matches.append(receipt["chosen_action_matches_admitted_abstract_proposal"])
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        action_keys.append(key)
        tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V106 execution crossed its cap or terminated outside success")
    if (
        incremental_labels
        != sum(row["ground_support_labels"] for row in distinctions)
        or len(failures) != len(distinctions)
    ):
        _fail("V106 incremental certificate accounting changed")
    payload = {
        "schema": "acfqp.generic_legality_conditioned_certificate_episode.v106",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "arm": arm,
        "target_candidate_id": candidate.public_document["candidate_id"],
        "action_keys": action_keys,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(action_keys),
        "preloaded_acquisition_ground_support_labels": preloaded_acquisition_ground_support_labels,
        "incremental_certificate_local_ground_support_labels": incremental_labels,
        "total_target_ground_support_labels": preloaded_acquisition_ground_support_labels + incremental_labels,
        "preloaded_transition_support_hit_count": preloaded_transition_support_hits,
        "queried_state_action_count": len(transition_cache),
        "abstract_plan_attempt_count": abstract_attempts,
        "abstract_plan_success_count": abstract_successes,
        "abstract_plan_abstention_count": abstract_abstentions,
        "abstract_planning_compute_events": abstract_compute,
        "abstract_plan_receipts": plan_receipts,
        "execution_action_matches_abstract_proposal": matches,
        "execution_action_matches_abstract_proposal_count": sum(matches),
        "abstract_execution_receipts": execution_receipts,
        "every_execution_action_has_content_addressed_receipt": len(execution_receipts) == len(action_keys),
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "raw_incremental_transition_rows": [row.to_document() for row in local_rows],
        "all_incremental_ground_queries_followed_failed_certificates": True,
        "preloaded_exact_rows_reused_without_reacquisition": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "abstract_model_used_only_for_action_ordering": True,
        "certified_legality_exposed_only_as_abstract_initial_action_constraint": True,
        "ground_transition_accessed_during_abstract_search": False,
        "model_or_alignment_used_as_safety_authority": False,
        "target_episode_outcomes_used_to_refit_model_or_alignment": False,
        "same_exact_engine_implementation_for_transfer_and_strict_arms": True,
        "complete_world_model_synthesized": False,
        "success": True,
    }
    return {
        **payload,
        "episode_id": hashlib.sha256(
            _EPISODE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_legality_conditioned_certificate_episode_v106",)
