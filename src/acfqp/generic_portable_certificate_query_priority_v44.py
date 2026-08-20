"""Portable certificate-query ordering distilled from a source episode.

The artifact maps canonical anonymous states to canonical anonymous action
descriptors using only the order of source transition queries.  On a compatible
target occurrence it may order the exact certificate engine's queries before
the V42 plan and the ordinary legal-action order.  It never proves legality,
transition support, terminality, or safety; every target ground query still
requires an explicit certificate failure and only the exact local overlay can
close the proof.
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


class GenericPortableCertificateQueryPriorityV44Error(ValueError):
    pass


_PRIORITY_DOMAIN = b"acfqp:generic-portable-certificate-query-priority:v44\x00"
_EPISODE_DOMAIN = b"acfqp:generic-portable-priority-certificate-episode:v44\x00"


def _fail(message: str) -> NoReturn:
    raise GenericPortableCertificateQueryPriorityV44Error(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def compile_portable_certificate_query_priority_v44(
    source_episode: Mapping[str, Any],
    source_candidate: PartialFactorCandidateV15,
) -> dict[str, Any]:
    if type(source_episode) is not dict or type(source_candidate) is not PartialFactorCandidateV15:
        _fail("V44 source priority inventory changed")
    if (
        source_episode.get("success") is not True
        or source_episode.get("reusable_model_frozen_before_target_episode") is not True
        or source_episode.get("all_ground_queries_followed_failed_certificates") is not True
        or source_episode.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
    ):
        _fail("V44 requires a successful certificate-local source episode")
    document = source_candidate.public_document
    layout = document.get("layout")
    state_order = layout.get("state_canonical_to_raw") if type(layout) is dict else None
    action_order = layout.get("action_canonical_to_raw") if type(layout) is dict else None
    distinctions = source_episode.get("local_distinctions")
    if (
        type(state_order) is not list
        or type(action_order) is not list
        or type(distinctions) is not list
    ):
        _fail("V44 source projection changed")
    priorities: dict[tuple[int, ...], tuple[int, ...]] = {}
    source_rows = 0
    for distinction in distinctions:
        if distinction.get("distinction_kind") != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            continue
        raw = distinction.get("raw_state")
        rows = distinction.get("raw_transition_rows")
        if type(raw) is not list or type(rows) is not list or not rows:
            _fail("V44 source transition distinction changed")
        selected = rows[0].get("selected_action")
        fields = selected.get("anonymous_fields") if type(selected) is dict else None
        if (
            type(fields) is not list
            or sorted(state_order) != list(range(len(raw)))
            or sorted(action_order) != list(range(len(fields)))
            or any(row.get("selected_action") != selected for row in rows)
        ):
            _fail("V44 source action descriptor changed")
        canonical_state = tuple(raw[index] for index in state_order)
        canonical_action = tuple(fields[index] for index in action_order)
        priorities.setdefault(canonical_state, canonical_action)
        source_rows += 1
    if not priorities:
        _fail("V44 source episode identified no transition-query priority")
    priority_rows = [
        {
            "canonical_state": list(state),
            "canonical_action_fields": list(priorities[state]),
        }
        for state in sorted(priorities)
    ]
    payload = {
        "schema": "acfqp.generic_portable_certificate_query_priority.v44",
        "source_episode_id": source_episode.get("episode_id"),
        "source_joint_successor_version_space_model_id": source_episode.get(
            "joint_successor_version_space_model_id"
        ),
        "source_partial_candidate_id": document["candidate_id"],
        "state_width": document["state_width"],
        "action_field_width": document["action_field_width"],
        "state_structural_colors": copy.deepcopy(layout["state_structural_colors"]),
        "action_structural_colors": copy.deepcopy(layout["action_structural_colors"]),
        "compiled_factor_assignments": copy.deepcopy(
            document["compiled_factor_assignments"]
        ),
        "priority_rows": priority_rows,
        "priority_state_count": len(priority_rows),
        "source_transition_query_count": source_rows,
        "first_source_transition_query_per_canonical_state_retained": True,
        "raw_action_key_reused_across_occurrences": False,
        "canonical_anonymous_action_descriptor_used": True,
        "target_outcomes_used_to_fit_priority": False,
        "priority_used_only_for_query_ordering": True,
        "ground_transition_authority_present": False,
        "safety_authority_present": False,
    }
    return {
        **payload,
        "portable_query_priority_id": _content_id(_PRIORITY_DOMAIN, payload),
    }


def verify_portable_certificate_query_priority_v44(
    priority: Mapping[str, Any],
) -> dict[str, Any]:
    if type(priority) is not dict:
        _fail("V44 priority type changed")
    payload = {
        key: value for key, value in priority.items() if key != "portable_query_priority_id"
    }
    rows = priority.get("priority_rows")
    if (
        priority.get("schema") != "acfqp.generic_portable_certificate_query_priority.v44"
        or _content_id(_PRIORITY_DOMAIN, payload)
        != priority.get("portable_query_priority_id")
        or type(rows) is not list
        or not rows
        or len(rows) != priority.get("priority_state_count")
        or rows != sorted(rows, key=lambda row: tuple(row["canonical_state"]))
        or len({tuple(row["canonical_state"]) for row in rows}) != len(rows)
        or priority.get("raw_action_key_reused_across_occurrences") is not False
        or priority.get("canonical_anonymous_action_descriptor_used") is not True
        or priority.get("target_outcomes_used_to_fit_priority") is not False
        or priority.get("priority_used_only_for_query_ordering") is not True
        or priority.get("ground_transition_authority_present") is not False
        or priority.get("safety_authority_present") is not False
    ):
        _fail("V44 priority identity or claim boundary changed")
    return copy.deepcopy(priority)


def run_portable_priority_certificate_episode_v44(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    reusable_model: Mapping[str, Any] | None,
    portable_query_priority: Mapping[str, Any] | None,
    model_source_episode_index: int,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_target_ground_support_labels: int = 100_000,
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
        or maximum_target_ground_support_labels <= 0
        or maximum_abstract_support_branch_evaluations <= 0
        or abstract_support_feasible_beam_width <= 0
    ):
        _fail("V44 episode inventory changed")
    model = (
        None
        if reusable_model is None
        else verify_joint_successor_version_space_model_v42(reusable_model)
    )
    priority = (
        None
        if portable_query_priority is None
        else verify_portable_certificate_query_priority_v44(portable_query_priority)
    )
    if (model is None) != (priority is None):
        _fail("V44 reusable model and portable priority must be jointly present or absent")
    if model is not None and model_source_episode_index == episode_index:
        _fail("V44 source and target episode identities coincide")
    document = candidate.public_document
    layout = document["layout"]
    state_order = layout["state_canonical_to_raw"]
    action_order = layout["action_canonical_to_raw"]
    if priority is not None and (
        priority["state_width"] != document["state_width"]
        or priority["action_field_width"] != document["action_field_width"]
        or priority["state_structural_colors"] != layout["state_structural_colors"]
        or priority["action_structural_colors"] != layout["action_structural_colors"]
        or priority["compiled_factor_assignments"]
        != document["compiled_factor_assignments"]
    ):
        _fail("V44 target occurrence is incompatible with the portable priority")
    priority_by_state = (
        {}
        if priority is None
        else {
            tuple(row["canonical_state"]): tuple(row["canonical_action_fields"])
            for row in priority["priority_rows"]
        }
    )
    action_fields_by_key = {
        action.key: tuple(action.fields[index] for index in action_order)
        for action in adapter.catalogue
    }
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
    portable_priority_lookup_count = 0
    portable_priority_ordering_accepted = 0
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

    def priority_preferred(raw: tuple[int, ...], legal: tuple[int, ...]) -> list[int]:
        nonlocal portable_priority_lookup_count, portable_priority_ordering_accepted
        if priority is None:
            return []
        portable_priority_lookup_count += 1
        canonical_state = tuple(raw[index] for index in state_order)
        wanted = priority_by_state.get(canonical_state)
        if wanted is None:
            return []
        matches = [key for key in legal if action_fields_by_key.get(key) == wanted]
        if len(matches) != 1:
            return []
        portable_priority_ordering_accepted += 1
        return matches

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
            _fail("V44 adapter raw state changed")
        legal = legal_by_raw.get(raw)
        if legal is None:
            if local_labels >= maximum_target_ground_support_labels:
                _fail("V44 target label cap reached before legality query")
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
        for key in (
            *priority_preferred(raw, legal),
            *model_preferred(raw, legal),
            *legal,
        ):
            if key in legal and key not in ordered:
                ordered.append(key)
        return tuple(ordered)

    def query(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal local_labels
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        if local_labels >= maximum_target_ground_support_labels:
            _fail("V44 target label cap reached before transition query")
        raw = adapter.encode(state)
        failure_index = failed_certificate(
            "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF", state, key
        )
        outcomes = tuple(adapter.kernel.step(state, adapter.action(key)))
        if not outcomes:
            _fail("V44 ground kernel returned empty support")
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
                    adapter.action(key),
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
        _fail("V44 exact query-local proof found no policy")
    action_keys = []
    outcome_tapes = []
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in exact_policy and not solve(state):
            _fail("V44 receding exact query-local proof did not close")
        key = exact_policy[state]
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V44 execution crossed its cap or terminated outside success")
    if (
        local_labels != sum(row["ground_support_labels"] for row in distinctions)
        or len(failed_certificates) != len(distinctions)
        or any(row["query_after_failed_certificate"] is not True for row in distinctions)
    ):
        _fail("V44 certificate-local accounting changed")
    payload = {
        "schema": "acfqp.generic_portable_priority_certificate_episode.v44",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "model_source_episode_index": model_source_episode_index,
        "arm": (
            "PORTABLE_PRIORITY_AND_REUSABLE_MODEL"
            if priority is not None
            else "STRICT_NO_REUSABLE_MODEL_OR_PRIORITY"
        ),
        "partial_candidate_id": document["candidate_id"],
        "joint_successor_version_space_model_id": (
            None if model is None else model["joint_successor_version_space_model_id"]
        ),
        "portable_query_priority_id": (
            None if priority is None else priority["portable_query_priority_id"]
        ),
        "action_keys": action_keys,
        "outcome_tape_sha256": outcome_tapes,
        "execution_steps": len(action_keys),
        "target_certificate_local_ground_support_labels": local_labels,
        "maximum_target_ground_support_labels": maximum_target_ground_support_labels,
        "queried_state_action_count": len(transition_cache),
        "portable_priority_lookup_count": portable_priority_lookup_count,
        "portable_priority_ordering_accepted_count": portable_priority_ordering_accepted,
        "abstract_plan_attempt_count": abstract_plan_attempts,
        "abstract_plan_success_count": abstract_plan_successes,
        "abstract_plan_abstention_count": abstract_plan_abstentions,
        "abstract_model_ordering_accepted_count": abstract_model_ordering_accepted,
        "abstract_planning_compute_events": abstract_planning_compute,
        "failed_certificates": failed_certificates,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "source_model_and_priority_frozen_before_target_episode": priority is not None,
        "target_outcomes_used_to_refit_source_artifacts": False,
        "same_exact_query_local_certificate_engine": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "reusable_artifacts_used_as_safety_authority": False,
        "portable_priority_used_only_for_query_ordering": True,
        "complete_world_model_synthesized": False,
        "success": True,
    }
    return {
        **payload,
        "episode_id": _content_id(_EPISODE_DOMAIN, payload),
    }


__all__ = (
    "GenericPortableCertificateQueryPriorityV44Error",
    "compile_portable_certificate_query_priority_v44",
    "run_portable_priority_certificate_episode_v44",
    "verify_portable_certificate_query_priority_v44",
)
