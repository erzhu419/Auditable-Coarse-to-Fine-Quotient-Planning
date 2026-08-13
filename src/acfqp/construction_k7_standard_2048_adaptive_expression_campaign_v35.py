"""Run certificate-triggered expression repair and a fresh 2048 segment."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as pre
from acfqp import construction_k7_standard_2048_adaptive_expression_runtime_v35 as adaptive
from acfqp import construction_k7_standard_2048_adaptive_expression_target_v35 as target
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
from acfqp.domains.standard_2048 import (
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_adaptive_expression_campaign_v35"
EXPECTED_CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
V34_ACCOUNTED_CAMPAIGN_ID = "0" * 64
V34_ACCOUNTING_VERIFICATION_ID = "0" * 64
V35_REGISTERED_V34_PREREGISTRATION_ID = (
    "9a02a999b32b3753c4cbfc9dde0baf7b783f661e696875d5bbf97d986bbc3fc5"
)
EXECUTED_V34R1_PREREGISTRATION_ID = (
    "4546af82f1f4e6429c83148b0f37f9a3995b80e9a0bb4abc2971ada13b115920"
)
COLD_EVALUATION_CHECKPOINTS = (0, 63, 127)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_preregistration_v35.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_runtime_v35.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_target_v35.py",
    "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
    "src/acfqp/domains/standard_2048.py",
)


class ConstructionK7Standard2048AdaptiveExpressionCampaignV35Error(RuntimeError):
    """A failed frontier, label, proof, plan, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveExpressionCampaignV35Error(message)


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _fraction(value: Any) -> Fraction:
    if type(value) is Fraction:
        return value
    if type(value) is not dict or set(value) != {"numerator", "denominator"}:
        _fail("adaptive-expression rational document changed")
    return Fraction(value["numerator"], value["denominator"])


def _source_facts() -> list[dict[str, Any]]:
    rows = []
    for relative in SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        rows.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


@dataclass(frozen=True, slots=True)
class _AcquiredModelV35:
    failure: dict[str, Any]
    acquisitions: tuple[dict[str, Any], ...]
    proposal: dict[str, Any]
    proof: dict[str, Any]
    overlay: dict[str, Any]
    control: dict[str, Any]
    candidate: adaptive.ExpressionProgramCandidateV35
    operational_counts: dict[str, int]


def _failure(frontier: tuple[adaptive.RawExpressionContextV35, ...]) -> dict[str, Any]:
    root = state_from_board_v1(pre.INITIAL_BOARDS[0])
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_failure.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": 0,
        "decision_index": 0,
        "root_state": _state_document(root),
        "planning_horizon": pre.PLANNING_HORIZON,
        "frontier_contexts": [context.to_document() for context in frontier],
        "frontier_context_count": len(frontier),
        "frontier_frozen_before_target_probability_query": True,
        "target_probability_query_count_before_failure_freeze": 0,
        "provisional_model_certificate_issued": False,
        "failure_reason": "TARGET_PROBABILITY_UNCOVERED_ON_FROZEN_H3_FRONTIER",
        "next_route": "LOCAL_GROUND_DISTINCTION_ACQUISITION",
    }
    return {
        **payload,
        "adaptive_expression_failure_id": content_id(
            pre.FUTURE_DOMAINS["failure"], payload
        ),
    }


def _acquisition(
    *,
    failure_id: str,
    query_ordinal: int,
    context: adaptive.RawExpressionContextV35,
    observed: Fraction,
    before: int,
    after: int,
    universe_generated: bool,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_acquisition.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_expression_failure_id": failure_id,
        "query_ordinal": query_ordinal,
        "raw_context": context.to_document(),
        "observed_rank_two_probability": _fdoc(observed),
        "candidate_count_before": before,
        "candidate_count_after": after,
        "candidate_universe_generated_after_this_label": universe_generated,
        "context_belongs_to_previously_frozen_failed_frontier": True,
        "full_state_action_outcome_row_materialized": False,
        "label_used_only_for_candidate_consistency": True,
    }
    return {
        **payload,
        "adaptive_expression_acquisition_id": content_id(
            pre.FUTURE_DOMAINS["acquisition"], payload
        ),
    }


