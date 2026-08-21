"""Online certificate planning with adaptive post-dependency activation."""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_multi_residual_acquisition_v24 import (
    GenericMultiResidualAcquisitionV24Error,
    acquire_multi_residual_factors_v24,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.generic_post_dependency_residual_v97 import (
    GenericPostDependencyResidualV97Error,
    plan_post_dependency_abstract_program_v97,
    synthesize_post_dependency_multi_residual_v97,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericOnlinePostDependencyCertificatePlannerV98Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericOnlinePostDependencyCertificatePlannerV98Error(message)


def _binding_projection(acquisition: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for candidate in acquisition["compilable_candidates"]:
        if candidate.get("candidate_kind") == "POST_DEPENDENCY_THREE_BAND_FINITE_SUPPORT":
            result.append(
                {
                    "kind": candidate["candidate_kind"],
                    "target_column": candidate["target_column"],
                    "driver_post_column": candidate["driver_post_column"],
                    "lower_inclusive_threshold": candidate[
                        "lower_inclusive_threshold"
                    ],
                    "upper_inclusive_threshold": candidate[
                        "upper_inclusive_threshold"
                    ],
                    "leaf_supports": candidate["leaf_supports"],
                }
            )
        else:
            result.append(
                {
                    "kind": "CALIBRATED_PREDECESSOR",
                    "target_column": candidate["target_column"],
                    "candidate_id": candidate["candidate_id"],
                }
            )
    return result


def _deduplicate(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[FlatRawTransitionV4, ...]:
    unique = {}
    for row in rows:
        unique[(row.pre, row.action.key, row.post)] = row
    return tuple(unique[key] for key in sorted(unique))


def run_online_post_dependency_certificate_episode_v98(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    residual_prior_library: Mapping[str, Any],
    structural_prior_library: Mapping[str, Any] | None,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    confidence_denominator: int = 64,
    maximum_support_branch_evaluations: int = 1_000_000,
    support_feasible_beam_width: int = 16,
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or maximum_abstract_depth <= 0
        or maximum_execution_steps <= 0
        or type(confidence_denominator) is not int
        or confidence_denominator < 2
    ):
        _fail("V98 online dependency inventory changed")
    document = candidate.public_document
    legal_by_raw = {}
    for row in observed_rows:
        legal_by_raw[row.pre] = row.legal_before
        legal_by_raw[row.post] = row.legal_after
    transition_cache = {}
    policy = {}
    visiting = set()
    failures = []
    distinctions = []
    local_rows: list[FlatRawTransitionV4] = []
    local_labels = 0
    partial_attempts = 0
    partial_compute = 0
    synthesis_attempts = 0
    candidate_changes = 0
    invalidations = 0
    issued_at = None
    active_at = None
    active_revisions = 0
    current_projection = None
    current_acquisition = None
    active_acquisition = None
    history = []
    joint_attempts = 0
    joint_successes = 0
    joint_compute = 0
    joint_cache = {}
    confidence_bits = math.ceil(math.log2(confidence_denominator))
    structure_code_units = 1 if structural_prior_library is not None else 8
    required_dependency_evidence_labels = confidence_bits + structure_code_units

    def evidence() -> dict[str, Any]:
        return {
            "layout": document["layout"],
            "unknown_residual_target_columns": document[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": [row.to_document() for row in local_rows],
        }

    def update_model(new_batch: tuple[FlatRawTransitionV4, ...]) -> None:
        nonlocal synthesis_attempts, candidate_changes, invalidations
        nonlocal issued_at, active_at, active_revisions, current_projection
        nonlocal current_acquisition, active_acquisition
        if not local_rows:
            return
        synthesis_attempts += 1
        try:
            base = acquire_multi_residual_factors_v24(
                evidence(),
                prior_library=residual_prior_library,
                confidence_denominator=confidence_denominator,
            )
            acquisition = synthesize_post_dependency_multi_residual_v97(
                evidence(),
                base,
                structural_prior_library=structural_prior_library,
            )
        except (
            GenericMultiResidualAcquisitionV24Error,
            GenericPostDependencyResidualV97Error,
        ):
            if current_projection is not None:
                invalidations += 1
            current_projection = None
            current_acquisition = None
            active_acquisition = None
            issued_at = None
            history.append(
                {
                    "ground_support_labels": local_labels,
                    "candidate_projection_sha256": None,
                    "candidate_issued_at_label": None,
                    "model_evidence_ground_support_labels": 0,
                    "required_model_evidence_ground_support_labels": (
                        required_dependency_evidence_labels
                    ),
                    "activated": False,
                }
            )
            return
        projection = _binding_projection(acquisition)
        projection_sha = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
        complete = acquisition["all_residual_targets_have_compilable_proposals"]
        dependency_count = len(
            acquisition["retrospective_post_dependency_candidates"]
        )
        if current_projection != projection:
            if current_projection is not None:
                candidate_changes += 1
                if active_acquisition is not None:
                    active_revisions += 1
            current_projection = projection
            current_acquisition = acquisition
            issued_at = local_labels
            joint_cache.clear()
        else:
            current_acquisition = acquisition
        evidence_labels = acquisition["shared_physical_ground_support_labels"]
        # The identical MDL/confidence rule is applied in both arms.  A
        # source-derived structure prior changes only the finite structure
        # description length.  Target columns, thresholds and leaf values are
        # still bound from target rows and may be revised as more rows arrive.
        calibrated_only = complete and dependency_count == 0
        required_evidence_labels = (
            confidence_bits
            if calibrated_only
            else required_dependency_evidence_labels
        )
        activated = complete and (
            evidence_labels >= required_evidence_labels
        )
        if activated:
            active_acquisition = acquisition
            if active_at is None:
                active_at = local_labels
        else:
            active_acquisition = None
        history.append(
            {
                "ground_support_labels": local_labels,
                "candidate_projection_sha256": projection_sha,
                "candidate_issued_at_label": issued_at,
                "model_evidence_ground_support_labels": evidence_labels,
                "required_model_evidence_ground_support_labels": (
                    required_evidence_labels
                ),
                "dependency_candidate_count": dependency_count,
                "all_residual_targets_have_compilable_proposals": complete,
                "activated": activated,
            }
        )

    def failure(kind: str, state: Any, key: int | None) -> int:
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

    def partial_preferred(raw: tuple[int, ...]) -> list[int]:
        nonlocal partial_attempts, partial_compute
        partial_attempts += 1
        planning_rows = _deduplicate((*observed_rows, *tuple(local_rows)))
        try:
            plan = plan_partial_factor_observation_graph_v15(
                candidate, planning_rows, adapter.catalogue, raw
            )
        except Exception as first_error:
            if not first_error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            try:
                plan = plan_partial_factor_program_v15(
                    candidate,
                    planning_rows,
                    adapter.catalogue,
                    raw,
                    maximum_depth=maximum_abstract_depth,
                )
            except Exception as second_error:
                if not second_error.__class__.__module__.startswith("acfqp.generic_"):
                    raise
                return []
        partial_compute += plan.get("projected_planning_compute_events", 0)
        return plan["action_keys"][:1]

    def joint_preferred(raw: tuple[int, ...]) -> list[int]:
        nonlocal joint_attempts, joint_successes, joint_compute
        if active_acquisition is None:
            return []
        cache_key = (raw, active_acquisition["multi_residual_acquisition_id"])
        if cache_key in joint_cache:
            cached = joint_cache[cache_key]
            return [] if cached is None else [cached["initial_action_key"]]
        joint_attempts += 1
        try:
            plan = plan_post_dependency_abstract_program_v97(
                candidate,
                _deduplicate((*observed_rows, *tuple(local_rows))),
                adapter.catalogue,
                raw,
                active_acquisition,
                maximum_depth=maximum_abstract_depth,
                maximum_support_branch_evaluations=(
                    maximum_support_branch_evaluations
                ),
                support_feasible_beam_width=support_feasible_beam_width,
            )
        except GenericPostDependencyResidualV97Error:
            joint_cache[cache_key] = None
            return []
        joint_cache[cache_key] = plan
        joint_successes += 1
        joint_compute += plan["abstract_support_branch_evaluations"]
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
        ordered = []
        for key in (*joint_preferred(raw), *partial_preferred(raw), *legal):
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
        typed_batch = tuple(batch)
        local_rows.extend(typed_batch)
        local_labels += 1
        transition_cache[pair] = successors
        distinctions.append(
            {
                "failure_index": index,
                "distinction_kind": "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT",
                "raw_state": list(raw),
                "action_key": key,
                "raw_transition_rows": [row.to_document() for row in typed_batch],
                "ground_support_labels": 1,
                "query_after_failed_certificate": True,
            }
        )
        update_model(typed_batch)
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
        _fail("V98 exact query-local proof found no policy")
    actions = []
    tapes = []
    joint_execution_matches = 0
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in policy and not solve(state):
            _fail("V98 receding exact query-local proof did not close")
        key = policy[state]
        proposed = joint_preferred(adapter.encode(state))
        joint_execution_matches += bool(proposed and proposed[0] == key)
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        actions.append(key)
        tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V98 execution crossed its cap or terminated outside success")
    if local_labels != sum(row["ground_support_labels"] for row in distinctions):
        _fail("V98 local label accounting changed")
    if len(failures) != len(distinctions):
        _fail("V98 certificate/distinction pairing changed")
    payload = {
        "schema": "acfqp.online_post_dependency_certificate_episode.v98",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "arm": (
            "POST_DEPENDENCY_STRUCTURE_META_PRIOR_ON"
            if structural_prior_library is not None
            else "STRICT_NO_POST_DEPENDENCY_STRUCTURE_META_PRIOR"
        ),
        "partial_candidate_id": document["candidate_id"],
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "local_ground_support_labels": local_labels,
        "queried_state_action_count": len(transition_cache),
        "partial_plan_attempt_count": partial_attempts,
        "partial_planning_compute_events": partial_compute,
        "post_dependency_synthesis_attempt_count": synthesis_attempts,
        "candidate_change_count": candidate_changes,
        "candidate_invalidation_count": invalidations,
        "structure_prior_code_units": structure_code_units,
        "confidence_penalty_units": confidence_bits,
        "required_post_dependency_model_evidence_labels": (
            required_dependency_evidence_labels
        ),
        "candidate_activated_at_ground_support_label": active_at,
        "active_candidate_revision_count": active_revisions,
        "adaptive_stopping_history": history,
        "final_post_dependency_acquisition": copy.deepcopy(current_acquisition),
        "active_post_dependency_acquisition": copy.deepcopy(active_acquisition),
        "joint_abstract_plan_attempt_count": joint_attempts,
        "joint_abstract_plan_success_count": joint_successes,
        "joint_abstract_support_branch_evaluations": joint_compute,
        "joint_execution_action_match_count": joint_execution_matches,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "same_synthesizer_and_stopping_rule_between_prior_arms": True,
        "only_switched_variable": "POST_DEPENDENCY_STRUCTURE_DESCRIPTION_CODE_UNITS",
        "activation_is_fallible_mdl_proposal_not_exact_dynamics_authority": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "abstract_model_used_only_for_action_ordering": True,
        "complete_world_model_synthesized": False,
        "success": True,
    }
    return {
        **payload,
        "episode_id": hashlib.sha256(
            b"acfqp:online-post-dependency-certificate-episode:v98\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_online_post_dependency_certificate_episode_v98",)
