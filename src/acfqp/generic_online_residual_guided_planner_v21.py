"""Online residual-proposal guidance with certificate-local exact safety.

The reusable partial model and an optional residual meta-prior only order
actions.  Every previously unseen legality or transition support is still
queried after a failed certificate and enters an occurrence-local exact
overlay.  Residual proposals are synthesized repeatedly from those past local
rows; they never predict a transition in lieu of a certificate.
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
from acfqp.generic_total_adaptive_residual_acquisition_v20 import (
    acquire_total_adaptive_residual_factor_v20,
    replay_total_adaptive_residual_factor_v20,
)


class GenericOnlineResidualGuidedPlannerV21Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericOnlineResidualGuidedPlannerV21Error(message)


def _expression_value(
    expression: Any,
    *,
    state: list[int],
    action: list[int],
    target: int,
    field: int | None,
    constant: int | None,
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (state[target],)
    if expression == ["R01"] and field is not None:
        return (action[field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R03":
        left = _expression_value(
            expression[1],
            state=state,
            action=action,
            target=target,
            field=field,
            constant=constant,
        )
        right = _expression_value(
            expression[2],
            state=state,
            action=action,
            target=target,
            field=field,
            constant=constant,
        )
        if len(left) == len(right) == 1:
            return (left[0] + right[0],)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R04":
        left = _expression_value(
            expression[1],
            state=state,
            action=action,
            target=target,
            field=field,
            constant=constant,
        )
        right = _expression_value(
            expression[2],
            state=state,
            action=action,
            target=target,
            field=field,
            constant=constant,
        )
        if len(left) == len(right) == 1:
            return tuple(sorted({left[0], right[0]}))
    _fail("V21 residual expression escaped the finite grammar")


def _evidence(
    candidate_document: Mapping[str, Any], rows: list[FlatRawTransitionV4]
) -> dict[str, Any]:
    return {
        "layout": candidate_document["layout"],
        "unknown_residual_target_columns": candidate_document[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": [row.to_document() for row in rows],
    }


def run_online_residual_guided_episode_v21(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    residual_prior_library: Mapping[str, Any] | None,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    if maximum_abstract_depth <= 0 or maximum_execution_steps <= 0:
        _fail("V21 planning caps changed")
    candidate_document = candidate.public_document
    layout = candidate_document["layout"]
    state_order = layout["state_canonical_to_raw"]
    action_order = layout["action_canonical_to_raw"]
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
    residual_candidate: dict[str, Any] | None = None
    residual_acquisition: dict[str, Any] | None = None
    residual_synthesis_attempts = 0
    residual_activations = []
    residual_invalidations = 0
    proven_policy_exemplars: list[tuple[tuple[int, ...], int]] = []

    def update_residual_proposal() -> None:
        nonlocal residual_candidate, residual_acquisition
        nonlocal residual_synthesis_attempts, residual_invalidations
        if not local_rows:
            return
        residual_synthesis_attempts += 1
        before = None if residual_candidate is None else residual_candidate["candidate_id"]
        try:
            acquisition = acquire_adaptive_residual_factor_v19(
                _evidence(candidate_document, local_rows),
                prior_library=residual_prior_library,
                confidence_denominator=confidence_denominator,
            )
        except GenericAdaptiveResidualFactorAcquisitionV19Error:
            if residual_candidate is not None:
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
            residual_activations.append(
                {
                    "local_residual_query_count": len(transition_cache),
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

    def residual_score(raw: tuple[int, ...], key: int) -> tuple[Any, ...]:
        if residual_candidate is None:
            return (1, 1, 0, key)
        state = [raw[index] for index in state_order]
        action_raw = adapter.catalogue[key].fields
        action = [action_raw[index] for index in action_order]
        target = residual_candidate["target_column"]
        support = _expression_value(
            residual_candidate["normalized_expression"],
            state=state,
            action=action,
            target=target,
            field=residual_candidate["action_field_binding"],
            constant=residual_candidate["anonymous_integer_constant_binding"],
        )
        current = state[target]
        contains_self = current in support
        maximum_change = max(abs(value - current) for value in support)
        return (contains_self, len(support), -maximum_change, key)

    def residual_delta_signature(
        raw: tuple[int, ...], key: int
    ) -> tuple[int, ...] | None:
        if residual_candidate is None:
            return None
        state = [raw[index] for index in state_order]
        action_raw = adapter.catalogue[key].fields
        action = [action_raw[index] for index in action_order]
        target = residual_candidate["target_column"]
        support = _expression_value(
            residual_candidate["normalized_expression"],
            state=state,
            action=action,
            target=target,
            field=residual_candidate["action_field_binding"],
            constant=residual_candidate["anonymous_integer_constant_binding"],
        )
        return tuple(sorted(value - state[target] for value in support))

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal planning_compute, abstract_plan_attempts, local_labels
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
        partial_rank = {key: index for index, key in enumerate(preferred)}
        if residual_candidate is None:
            return tuple(
                [key for key in preferred if key in legal]
                + [key for key in legal if key not in preferred]
            )
        proven_signatures = {
            signature
            for exemplar_raw, exemplar_key in proven_policy_exemplars
            if (signature := residual_delta_signature(exemplar_raw, exemplar_key))
            is not None
        }

        def transfer_rank(key: int) -> int:
            signature = residual_delta_signature(raw, key)
            return 0 if signature in proven_signatures else 1

        return tuple(
            sorted(
                legal,
                key=lambda key: (
                    transfer_rank(key) if proven_signatures else 1,
                    partial_rank.get(key, len(preferred)),
                    *residual_score(raw, key)[:-1],
                    key,
                ),
            )
        )

    def query(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal local_labels
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        raw = adapter.encode(state)
        index = failure(
            "UNKNOWN_RESIDUAL_PREVENTS_ALL_BRANCH_SAFETY_PROOF", state, key
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
                "failure_index": index,
                "distinction_kind": "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT",
                "raw_state": list(raw),
                "action_key": key,
                "raw_transition_rows": [row.to_document() for row in batch],
                "ground_support_labels": 1,
                "query_after_failed_certificate": True,
            }
        )
        update_residual_proposal()
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
                exemplar = (adapter.encode(state), key)
                if exemplar not in proven_policy_exemplars:
                    proven_policy_exemplars.append(exemplar)
                visiting.remove(state)
                return True
        visiting.remove(state)
        return False

    state = adapter.initial()
    if not solve(state):
        _fail("V21 certificate-local robust proof found no policy")
    action_keys = []
    outcome_tapes = []
    decision = 0
    while adapter.active(state):
        if decision >= maximum_execution_steps:
            _fail("V21 execution crossed its registered cap")
        if state not in policy and not solve(state):
            _fail("V21 receding robust proof did not close")
        key = policy[state]
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
        decision += 1
    if not adapter.success(state):
        _fail("V21 episode terminated outside success")
    final_evidence = _evidence(candidate_document, local_rows)
    final_acquisition = acquire_total_adaptive_residual_factor_v20(
        final_evidence,
        prior_library=residual_prior_library,
        confidence_denominator=confidence_denominator,
    )
    final_replay = replay_total_adaptive_residual_factor_v20(
        final_acquisition, final_evidence
    )
    if local_labels != sum(row["ground_support_labels"] for row in distinctions):
        _fail("V21 local-label accounting changed")
    if len(failed_certificates) != len(distinctions):
        _fail("V21 certificate/distinction pairing changed")
    return {
        "schema": "acfqp.generic_online_residual_guided_episode.v21",
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
        "abstract_plan_attempt_count": abstract_plan_attempts,
        "abstract_planning_compute_events": planning_compute,
        "residual_synthesis_attempt_count": residual_synthesis_attempts,
        "residual_proposal_activations": residual_activations,
        "residual_proposal_invalidation_count": residual_invalidations,
        "proven_residual_policy_exemplar_count": len(proven_policy_exemplars),
        "final_total_residual_acquisition": final_acquisition,
        "final_total_residual_replay": final_replay,
        "failed_certificates": failed_certificates,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "all_ground_queries_followed_failed_certificates": True,
        "partial_and_residual_models_used_only_for_abstract_action_order": True,
        "query_local_exact_overlay_used_for_safety": True,
        "residual_proposal_used_as_safety_authority": False,
        "only_action_conditioned_zero_excess_residual_proposals_guided_ordering": True,
        "complete_residual_world_model_synthesized": False,
        "success": True,
    }


__all__ = ("run_online_residual_guided_episode_v21",)