def _proposal(
    *,
    failure: dict[str, Any],
    acquisitions: list[dict[str, Any]],
    universe: tuple[adaptive.ExpressionProgramCandidateV35, ...],
    selected: adaptive.ExpressionProgramCandidateV35,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_proposal.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_expression_failure_id": failure["adaptive_expression_failure_id"],
        "acquisition_ids": [
            row["adaptive_expression_acquisition_id"] for row in acquisitions
        ],
        "candidate_universe": [candidate.to_document() for candidate in universe],
        "candidate_universe_count": len(universe),
        "selected_candidate": selected.to_document(),
        "selected_candidate_id": selected.candidate_id,
        "remaining_candidate_count": 1,
        "candidate_universe_frozen_from_first_failed_frontier": True,
        "candidate_universe_expanded_after_first_failure": False,
        "selected_before_target_semantics_document_access": True,
        "proposal_has_world_model_authority": False,
    }
    return {
        **payload,
        "adaptive_expression_proposal_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN,
            payload,
        ),
    }


def _proof(
    proposal: dict[str, Any],
    selected: adaptive.ExpressionProgramCandidateV35,
) -> dict[str, Any]:
    revealed = target.target_semantics_document_v35()
    exact = (
        target.verify_target_commitment_v35() == pre.TARGET_KERNEL_COMMITMENT_ID
        and dict(selected.expression_ast) == revealed["override_expression_ast"]
        and selected.threshold == revealed["override_threshold"]
        and selected.direction == "LE_OVERRIDE"
        and adaptive.BASE_RANK_TWO_PROBABILITY
        == revealed["base_rank_two_probability"]
        and selected.override_probability
        == revealed["override_rank_two_probability"]
    )
    if not exact:
        _fail("selected local expression failed committed semantic proof")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_proof.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_expression_proposal_id": proposal[
            "adaptive_expression_proposal_id"
        ],
        "target_kernel_id": revealed["target_kernel_id"],
        "selected_candidate_id": selected.candidate_id,
        "revealed_target_semantics": revealed,
        "field_equality_rows": [
            {
                "field": "expression_ast",
                "exact_match": dict(selected.expression_ast)
                == revealed["override_expression_ast"],
            },
            {
                "field": "threshold_and_relation",
                "exact_match": selected.threshold == revealed["override_threshold"]
                and selected.direction == "LE_OVERRIDE",
            },
            {
                "field": "base_probability",
                "exact_match": adaptive.BASE_RANK_TWO_PROBABILITY
                == revealed["base_rank_two_probability"],
            },
            {
                "field": "override_probability",
                "exact_match": selected.override_probability
                == revealed["override_rank_two_probability"],
            },
        ],
        "proposal_frozen_before_target_semantics_document_access": True,
        "target_commitment_recomputed_before_comparison": True,
        "exact_program_equivalence_proved": True,
        "proof_probability_label_query_count": 0,
    }
    return {
        **payload,
        "adaptive_expression_proof_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN,
            payload,
        ),
    }


def _overlay(
    proposal: dict[str, Any],
    proof: dict[str, Any],
    selected: adaptive.ExpressionProgramCandidateV35,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_overlay.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_expression_proposal_id": proposal[
            "adaptive_expression_proposal_id"
        ],
        "adaptive_expression_proof_id": proof["adaptive_expression_proof_id"],
        "target_kernel_id": target.TARGET_KERNEL_ID,
        "selected_candidate": selected.to_document(),
        "source_facts": _source_facts(),
        "exact_over_committed_target": True,
        "reusable_across_later_states_actions_and_episodes": True,
        "serialized_state_action_probability_table_present": False,
        "operational_target_probability_query_count_after_overlay_freeze": 0,
    }
    return {
        **payload,
        "adaptive_expression_overlay_id": content_id(
            pre.FUTURE_DOMAINS["overlay"], payload
        ),
    }


def _no_prior_control(
    failure: dict[str, Any],
    frontier: tuple[adaptive.RawExpressionContextV35, ...],
) -> dict[str, Any]:
    rows = [
        {
            "structural_context_sha256": context.context_sha256,
            "rank_two_probability": _fdoc(
                target.query_rank_two_probability_v35(context.post_swipe_board)
            ),
        }
        for context in frontier
    ]
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_ground_control.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_expression_failure_id": failure["adaptive_expression_failure_id"],
        "control_scope": "FIRST_OPERATIONAL_CERTIFICATE_FAILURE_FRONTIER",
        "context_probability_rows": rows,
        "distinct_context_probability_label_count": len(rows),
        "every_distinct_frozen_frontier_context_queried": True,
        "labels_used_to_modify_operational_overlay": False,
        "lane": "STANDALONE_EVALUATION_ONLY",
        "route_or_certificate_authority": False,
    }
    return {
        **payload,
        "adaptive_expression_ground_control_id": content_id(
            pre.FUTURE_DOMAINS["ground_control"], payload
        ),
    }


