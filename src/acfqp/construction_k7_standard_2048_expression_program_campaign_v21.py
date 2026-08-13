"""Synthesize a structural expression, acquire four labels, prove, and plan."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_context_program_campaign_v20 as planner_v20
from acfqp import construction_k7_standard_2048_expression_program_preregistration_v21 as pre
from acfqp import construction_k7_standard_2048_local_dynamics_kernel_v18 as kernel
from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as swipe_v14
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_expression_program_campaign_v21"
MAXIMUM_PROCESSES = 3
EXPECTED_CAMPAIGN_ID = "264749b3f9b4bd44d289476f829b0fc88076828ae7747a2a3b6c12fb6af75d4f"
EXPECTED_CANONICAL_BYTE_COUNT = 188437
EXPECTED_CANONICAL_SHA256 = "745d95599a7e3e0396dbe78aa432048ac0a0cb7b2d44e289e4b740057485b5de"
SELECTED_SWIPE_PROGRAM = "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP"
BASE_RATE = Fraction(1, 10)
ExpressionCandidate = tuple[str, dict[str, Any], int, Fraction, tuple[Fraction, ...]]


class ConstructionK7Standard2048ExpressionProgramCampaignV21Error(ValueError):
    """The expression pool, active acquisition, proof, or planning changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionProgramCampaignV21Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _fraction(value: Any) -> Fraction:
    if type(value) is Fraction:
        return value
    if type(value) is not dict or set(value) != {"numerator", "denominator"}:
        _fail("rational document changed")
    return Fraction(value["numerator"], value["denominator"])


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@lru_cache(maxsize=None)
def _swipe(board: tuple[int, ...], action: str) -> tuple[tuple[int, ...], int]:
    return swipe_v14.apply_observation_proposed_swipe_program_v14(
        board, action, candidate_key=SELECTED_SWIPE_PROGRAM
    )


def _adjacent_equal_nonzero(board: tuple[int, ...]) -> int:
    return sum(
        1
        for row in range(4)
        for column in range(4)
        for delta_row, delta_column in ((0, 1), (1, 0))
        if row + delta_row < 4
        and column + delta_column < 4
        and board[row * 4 + column] != 0
        and board[row * 4 + column]
        == board[(row + delta_row) * 4 + column + delta_column]
    )


def _expression_inventory(
    pre_board: tuple[int, ...],
    action: str,
    post_board: tuple[int, ...],
    merge_score: int,
    constants: tuple[int, ...],
) -> list[dict[str, Any]]:
    rows = []
    for source_name, board in (
        ("PRE_BOARD_RANKS", pre_board),
        ("POST_SWIPE_BOARD_RANKS", post_board),
    ):
        for constant in constants:
            rows.append(
                {
                    "expression_key": f"COUNT_EQ({source_name},{constant})",
                    "expression_ast": {
                        "operator": "COUNT_EQ",
                        "vector_source": source_name,
                        "constant": constant,
                    },
                    "value": board.count(constant),
                }
            )
        for operator, value in (
            ("MAX", max(board)),
            ("SUM", sum(board)),
            ("DISTINCT_NONZERO_COUNT", len(set(board) - {0})),
            ("ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT", _adjacent_equal_nonzero(board)),
        ):
            rows.append(
                {
                    "expression_key": f"{operator}({source_name})",
                    "expression_ast": {"operator": operator, "vector_source": source_name},
                    "value": value,
                }
            )
    rows.extend(
        (
            {
                "expression_key": "MERGE_SCORE",
                "expression_ast": {"operator": "RAW_SCALAR", "source": "MERGE_SCORE"},
                "value": merge_score,
            },
            {
                "expression_key": "ACTION_ORDINAL",
                "expression_ast": {"operator": "RAW_SCALAR", "source": "ACTION_ORDINAL"},
                "value": tuple(item.value for item in ACTION_ORDER).index(action),
            },
        )
    )
    if len({row["expression_key"] for row in rows}) != len(rows):
        _fail("structural expression keys are not unique")
    return rows


