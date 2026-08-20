"""Online certificate planner with jointly selected transition/terminal programs."""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_batch_exact_multi_residual_compiler_v27 import (
    GenericBatchExactMultiResidualCompilerV27Error,
    compile_batch_exact_multi_residual_support_v27,
    replay_batch_exact_multi_residual_support_v27,
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
from acfqp.generic_relational_residual_abstract_planner_v29 import (
    GenericRelationalResidualAbstractPlannerV29Error,
    plan_relational_residual_abstract_frontier_v29,
)
from acfqp.generic_relational_terminal_program_v28 import (
    GenericRelationalTerminalProgramV28Error,
    synthesize_relational_terminal_program_v28,
)


class GenericRelationalWorldModelCertificatePlannerV30Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericRelationalWorldModelCertificatePlannerV30Error(message)


def run_relational_world_model_certificate_episode_v30(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    residual_prior_library: Mapping[str, Any] | None,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    confidence_denominator: int = 64,
    maximum_terminal_program_candidates_to_try: int = 32,
    maximum_relational_support_branch_evaluations: int = 1_000_000,
    relational_support_feasible_beam_width: int = 32,
) -> dict[str, Any]:
    if maximum_abstract_depth <= 0 or maximum_execution_steps <= 0:
        _fail("V30 planning caps changed")
    document = candidate.public_document
    legal_by_raw: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in observed_rows:
        legal_by_raw[row.pre] = row.legal_before
        legal_by_raw[row.post] = row.legal_after
    transition_cache: dict[tuple[Any, int], tuple[Any, ...]] = {}
    exact_policy: dict[Any, int] = {}
    visiting: set[Any] = set()
    failures: list[dict[str, Any]] = []
    distinctions: list[dict[str, Any]] = []
    local_rows: list[FlatRawTransitionV4] = []
    local_labels = 0
    partial_attempts = 0
    partial_compute = 0
    synthesis_attempts = 0
    synthesis_invalidations = 0
    active_bundle: tuple[dict[str, Any], dict[str, Any]] | None = None
    activations: list[dict[str, Any]] = []
    plan_attempts = 0
    plan_successes = 0
    plan_compute = 0
    terminal_candidates_attempted = 0
    terminal_candidates_rejected = 0
    robust_closures = 0
    resource_truncations = 0
    plan_cache: dict[tuple[tuple[int, ...], str, str], dict[str, Any] | None] = {}

    def evidence() -> dict[str, Any]:
        return {
            "layout": document["layout"],
            "unknown_residual_target_columns": document[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": [row.to_document() for row in local_rows],
        }

    def terminal_evidence() -> dict[str, Any]:
        return {
            "layout": document["layout"],
            "unknown_residual_target_columns": document[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": [
                *(row.to_document() for row in observed_rows),
                *(row.to_document() for row in local_rows),
            ],
        }

    def update_bundle() -> None:
        nonlocal synthesis_attempts, synthesis_invalidations, active_bundle
        if not local_rows:
            return
        synthesis_attempts += 1
        before = (
            None
            if active_bundle is None
            else (
                active_bundle[0]["batch_exact_multi_residual_id"],
                active_bundle[1]["terminal_program_id"],
            )
        )
        try:
            acquisition = acquire_multi_residual_factors_v24(
                evidence(),
                prior_library=residual_prior_library,
                confidence_denominator=confidence_denominator,
            )
            exact = compile_batch_exact_multi_residual_support_v27(
                acquisition,
                evidence(),
                prior_library=residual_prior_library,
            )
            terminal = synthesize_relational_terminal_program_v28(
                terminal_evidence(), maximum_program_candidates=32
            )
            status_target = terminal["status_target_column"]
            residual_targets = {
                row["target_column"] for row in exact["joint_batch_exact_candidates"]
            }
            if residual_targets | {status_target} != set(
                document["unknown_residual_target_columns"]
            ):
                raise GenericRelationalResidualAbstractPlannerV29Error(
                    "V30 residual and terminal programs do not cover the complement"
                )
        except (
            GenericMultiResidualAcquisitionV24Error,
            GenericBatchExactMultiResidualCompilerV27Error,
            GenericRelationalTerminalProgramV28Error,
            GenericRelationalResidualAbstractPlannerV29Error,
        ):
            if before is not None:
                synthesis_invalidations += 1
            active_bundle = None
            return
        active_bundle = (exact, terminal)
        after = (exact["batch_exact_multi_residual_id"], terminal["terminal_program_id"])
        if before != after:
            plan_cache.clear()
            activations.append(
                {
                    "local_transition_query_count": len(transition_cache),
                    "batch_exact_multi_residual_id": after[0],
                    "terminal_program_id": after[1],
                    "batch_exact_residual_candidate_count": exact[
                        "joint_batch_exact_candidate_count"
                    ],
                    "terminal_candidate_count": terminal[
                        "decision_tree_candidate_count"
                    ],
                    "all_observed_state_coordinates_represented": True,
                }
            )

    def fail_certificate(kind: str, state: Any, key: int | None) -> int:
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
        try:
            plan = plan_partial_factor_observation_graph_v15(
                candidate, observed_rows, adapter.catalogue, raw
            )
            partial_compute += plan["projected_planning_compute_events"]
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
                partial_compute += plan["projected_planning_compute_events"]
                return plan["action_keys"][:1]
            except Exception:
                return []

    def relational_preferred(raw: tuple[int, ...]) -> list[int]:
        nonlocal plan_attempts, plan_successes, plan_compute
        nonlocal terminal_candidates_attempted, terminal_candidates_rejected
        nonlocal robust_closures, resource_truncations
        if active_bundle is None:
            return []
        exact, terminal = active_bundle
        key = (
            raw,
            exact["batch_exact_multi_residual_id"],
            terminal["terminal_program_id"],
        )
        if key in plan_cache:
            cached = plan_cache[key]
            return [] if cached is None else [cached["initial_action_key"]]
        plan_attempts += 1
        try:
            plan = plan_relational_residual_abstract_frontier_v29(
                candidate,
                observed_rows,
                adapter.catalogue,
                raw,
                exact,
                terminal,
                maximum_depth=maximum_abstract_depth,
                maximum_terminal_program_candidates_to_try=(
                    maximum_terminal_program_candidates_to_try
                ),
                maximum_support_branch_evaluations=(
                    maximum_relational_support_branch_evaluations
                ),
                support_feasible_beam_width=(
                    relational_support_feasible_beam_width
                ),
            )
        except GenericRelationalResidualAbstractPlannerV29Error:
            plan_cache[key] = None
            return []
        plan_cache[key] = plan
        plan_successes += 1
        plan_compute += plan["abstract_support_branch_evaluations"]
        terminal_candidates_attempted += plan["terminal_candidate_attempt_count"]
        terminal_candidates_rejected += len(plan["rejected_terminal_candidate_attempts"])
        robust_closures += plan["robust_all_modeled_branches_closed"] is True
        resource_truncations += plan["robust_search_resource_cap_reached"] is True
        return [plan["initial_action_key"]]

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal local_labels
        raw = adapter.encode(state)
        legal = legal_by_raw.get(raw)
        if legal is None:
            index = fail_certificate("MISSING_QUERY_LOCAL_LEGALITY_SUPPORT", state, None)
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
        relational = relational_preferred(raw)
        partial = partial_preferred(raw)
        ordered = []
        for key in (*relational, *partial, *legal):
            if key in legal and key not in ordered:
                ordered.append(key)
        return tuple(ordered)

    def query(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal local_labels
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        raw = adapter.encode(state)
        index = fail_certificate(
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
        update_bundle()
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
        _fail("V30 exact query-local proof found no policy")
    action_keys = []
    outcome_tapes = []
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in exact_policy and not solve(state):
            _fail("V30 receding exact query-local proof did not close")
        key = exact_policy[state]
        outcome, tape = adapter.select_outcome(state, key, episode_index, decision)
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V30 execution crossed its cap or terminated outside success")
    final_multi = acquire_multi_residual_factors_v24(
        evidence(),
        prior_library=residual_prior_library,
        confidence_denominator=confidence_denominator,
    )
    final_multi_replay = replay_multi_residual_factors_v24(
        final_multi,
        evidence(),
        prior_library=residual_prior_library,
        confidence_denominator=confidence_denominator,
    )
    final_exact = compile_batch_exact_multi_residual_support_v27(
        final_multi, evidence(), prior_library=residual_prior_library
    )
    final_exact_replay = replay_batch_exact_multi_residual_support_v27(
        final_exact,
        final_multi,
        evidence(),
        prior_library=residual_prior_library,
    )
    final_terminal = synthesize_relational_terminal_program_v28(terminal_evidence())
    if local_labels != sum(row["ground_support_labels"] for row in distinctions):
        _fail("V30 local-label accounting changed")
    if len(failures) != len(distinctions):
        _fail("V30 certificate/distinction pairing changed")
    return {
        "schema": "acfqp.generic_relational_world_model_certificate_episode.v30",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "arm": (
            "RESIDUAL_FACTOR_PRIOR_ON"
            if residual_prior_library is not None
            else "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
        ),
        "partial_candidate_id": document["candidate_id"],
        "action_keys": action_keys,
        "outcome_tape_sha256": outcome_tapes,
        "execution_steps": len(action_keys),
        "local_ground_support_labels": local_labels,
        "queried_state_action_count": len(transition_cache),
        "partial_plan_attempt_count": partial_attempts,
        "partial_planning_compute_events": partial_compute,
        "relational_world_model_synthesis_attempt_count": synthesis_attempts,
        "relational_world_model_invalidation_count": synthesis_invalidations,
        "relational_world_model_activations": activations,
        "relational_abstract_plan_attempt_count": plan_attempts,
        "relational_abstract_plan_success_count": plan_successes,
        "relational_abstract_support_branch_evaluations": plan_compute,
        "terminal_program_candidate_attempt_count": terminal_candidates_attempted,
        "terminal_program_candidate_rejection_count": terminal_candidates_rejected,
        "relational_abstract_robust_closure_count": robust_closures,
        "relational_abstract_resource_truncation_count": resource_truncations,
        "final_multi_residual_acquisition": final_multi,
        "final_multi_residual_replay": final_multi_replay,
        "final_batch_exact_residual_support": final_exact,
        "final_batch_exact_residual_replay": final_exact_replay,
        "final_relational_terminal_program": final_terminal,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "all_observed_state_coordinates_represented_when_model_active": True,
        "terminal_and_transition_programs_jointly_selected_for_abstract_planning": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "relational_abstract_plan_used_as_safety_authority": False,
        "empirical_support_promoted_to_global_exact_dynamics": False,
        "complete_world_model_synthesized": False,
        "success": True,
    }


__all__ = ("run_relational_world_model_certificate_episode_v30",)