def _acquire_model() -> _AcquiredModelV35:
    root = state_from_board_v1(pre.INITIAL_BOARDS[0])
    frontier = adaptive.enumerate_raw_frontier_contexts_v35(
        root, horizon=pre.PLANNING_HORIZON
    )
    failure = _failure(frontier)
    contexts_by_id = {context.context_sha256: context for context in frontier}
    labels: dict[str, Fraction] = {}
    candidates: tuple[adaptive.ExpressionProgramCandidateV35, ...] = ()
    universe: tuple[adaptive.ExpressionProgramCandidateV35, ...] = ()
    acquisitions: list[dict[str, Any]] = []
    counters = {
        "model.structural_context_rows_frozen": 0,
        "model.structural_expression_value_evaluations": 0,
        "model.expression_candidates_materialized": 0,
        "model.candidate_label_consistency_checks": 0,
        "model.active_query_partition_evaluations": 0,
        "model.target_probability_labels_acquired": 0,
        "model.exact_program_proof_rows_evaluated": 0,
        "model.world_model_freezes": 0,
    }
    while True:
        decision = adaptive.local_certificate_or_query_v35(
            frontier_contexts=frontier,
            candidates=candidates,
            labels=labels,
        )
        counters["model.active_query_partition_evaluations"] += (
            decision.partition_evaluation_count
        )
        if decision.status == "LOCALLY_CERTIFIED_ALL_SURVIVORS_AGREE":
            if decision.selected_candidate_id is None:
                raise AssertionError("local certificate omitted selected candidate")
            selected = next(
                candidate
                for candidate in candidates
                if candidate.candidate_id == decision.selected_candidate_id
            )
            break
        context_id = decision.next_query_context_sha256
        if context_id is None or context_id not in contexts_by_id:
            _fail("local repair could not select another failed-frontier context")
        if len(acquisitions) >= pre.MAXIMUM_TARGET_PROBABILITY_LABELS:
            _fail("local repair exhausted its target-label cap")
        context = contexts_by_id[context_id]
        observed = target.query_rank_two_probability_v35(context.post_swipe_board)
        labels[context_id] = observed
        before = len(candidates)
        generated = False
        if not universe and any(
            value != adaptive.BASE_RANK_TWO_PROBABILITY
            for value in labels.values()
        ):
            candidates, generated_counts = (
                adaptive.generate_consistent_expression_candidates_v35(
                    archived_contexts=frontier,
                    labels=labels,
                )
            )
            universe = candidates
            for path, value in generated_counts.items():
                counters[path] += value
            generated = True
        elif universe:
            candidates, checks = adaptive.filter_expression_candidates_v35(
                candidates=candidates,
                contexts_by_id=contexts_by_id,
                labels={context_id: observed},
            )
            counters["model.candidate_label_consistency_checks"] += checks
        counters["model.target_probability_labels_acquired"] += 1
        acquisitions.append(
            _acquisition(
                failure_id=failure["adaptive_expression_failure_id"],
                query_ordinal=len(acquisitions),
                context=context,
                observed=observed,
                before=before,
                after=len(candidates),
                universe_generated=generated,
            )
        )
    if not universe or len(candidates) != 1:
        _fail("first failed frontier did not freeze one reusable expression")
    proposal = _proposal(
        failure=failure,
        acquisitions=acquisitions,
        universe=universe,
        selected=selected,
    )
    proof = _proof(proposal, selected)
    counters["model.exact_program_proof_rows_evaluated"] = len(
        proof["field_equality_rows"]
    )
    overlay = _overlay(proposal, proof, selected)
    counters["model.world_model_freezes"] = 1
    control = _no_prior_control(failure, frontier)
    return _AcquiredModelV35(
        failure,
        tuple(acquisitions),
        proposal,
        proof,
        overlay,
        control,
        selected,
        counters,
    )