def _context_pool() -> dict[str, Any]:
    structural = []
    constants = set()
    for ordinal, (board, action) in enumerate(pre.RAW_CONTEXT_POOL):
        post_board, merge_score = _swipe(board, action)
        if post_board == board:
            _fail("raw context contains an illegal no-op action")
        structural.append((ordinal, board, action, post_board, merge_score))
        constants.update(board)
        constants.update(post_board)
    frozen_constants = tuple(sorted(constants))
    rows = []
    for ordinal, board, action, post_board, merge_score in structural:
        expressions = _expression_inventory(
            board, action, post_board, merge_score, frozen_constants
        )
        raw_payload = {
            "pool_ordinal": ordinal,
            "pre_state_board_ranks": list(board),
            "action": action,
            "post_swipe_board_ranks": list(post_board),
            "merge_score": merge_score,
            "expression_values": expressions,
        }
        rows.append(
            {
                **raw_payload,
                "structural_context_sha256": hashlib.sha256(
                    canonical_json_bytes(raw_payload)
                ).hexdigest(),
            }
        )
    payload = {
        "schema": "acfqp.standard_2048_structural_context_pool.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": pre.PREREGISTRATION_ID,
        "swipe_world_model_id": swipe_v14.FACTORED_WORLD_MODEL_ID,
        "observed_raw_rank_constants": list(frozen_constants),
        "rows": rows,
        "context_count": len(rows),
        "expression_count_per_context": len(rows[0]["expression_values"]),
        "all_expression_values_frozen_before_first_target_probability_query": True,
        "target_probability_or_formula_present": False,
        "named_empty_count_or_v20_feature_basis_present": False,
    }
    return {
        **payload,
        "structural_context_pool_id": content_id(pre.FUTURE_DOMAINS["context_pool"], payload),
    }


def _expression_maps(pool: dict[str, Any]) -> tuple[tuple[str, dict[str, Any], tuple[int, ...]], ...]:
    rows = pool["rows"]
    first = rows[0]["expression_values"]
    result = []
    for index, expression in enumerate(first):
        key = expression["expression_key"]
        ast = expression["expression_ast"]
        values = []
        for row in rows:
            item = row["expression_values"][index]
            if item["expression_key"] != key or item["expression_ast"] != ast:
                _fail("expression inventory order changed across contexts")
            values.append(item["value"])
        result.append((key, ast, tuple(values)))
    return tuple(result)


def _candidate_artifacts(
    pool: dict[str, Any], override: Fraction
) -> tuple[list[dict[str, Any]], tuple[ExpressionCandidate, ...]]:
    artifacts = []
    native = []
    ordinal = 0
    for key, ast, values in _expression_maps(pool):
        for threshold in sorted(set(values)):
            predictions = tuple(
                override if value <= threshold else BASE_RATE for value in values
            )
            if len(set(predictions)) == 1:
                continue
            payload = {
                "schema": "acfqp.standard_2048_expression_candidate.v21",
                "schema_version": SCHEMA_VERSION,
                "expression_program_preregistration_id": pre.PREREGISTRATION_ID,
                "structural_context_pool_id": pool["structural_context_pool_id"],
                "candidate_ordinal": ordinal,
                "expression_key": key,
                "expression_ast": ast,
                "threshold": threshold,
                "program_schema": "IF_EXPRESSION_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
                "base_rank_two_probability": _fdoc(BASE_RATE),
                "override_rank_two_probability": _fdoc(override),
                "expression_values_over_frozen_pool": list(values),
                "predictions_over_frozen_pool": [_fdoc(value) for value in predictions],
                "constant_prediction_candidate": False,
                "expression_and_threshold_generated_from_structural_pool": True,
            }
            artifact = {
                **payload,
                "expression_candidate_id": content_id(
                    pre.FUTURE_DOMAINS["candidate"], payload
                ),
            }
            artifacts.append(artifact)
            native.append((key, ast, threshold, override, predictions))
            ordinal += 1
    return artifacts, tuple(native)


