"""Certificate-local execution ordered by a frozen reusable V42 model.

Both ablation arms use the same exact query-local proof engine.  The derived
arm may ask the frozen V42 version-space planner which legal action to try
first; the strict arm receives no abstract model.  In either arm an unseen
state-action pair first creates a failed certificate, then and only then is its
ground support queried and stored in an occurrence-local immutable overlay.

Thus the reusable model can reduce search labels, but it never discharges
legality, transition, terminal, or safety obligations.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    plan_joint_successor_version_space_v42,
    verify_joint_successor_version_space_model_v42,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


class GenericReusableVersionSpaceCertificatePlannerV43Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericReusableVersionSpaceCertificatePlannerV43Error(message)


def run_reusable_version_space_certificate_episode_v43(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    reusable_model: Mapping[str, Any] | None,
    model_source_episode_index: int,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_abstract_support_branch_evaluations: int = 1_000_000,
    abstract_support_feasible_beam_width: int = 64,
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or type(model_source_episode_index) is not int
        or type(episode_index) is not int
        or maximum_abstract_depth <= 0
        or maximum_execution_steps <= 0
        or maximum_abstract_support_branch_evaluations <= 0
        or abstract_support_feasible_beam_width <= 0
    ):
        _fail("V43 episode inventory changed")
    if reusable_model is not None:
        model = verify_joint_successor_version_space_model_v42(reusable_model)
        if model_source_episode_index == episode_index:
            _fail("V43 reusable model source and target episode identities coincide")
    else:
        model = None
    document = candidate.public_document
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
    abstract_plan_attempts = 0
    abstract_plan_successes = 0
    abstract_plan_abstentions = 0
    abstract_planning_compute = 0
    abstract_model_ordering_accepted = 0
    plan_cache: dict[tuple[int, ...], dict[str, Any] | None] = {}

    def failed_certificate(kind: str, state: Any, key: int | None) -> int:
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

    def model_preferred(raw: tuple[int, ...], legal: tuple[int, ...]) -> list[int]:
        nonlocal abstract_plan_attempts, abstract_plan_successes
        nonlocal abstract_plan_abstentions, abstract_planning_compute
        nonlocal abstract_model_ordering_accepted
        if model is None:
            return []
        if raw in plan_cache:
            cached = plan_cache[raw]
            if cached is None:
                return []
            key = cached["initial_action_key"]
            return [key] if key in legal else []
        abstract_plan_attempts += 1
        try:
            plan = plan_joint_successor_version_space_v42(
                model,
                candidate,
                adapter.catalogue,
                raw,
                maximum_depth=maximum_abstract_depth,
                maximum_support_branch_evaluations=(
                    maximum_abstract_support_branch_evaluations
                ),
                support_feasible_beam_width=abstract_support_feasible_beam_width,
            )
        except GenericJointSuccessorVersionSpacePlannerV42Error:
            plan_cache[raw] = None
            abstract_plan_abstentions += 1
            return []
        plan_cache[raw] = plan
        abstract_plan_successes += 1
        abstract_planning_compute += plan["abstract_support_branch_evaluations"]
        key = plan["initial_action_key"]
        if key not in legal:
            abstract_plan_abstentions += 1
            return []
        abstract_model_ordering_accepted += 1
        return [key]

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal local_labels
        raw = adapter.encode(state)
        if type(raw) is not tuple:
            _fail("V43 adapter raw state changed")
        legal = legal_by_raw.get(raw)
        if legal is None:
            failure_index = failed_certificate(
                "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT", state, None
            )
            legal = tuple(
                sorted(adapter.action_key(action) for action in adapter.actions(state))
            )
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
        ordered = []
        for key in (*model_preferred(raw, legal), *legal):
            if key in legal and key not in ordered:
                ordered.append(key)
        return tuple(ordered)

    def query(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal local_labels
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        raw = adapter.encode(state)
        failure_index = failed_certificate(
            "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF", state, key
        )
        outcomes = tuple(adapter.kernel.step(state, adapter.action(key)))
        if not outcomes:
            _fail("V43 ground kernel returned empty support")
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
                "failure_index": failure_index,
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
        _fail("V43 exact query-local proof found no policy")
    action_keys = []
    outcome_tapes = []
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in exact_policy and not solve(state):
            _fail("V43 receding exact query-local proof did not close")
        key = exact_policy[state]
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V43 execution crossed its cap or terminated outside success")
    if (
        local_labels
        != sum(row["ground_support_labels"] for row in distinctions)
        or len(failed_certificates) != len(distinctions)
        or any(
            row["query_after_failed_certificate"] is not True
            for row in distinctions
        )
    ):
        _fail("V43 certificate-local accounting changed")
    payload = {
        "schema": "acfqp.generic_reusable_version_space_certificate_episode.v43",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "model_source_episode_index": model_source_episode_index,
        "arm": (
            "REUSABLE_JOINT_VERSION_SPACE_MODEL"
            if model is not None
            else "STRICT_NO_REUSABLE_MODEL"
        ),
        "partial_candidate_id": document["candidate_id"],
        "joint_successor_version_space_model_id": (
            None if model is None else model["joint_successor_version_space_model_id"]
        ),
        "action_keys": action_keys,
        "outcome_tape_sha256": outcome_tapes,
        "execution_steps": len(action_keys),
        "target_certificate_local_ground_support_labels": local_labels,
        "queried_state_action_count": len(transition_cache),
        "abstract_plan_attempt_count": abstract_plan_attempts,
        "abstract_plan_success_count": abstract_plan_successes,
        "abstract_plan_abstention_count": abstract_plan_abstentions,
        "abstract_model_ordering_accepted_count": abstract_model_ordering_accepted,
        "abstract_planning_compute_events": abstract_planning_compute,
        "failed_certificates": failed_certificates,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "reusable_model_frozen_before_target_episode": model is not None,
        "target_outcomes_used_to_refit_reusable_model": False,
        "same_exact_query_local_certificate_engine": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "reusable_abstract_model_used_as_safety_authority": False,
        "empirical_version_space_promoted_to_global_exact_dynamics": False,
        "complete_world_model_synthesized": False,
        "success": True,
    }
    return {
        **payload,
        "episode_id": hashlib.sha256(
            b"acfqp:generic-reusable-version-space-certificate-episode:v43\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_matched_reusable_version_space_ablation_v43(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    model: Mapping[str, Any],
    *,
    model_source_episode_index: int,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_abstract_support_branch_evaluations: int = 1_000_000,
    abstract_support_feasible_beam_width: int = 64,
) -> dict[str, Any]:
    verified = verify_joint_successor_version_space_model_v42(model)
    arguments = {
        "model_source_episode_index": model_source_episode_index,
        "episode_index": episode_index,
        "maximum_abstract_depth": maximum_abstract_depth,
        "maximum_execution_steps": maximum_execution_steps,
        "maximum_abstract_support_branch_evaluations": (
            maximum_abstract_support_branch_evaluations
        ),
        "abstract_support_feasible_beam_width": abstract_support_feasible_beam_width,
    }
    derived = run_reusable_version_space_certificate_episode_v43(
        adapter,
        candidate,
        observed_rows,
        reusable_model=verified,
        **arguments,
    )
    strict = run_reusable_version_space_certificate_episode_v43(
        adapter,
        candidate,
        observed_rows,
        reusable_model=None,
        **arguments,
    )
    derived_labels = derived["target_certificate_local_ground_support_labels"]
    strict_labels = strict["target_certificate_local_ground_support_labels"]
    payload = {
        "schema": "acfqp.generic_reusable_version_space_ablation.v43",
        "family": adapter.family,
        "seed": adapter.seed,
        "model_source_episode_index": model_source_episode_index,
        "target_episode_index": episode_index,
        "joint_successor_version_space_model_id": verified[
            "joint_successor_version_space_model_id"
        ],
        "arms": {
            "REUSABLE_JOINT_VERSION_SPACE_MODEL": derived,
            "STRICT_NO_REUSABLE_MODEL": strict,
        },
        "derived_target_certificate_local_ground_support_labels": derived_labels,
        "strict_target_certificate_local_ground_support_labels": strict_labels,
        "derived_minus_strict_target_labels": derived_labels - strict_labels,
        "actual_target_sample_reduction_observed": derived_labels < strict_labels,
        "same_adapter_kernel_seed_and_target_episode": True,
        "same_exact_certificate_engine_and_stopping_rule": True,
        "only_reusable_model_availability_differs_between_arms": True,
        "offline_source_labels_and_target_labels_separate": True,
        "execution_steps_and_planning_compute_separate_from_labels": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "abstract_model_safety_authority_present": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "ablation_id": hashlib.sha256(
            b"acfqp:generic-reusable-version-space-ablation:v43\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "GenericReusableVersionSpaceCertificatePlannerV43Error",
    "run_matched_reusable_version_space_ablation_v43",
    "run_reusable_version_space_certificate_episode_v43",
)