def _episode(
    task: tuple[int, tuple[int, ...], str, dict[str, Any], dict[str, Any]]
) -> dict[str, Any]:
    episode_index, initial_board, seed, overlay, candidate_document = task
    state = state_from_board_v1(initial_board)
    initial = _state_document(state)
    session = planner.create_expression_planning_session_v1(
        expression_ast=candidate_document["expression_ast"],
        threshold=candidate_document["threshold"],
        base_probability=_fraction(candidate_document["base_rank_two_probability"]),
        override_probability=_fraction(
            candidate_document["override_rank_two_probability"]
        ),
        horizon=pre.PLANNING_HORIZON,
    )
    decisions = []
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model = session.plan_root(state)
        certificate_payload = {
            "schema": "acfqp.standard_2048_adaptive_expression_certificate.v35",
            "schema_version": SCHEMA_VERSION,
            "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
            "adaptive_expression_overlay_id": overlay[
                "adaptive_expression_overlay_id"
            ],
            "adaptive_expression_proof_id": overlay[
                "adaptive_expression_proof_id"
            ],
            "episode_index": episode_index,
            "decision_index": decision_index,
            "root_state": _state_document(state),
            "planning_horizon": pre.PLANNING_HORIZON,
            "root_action_exact_values": model["root_action_exact_values"],
            "selected_action": model["selected_action"],
            "selected_expected_merge_score": model[
                "selected_expected_merge_score"
            ],
            "selected_loss_probability_within_horizon": model[
                "selected_loss_probability_within_horizon"
            ],
            "factored_action_row_evaluation_count": model[
                "factored_action_row_evaluation_count"
            ],
            "factored_support_outcome_evaluation_count": model[
                "factored_support_outcome_evaluation_count"
            ],
            "subproof_cache_hit_count": model["subproof_cache_hit_count"],
            "subproof_cache_miss_count": model["subproof_cache_miss_count"],
            "cross_decision_subproof_cache_hit_count": model[
                "cross_decision_subproof_cache_hit_count"
            ],
            "persistent_subproof_cache_entry_count": model[
                "persistent_subproof_cache_entry_count"
            ],
            "operational_target_probability_query_count_after_overlay_freeze": 0,
            "operational_ground_state_action_row_count": 0,
            "target_transition_accessed_before_certificate_freeze": False,
            "status": "CERTIFIED_PROVED_ADAPTIVE_EXPRESSION_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "adaptive_expression_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], certificate_payload
            ),
        }
        cold = None
        if decision_index in COLD_EVALUATION_CHECKPOINTS:
            cold = planner.evaluate_ground_root_v1(
                state,
                outcome_provider=target.target_outcomes_v35,
                horizon=pre.PLANNING_HORIZON,
            )
            if (
                cold["root_action_exact_values"] != model["root_action_exact_values"]
                or cold["selected_action"] != model["selected_action"]
            ):
                _fail("adaptive expression checkpoint differs from cold ground")
        outcome, tape = select_seeded_outcome_v1(
            target.target_outcomes_v35(
                state, Swipe2048Action(model["selected_action"])
            ),
            seed=seed,
            decision_index=decision_index,
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "PROVED_ADAPTIVE_EXPRESSION_WORLD_MODEL",
                "cold_target_checkpoint": cold,
                "checkpoint_root_values_and_action_exactly_equal": cold is None
                or (
                    cold["root_action_exact_values"]
                    == model["root_action_exact_values"]
                    and cold["selected_action"] == model["selected_action"]
                ),
                "certificate_frozen_before_cold_checkpoint_and_target_transition": True,
                "executed_action": model["selected_action"],
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
                "execution_transition_used_to_modify_world_model": False,
            }
        )
        state = outcome.next_state
    checkpoint_rows = [
        row for row in decisions if row["cold_target_checkpoint"] is not None
    ]
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_episode.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_expression_overlay_id": overlay["adaptive_expression_overlay_id"],
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial,
        "decisions": decisions,
        "decision_count": len(decisions),
        "maximum_registered_decision_count": pre.MAXIMUM_DECISIONS_PER_EPISODE,
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        ),
        "model_certificate_count": len(decisions),
        "cold_evaluation_checkpoint_count": len(checkpoint_rows),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoint_rows
        ),
        "factored_action_row_evaluation_count": sum(
            row["certificate"]["factored_action_row_evaluation_count"]
            for row in decisions
        ),
        "factored_support_outcome_evaluation_count": sum(
            row["certificate"]["factored_support_outcome_evaluation_count"]
            for row in decisions
        ),
        "subproof_cache_hit_count": sum(
            row["certificate"]["subproof_cache_hit_count"] for row in decisions
        ),
        "subproof_cache_miss_count": sum(
            row["certificate"]["subproof_cache_miss_count"] for row in decisions
        ),
        "cross_decision_subproof_cache_hit_count": sum(
            row["certificate"]["cross_decision_subproof_cache_hit_count"]
            for row in decisions
        ),
        "final_state": _state_document(state),
        "maximum_final_board_tile_rank": max(state.board),
        "tile_2048_reached": max(state.board) >= GOAL_RANK,
    }
    return {
        **payload,
        "adaptive_expression_episode_id": content_id(
            pre.FUTURE_DOMAINS["episode"], payload
        ),
    }