def _query(
    *, pool: dict[str, Any], pool_ordinal: int, query_ordinal: int,
    candidate_count_before: int | None, candidate_count_after: int,
    candidates_generated_after_query: bool,
) -> dict[str, Any]:
    row = pool["rows"][pool_ordinal]
    empty_count = row["post_swipe_board_ranks"].count(0)
    observed = kernel.query_rank_two_probability_v18(empty_count)
    payload = {
        "schema": "acfqp.standard_2048_expression_acquisition.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": pre.PREREGISTRATION_ID,
        "structural_context_pool_id": pool["structural_context_pool_id"],
        "query_ordinal": query_ordinal,
        "pool_ordinal": pool_ordinal,
        "structural_context_sha256": row["structural_context_sha256"],
        "observed_rank_two_probability": _fdoc(observed),
        "candidate_count_before": candidate_count_before,
        "candidate_count_after": candidate_count_after,
        "candidates_generated_after_this_query": candidates_generated_after_query,
        "context_and_all_expression_values_frozen_before_query": True,
        "full_state_action_outcome_row_materialized": False,
    }
    return {
        **payload,
        "expression_acquisition_id": content_id(pre.FUTURE_DOMAINS["acquisition"], payload),
    }


def _active_acquire(
    pool: dict[str, Any], artifacts: list[dict[str, Any]],
    candidates: tuple[ExpressionCandidate, ...], first_observation: Fraction,
) -> tuple[list[dict[str, Any]], tuple[ExpressionCandidate, ...]]:
    query_ordinals = [0]
    observed = {0: first_observation}
    remaining = tuple(
        candidate for candidate in candidates if candidate[4][0] == first_observation
    )
    acquisitions = [
        _query(
            pool=pool, pool_ordinal=0, query_ordinal=0,
            candidate_count_before=None, candidate_count_after=len(remaining),
            candidates_generated_after_query=True,
        )
    ]
    while len(remaining) > 1:
        choices = []
        for pool_ordinal in range(len(pool["rows"])):
            if pool_ordinal in query_ordinals:
                continue
            buckets: dict[Fraction, int] = {}
            for candidate in remaining:
                prediction = candidate[4][pool_ordinal]
                buckets[prediction] = buckets.get(prediction, 0) + 1
            if len(buckets) > 1:
                choices.append((max(buckets.values()), pool_ordinal))
        if not choices:
            _fail("active expression version space cannot be separated")
        _, pool_ordinal = min(choices)
        query_ordinals.append(pool_ordinal)
        before = remaining
        empty_count = pool["rows"][pool_ordinal]["post_swipe_board_ranks"].count(0)
        value = kernel.query_rank_two_probability_v18(empty_count)
        observed[pool_ordinal] = value
        remaining = tuple(
            candidate for candidate in remaining if candidate[4][pool_ordinal] == value
        )
        if not remaining or len(remaining) >= len(before):
            _fail("active expression query did not shrink version space")
        acquisitions.append(
            _query(
                pool=pool, pool_ordinal=pool_ordinal,
                query_ordinal=len(acquisitions),
                candidate_count_before=len(before),
                candidate_count_after=len(remaining),
                candidates_generated_after_query=False,
            )
        )
        if len(acquisitions) > pre.MAXIMUM_TARGET_PROBABILITY_QUERIES:
            _fail("expression acquisition exceeded preregistered query budget")
    if len(remaining) != 1:
        _fail("active expression acquisition did not select one program")
    return acquisitions, remaining


def _proposal(
    pool: dict[str, Any], artifacts: list[dict[str, Any]],
    acquisitions: list[dict[str, Any]], selected: ExpressionCandidate,
) -> dict[str, Any]:
    selected_artifact = next(
        row for row in artifacts
        if row["expression_key"] == selected[0]
        and row["expression_ast"] == selected[1]
        and row["threshold"] == selected[2]
    )
    payload = {
        "schema": "acfqp.standard_2048_expression_proposal.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": pre.PREREGISTRATION_ID,
        "structural_context_pool_id": pool["structural_context_pool_id"],
        "expression_candidate_artifacts": artifacts,
        "expression_candidate_count": len(artifacts),
        "expression_acquisition_ids": [row["expression_acquisition_id"] for row in acquisitions],
        "queried_pool_ordinals": [row["pool_ordinal"] for row in acquisitions],
        "version_space_counts_after_queries": [row["candidate_count_after"] for row in acquisitions],
        "selected_expression_candidate_id": selected_artifact["expression_candidate_id"],
        "selected_expression_key": selected[0],
        "selected_expression_ast": selected[1],
        "selected_threshold": selected[2],
        "selected_base_rank_two_probability": _fdoc(BASE_RATE),
        "selected_override_rank_two_probability": _fdoc(selected[3]),
        "unique_program_consistent_with_all_queried_contexts": True,
        "named_empty_count_feature_supplied_to_synthesizer": False,
        "proposal_frozen_before_target_formula_access": True,
        "proposal_has_world_model_authority": False,
    }
    return {
        **payload,
        "expression_proposal_id": content_id(pre.FUTURE_DOMAINS["proposal"], payload),
    }


def _proof(proposal: dict[str, Any]) -> dict[str, Any]:
    ast = proposal["selected_expression_ast"]
    if ast != {
        "operator": "COUNT_EQ",
        "vector_source": "POST_SWIPE_BOARD_RANKS",
        "constant": 0,
    }:
        _fail("selected expression does not normalize to post-swipe empty count")
    threshold = proposal["selected_threshold"]
    override = _fraction(proposal["selected_override_rank_two_probability"])
    rows = []
    for empty_count in range(1, 17):
        predicted = override if empty_count <= threshold else BASE_RATE
        target = kernel.query_rank_two_probability_v18(empty_count)
        rows.append(
            {
                "post_swipe_empty_count": empty_count,
                "normalized_expression_value": empty_count,
                "predicted_rank_two_probability": _fdoc(predicted),
                "target_rank_two_probability": _fdoc(target),
                "exact_match": predicted == target,
            }
        )
    mismatch_count = sum(row["exact_match"] is not True for row in rows)
    if mismatch_count:
        _fail("expression program failed exact target proof")
    payload = {
        "schema": "acfqp.standard_2048_expression_proof.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": pre.PREREGISTRATION_ID,
        "expression_proposal_id": proposal["expression_proposal_id"],
        "proposal_frozen_before_target_formula_access": True,
        "normalization_rewrite": "COUNT_EQ(POST_SWIPE_BOARD_RANKS,0)=POST_SWIPE_EMPTY_COUNT",
        "proof_rows": rows,
        "proof_row_count": len(rows),
        "proof_mismatch_count": mismatch_count,
        "exact_formula_equivalence_proved": True,
        "proof_rows_not_counted_as_target_probability_queries": True,
    }
    return {
        **payload,
        "expression_proof_id": content_id(pre.FUTURE_DOMAINS["proof"], payload),
    }


def _world_model(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_world_model.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": pre.PREREGISTRATION_ID,
        "expression_proposal_id": proposal["expression_proposal_id"],
        "expression_proof_id": proof["expression_proof_id"],
        "swipe_world_model_id": swipe_v14.FACTORED_WORLD_MODEL_ID,
        "selected_expression_ast": proposal["selected_expression_ast"],
        "selected_threshold": proposal["selected_threshold"],
        "base_rank_two_probability": proposal["selected_base_rank_two_probability"],
        "override_rank_two_probability": proposal["selected_override_rank_two_probability"],
        "normalized_planner_feature": "POST_SWIPE_EMPTY_COUNT",
        "exact_over_registered_target_kernel": True,
        "reusable_across_fresh_states_actions_and_episodes": True,
        "serialized_full_state_action_table_present": False,
        "open_ended_expression_language_claimed": False,
    }
    return {
        **payload,
        "expression_world_model_id": content_id(pre.FUTURE_DOMAINS["world_model"], payload),
    }