def _assemble_campaign_document(
    preregistration: dict[str, Any],
    acquired: _AcquiredModelV35,
    episode_documents: list[dict[str, Any]],
) -> dict[str, Any]:
    episodes = sorted(episode_documents, key=lambda row: row["episode_index"])
    if (
        len(episodes) != len(pre.INITIAL_BOARDS)
        or [row.get("episode_index") for row in episodes]
        != list(range(len(pre.INITIAL_BOARDS)))
    ):
        _fail("adaptive-expression episode inventory changed")
    decisions = [row for episode in episodes for row in episode["decisions"]]
    checkpoints = [
        row for row in decisions if row["cold_target_checkpoint"] is not None
    ]
    adaptive_labels = len(acquired.acquisitions)
    control_labels = acquired.control["distinct_context_probability_label_count"]
    if not 0 < adaptive_labels < control_labels:
        _fail("adaptive acquisition did not reduce the registered label count")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_campaign.v35",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "adaptive_expression_preregistration": preregistration,
        "additive_role_domains": {
            "proposal": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN,
            "proof": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN,
            "roles_are_not_reused_as_overlay_or_plan_certificate": True,
        },
        "preexecution_v34_accounting_binding": {
            "v35_registered_v34_preregistration_id": (
                V35_REGISTERED_V34_PREREGISTRATION_ID
            ),
            "executed_v34r1_preregistration_id": (
                EXECUTED_V34R1_PREREGISTRATION_ID
            ),
            "v34_accounted_campaign_id": V34_ACCOUNTED_CAMPAIGN_ID,
            "v34_accounting_verification_id": V34_ACCOUNTING_VERIFICATION_ID,
            "failed_v34_predecessor_preserved": True,
            "resource_cap_successor_preserves_scientific_workload": True,
            "partial_failed_predecessor_bundles_reused": False,
            "verified_before_first_target_probability_query": True,
        },
        "certificate_failure": acquired.failure,
        "expression_acquisitions": list(acquired.acquisitions),
        "expression_proposal": acquired.proposal,
        "expression_proof": acquired.proof,
        "expression_overlay": acquired.overlay,
        "matched_no_prior_first_frontier_control": acquired.control,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "model_certificate_count": len(decisions),
        "certificate_failure_count": 1,
        "ground_distinction_query_count": adaptive_labels,
        "first_frontier_no_prior_label_count": control_labels,
        "ground_distinction_label_reduction": control_labels - adaptive_labels,
        "adaptive_label_fraction_of_no_prior": Fraction(
            adaptive_labels, control_labels
        ),
        "certified_decisions_per_ground_distinction_label": Fraction(
            len(decisions), adaptive_labels
        ),
        "candidate_universe_count": acquired.proposal["candidate_universe_count"],
        "final_candidate_count": acquired.proposal["remaining_candidate_count"],
        "overlay_freeze_count": 1,
        "operational_target_probability_query_count_after_overlay_freeze": 0,
        "online_target_transition_observation_count": len(decisions),
        "cold_evaluation_checkpoint_count": len(checkpoints),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoints
        ),
        "model_operational_counter_values": acquired.operational_counts,
        "planning_factored_action_row_evaluation_count": sum(
            episode["factored_action_row_evaluation_count"] for episode in episodes
        ),
        "planning_factored_support_outcome_evaluation_count": sum(
            episode["factored_support_outcome_evaluation_count"]
            for episode in episodes
        ),
        "planning_subproof_cache_hit_count": sum(
            episode["subproof_cache_hit_count"] for episode in episodes
        ),
        "planning_subproof_cache_miss_count": sum(
            episode["subproof_cache_miss_count"] for episode in episodes
        ),
        "planning_cross_decision_subproof_cache_hit_count": sum(
            episode["cross_decision_subproof_cache_hit_count"]
            for episode in episodes
        ),
        "evaluation_no_prior_probability_label_count": control_labels,
        "evaluation_cold_target_ground_state_action_row_count": sum(
            row["cold_target_checkpoint"]["ground_state_action_row_count"]
            for row in checkpoints
        ),
        "evaluation_cold_target_ground_outcome_count": sum(
            row["cold_target_checkpoint"]["ground_outcome_count"]
            for row in checkpoints
        ),
        "sample_tax_reduced_on_registered_first_failure_label_axis": True,
        "all_plans_after_repair_use_proved_reusable_expression_model": True,
        "target_queries_restricted_to_previously_failed_frontier": True,
        "matched_control_labels_excluded_from_operational_overlay": True,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "formal_native_accounting_successor_required": True,
        "full_standard_2048_game_claimed": False,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "adaptive_expression_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