def _episode(
    task: tuple[int, tuple[int, ...], str, dict[str, Any]]
) -> dict[str, Any]:
    episode_index, initial_board, seed, world_model = task
    state = state_from_board_v1(initial_board)
    initial_state = _state_document(state)
    decisions = []
    threshold = world_model["selected_threshold"]
    override = _fraction(world_model["override_rank_two_probability"])
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model = planner_v20.plan_proved_context_program_root_v20(
            state,
            feature_name="POST_SWIPE_EMPTY_COUNT",
            threshold=threshold,
            override_probability=override,
        )
        certificate_payload = {
            "schema": "acfqp.standard_2048_expression_plan_certificate.v21",
            "schema_version": SCHEMA_VERSION,
            "expression_program_preregistration_id": pre.PREREGISTRATION_ID,
            "expression_world_model_id": world_model["expression_world_model_id"],
            "episode_index": episode_index,
            "decision_index": decision_index,
            "root_state": _state_document(state),
            "planning_horizon": pre.PLANNING_HORIZON,
            "root_action_exact_values": model["root_action_exact_values"],
            "selected_action": model["selected_action"],
            "selected_expected_merge_score": model["selected_expected_merge_score"],
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
            "operational_target_probability_query_count": 0,
            "operational_ground_state_action_row_count": 0,
            "target_transition_accessed_before_certificate_freeze": False,
            "status": "CERTIFIED_RAW_CONTEXT_EXPRESSION_WORLD_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "expression_plan_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], certificate_payload
            ),
        }
        direct = planner_v20.evaluate_target_root_v20(state)
        if (
            model["root_action_exact_values"] != direct["root_action_exact_values"]
            or model["selected_action"] != direct["selected_action"]
        ):
            _fail("expression world model and target-ground control differ")
        outcome, tape = select_seeded_outcome_v1(
            kernel.target_outcomes_v18(state, Swipe2048Action(model["selected_action"])),
            seed=seed,
            decision_index=decision_index,
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "EXACT_RAW_CONTEXT_EXPRESSION_MODEL_CERTIFIED",
                "matched_cold_target_ground": direct,
                "all_root_action_values_exactly_equal": True,
                "selected_action_exact_value_and_loss_equivalent": True,
                "certificate_frozen_before_cold_evaluation_and_target_transition": True,
                "executed_action": model["selected_action"],
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
                "execution_transition_used_to_modify_world_model": False,
            }
        )
        state = outcome.next_state
    payload = {
        "schema": "acfqp.standard_2048_expression_episode.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": pre.PREREGISTRATION_ID,
        "expression_world_model_id": world_model["expression_world_model_id"],
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial_state,
        "planning_horizon": pre.PLANNING_HORIZON,
        "decisions": decisions,
        "decision_count": len(decisions),
        "expression_model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "final_state": _state_document(state),
        "all_root_action_values_exactly_equal": all(
            row["all_root_action_values_exactly_equal"] for row in decisions
        ),
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["selected_action_exact_value_and_loss_equivalent"] for row in decisions
        ),
    }
    return {
        **payload,
        "expression_episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_expression_program_preregistration_v21()
    pool = _context_pool()
    first_row = pool["rows"][0]
    first_empty_count = first_row["post_swipe_board_ranks"].count(0)
    first_observation = kernel.query_rank_two_probability_v18(first_empty_count)
    if first_observation == BASE_RATE:
        _fail("first expression query did not reveal a nonbase output")
    artifacts, candidates = _candidate_artifacts(pool, first_observation)
    acquisitions, remaining = _active_acquire(
        pool, artifacts, candidates, first_observation
    )
    proposal = _proposal(pool, artifacts, acquisitions, remaining[0])
    proof = _proof(proposal)
    world_model = _world_model(proposal, proof)
    tasks = tuple(
        (index, board, pre.TARGET_SEEDS[index], world_model)
        for index, board in enumerate(pre.TARGET_INITIAL_BOARDS)
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
        episodes = list(executor.map(_episode, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    if len(decisions) != 12:
        _fail("expression workload did not retain all preregistered decisions")
    query_count = len(acquisitions)
    payload = {
        "schema": "acfqp.standard_2048_expression_campaign.v21",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "expression_program_preregistration": preregistration.to_document(),
        "structural_context_pool": pool,
        "expression_acquisitions": acquisitions,
        "expression_proposal": proposal,
        "expression_proof": proof,
        "expression_world_model": world_model,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "raw_structural_context_count": len(pool["rows"]),
        "generated_primitive_expression_count": pool["expression_count_per_context"],
        "generated_expression_program_candidate_count": len(artifacts),
        "target_probability_query_count": query_count,
        "queried_pool_ordinals": [row["pool_ordinal"] for row in acquisitions],
        "version_space_counts_after_queries": [row["candidate_count_after"] for row in acquisitions],
        "selected_expression_key": proposal["selected_expression_key"],
        "selected_expression_ast": proposal["selected_expression_ast"],
        "selected_threshold": proposal["selected_threshold"],
        "postproposal_exact_formula_proof_row_count": proof["proof_row_count"],
        "v19_strict_no_prior_query_count": 10,
        "retained_query_reduction_against_no_prior": 10 - query_count,
        "expression_query_fraction_of_no_prior": Fraction(query_count, 10),
        "named_empty_count_or_v20_feature_basis_supplied_to_synthesizer": False,
        "structural_expression_and_program_synthesized_from_raw_contexts": True,
        "all_12_plans_in_expression_world_model": True,
        "all_12_root_action_values_exactly_match_cold_target_ground": all(
            row["all_root_action_values_exactly_equal"] for row in decisions
        ),
        "all_12_selected_actions_exactly_match_cold_target_ground": all(
            row["selected_action_exact_value_and_loss_equivalent"] for row in decisions
        ),
        "operational_target_probability_query_count_during_planning": 0,
        "operational_ground_state_action_row_count_during_planning": 0,
        "online_target_transition_observation_count": len(decisions),
        "evaluation_cold_target_ground_state_action_row_count": sum(
            row["matched_cold_target_ground"]["ground_state_action_row_count"]
            for row in decisions
        ),
        "evaluation_cold_target_ground_outcome_count": sum(
            row["matched_cold_target_ground"]["ground_outcome_count"]
            for row in decisions
        ),
        "sample_tax_result": "POSITIVE_REGISTERED_RAW_CONTEXT_EXPRESSION_RESULT_WITH_FOUR_QUERIES",
        "v20_result_used_during_v21_grammar_and_fixture_design": True,
        "blind_new_target_discovery_claimed": False,
        "conditional_on_registered_depth_one_reducer_grammar": True,
        "open_ended_expression_or_coordinate_invention_completed": False,
        "broad_or_physical_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": any(
            max(episode["final_state"]["board_ranks"]) >= GOAL_RANK for episode in episodes
        ),
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "expression_campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionProgramCampaignV21:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("expression campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("expression campaign bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "expression_campaign_id"
        }
        if (
            document.get("expression_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("expression campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("expression campaign is not an object")
        return document


@lru_cache(maxsize=1)
def run_standard_2048_expression_program_campaign_v21(
) -> Standard2048ExpressionProgramCampaignV21:
    document = _campaign_document()
    canonical_bytes = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["expression_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen expression campaign outcome changed")
    return Standard2048ExpressionProgramCampaignV21(
        _ISSUER, canonical_bytes, document["expression_campaign_id"]
    )


def verify_standard_2048_expression_program_campaign_v21(
    value: Standard2048ExpressionProgramCampaignV21,
) -> Standard2048ExpressionProgramCampaignV21:
    if type(value) is not Standard2048ExpressionProgramCampaignV21:
        _fail("expression campaign verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != run_standard_2048_expression_program_campaign_v21().canonical_bytes:
        _fail("expression campaign differs from semantic replay")
    document = value.to_document()
    if (
        document["target_probability_query_count"] != 4
        or document["selected_expression_key"]
        != "COUNT_EQ(POST_SWIPE_BOARD_RANKS,0)"
        or document["selected_threshold"] != 4
        or document["all_12_root_action_values_exactly_match_cold_target_ground"] is not True
        or document["official_execution_allowed"] is not False
    ):
        _fail("expression campaign result or claim locks changed")
    return value


__all__ = (
    "ConstructionK7Standard2048ExpressionProgramCampaignV21Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048ExpressionProgramCampaignV21",
    "run_standard_2048_expression_program_campaign_v21",
    "verify_standard_2048_expression_program_campaign_v21",
)