def _campaign_document() -> dict[str, Any]:
    if (
        V34_ACCOUNTED_CAMPAIGN_ID == "0" * 64
        or V34_ACCOUNTING_VERIFICATION_ID == "0" * 64
    ):
        _fail("V34 accounting predecessor has not been frozen")
    preregistration = pre.freeze_standard_2048_adaptive_expression_preregistration_v35()
    acquired = _acquire_model()
    candidate_document = acquired.candidate.to_document()
    tasks = tuple(
        (
            index,
            board,
            pre.EPISODE_SEEDS[index],
            acquired.overlay,
            candidate_document,
        )
        for index, board in enumerate(pre.INITIAL_BOARDS)
    )
    episodes = []
    for start in range(0, len(tasks), pre.MAXIMUM_WORKER_PROCESSES):
        batch = tasks[start : start + pre.MAXIMUM_WORKER_PROCESSES]
        executors = [ProcessPoolExecutor(max_workers=1) for _ in batch]
        try:
            futures = [
                executor.submit(_episode, task)
                for executor, task in zip(executors, batch, strict=True)
            ]
            episodes.extend(future.result() for future in futures)
        finally:
            for executor in executors:
                executor.shutdown(wait=True, cancel_futures=True)
    return _assemble_campaign_document(
        preregistration.to_document(), acquired, episodes
    )


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveExpressionCampaignV35:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("adaptive-expression campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("adaptive-expression campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_expression_campaign_id"
        }
        if (
            document.get("adaptive_expression_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload)
            != self.campaign_id
        ):
            _fail("adaptive-expression campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("adaptive-expression campaign is not an object")
        return document


def run_standard_2048_adaptive_expression_campaign_v35(
) -> Standard2048AdaptiveExpressionCampaignV35:
    document = _campaign_document()
    raw = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["adaptive_expression_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen adaptive-expression campaign changed")
    return Standard2048AdaptiveExpressionCampaignV35(
        _ISSUER, raw, document["adaptive_expression_campaign_id"]
    )


def verify_standard_2048_adaptive_expression_campaign_v35(
    value: Standard2048AdaptiveExpressionCampaignV35,
) -> Standard2048AdaptiveExpressionCampaignV35:
    if type(value) is not Standard2048AdaptiveExpressionCampaignV35:
        _fail("adaptive-expression campaign verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != run_standard_2048_adaptive_expression_campaign_v35().canonical_bytes:
        _fail("adaptive-expression campaign differs from semantic replay")
    document = value.to_document()
    if (
        document["certificate_failure_count"] != 1
        or document["ground_distinction_query_count"]
        >= document["first_frontier_no_prior_label_count"]
        or document["all_checkpoint_root_values_and_actions_exactly_equal"] is not True
        or document[
            "operational_target_probability_query_count_after_overlay_freeze"
        ]
        != 0
        or document["official_execution_allowed"] is not False
    ):
        _fail("adaptive-expression result or claim locks changed")
    return value


__all__ = (
    "COLD_EVALUATION_CHECKPOINTS",
    "ConstructionK7Standard2048AdaptiveExpressionCampaignV35Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048AdaptiveExpressionCampaignV35",
    "run_standard_2048_adaptive_expression_campaign_v35",
    "verify_standard_2048_adaptive_expression_campaign_v35",
)
