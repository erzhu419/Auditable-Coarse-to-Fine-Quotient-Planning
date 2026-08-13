"""Transfer frozen expression synthesis to the committed-and-revealed target."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_blind_expression_preregistration_v22 as pre
from acfqp import construction_k7_standard_2048_commit_reveal_target_kernel_v22 as kernel
from acfqp import construction_k7_standard_2048_expression_planner_v1 as expression_runtime
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
PROFILE_KEY = "construction_k7_standard_2048_blind_expression_campaign_v22"
MAXIMUM_PROCESSES = 3
EXPECTED_CAMPAIGN_ID = "85a0f59d0751dfcad87517ed8167d66943d4be0ab9159f78aeaaef7f85923c3e"
EXPECTED_CANONICAL_BYTE_COUNT = 199840
EXPECTED_CANONICAL_SHA256 = "c3d19bedd6191c2137392c627a936c08fe90f8b2996bd9f2e0c877a93ab5c477"
BASE_RATE = Fraction(1, 10)
SELECTED_SWIPE_PROGRAM = "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP"
Candidate = tuple[str, dict[str, Any], int, Fraction, tuple[Fraction, ...]]


class ConstructionK7Standard2048BlindExpressionCampaignV22Error(ValueError):
    """The transferred synthesis, commitment, proof, or fresh plans changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048BlindExpressionCampaignV22Error(message)


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


def _expression_definitions(constants: tuple[int, ...]) -> tuple[tuple[str, dict[str, Any]], ...]:
    result = []
    for source in ("PRE_BOARD_RANKS", "POST_SWIPE_BOARD_RANKS"):
        for constant in constants:
            result.append(
                (
                    f"COUNT_EQ({source},{constant})",
                    {"operator": "COUNT_EQ", "vector_source": source, "constant": constant},
                )
            )
        for operator in (
            "MAX",
            "SUM",
            "DISTINCT_NONZERO_COUNT",
            "ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT",
        ):
            result.append(
                (f"{operator}({source})", {"operator": operator, "vector_source": source})
            )
    result.extend(
        (
            ("MERGE_SCORE", {"operator": "RAW_SCALAR", "source": "MERGE_SCORE"}),
            ("ACTION_ORDINAL", {"operator": "RAW_SCALAR", "source": "ACTION_ORDINAL"}),
        )
    )
    return tuple(result)


def _context_pool() -> dict[str, Any]:
    raw = []
    constants = set()
    for ordinal, (board, action) in enumerate(pre.RAW_CONTEXT_POOL):
        post, merge = _swipe(board, action)
        if post == board:
            _fail("blind raw context contains an illegal no-op")
        raw.append((ordinal, board, action, post, merge))
        constants.update(board)
        constants.update(post)
    frozen_constants = tuple(sorted(constants))
    definitions = _expression_definitions(frozen_constants)
    rows = []
    for ordinal, board, action, post, merge in raw:
        expressions = [
            {
                "expression_key": key,
                "expression_ast": ast,
                "value": expression_runtime.evaluate_structural_expression_v1(
                    ast,
                    pre_board=board,
                    action=action,
                    post_swipe_board=post,
                    merge_score=merge,
                ),
            }
            for key, ast in definitions
        ]
        raw_payload = {
            "pool_ordinal": ordinal,
            "pre_state_board_ranks": list(board),
            "action": action,
            "post_swipe_board_ranks": list(post),
            "merge_score": merge,
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
        "schema": "acfqp.standard_2048_blind_structural_pool.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "target_kernel_commitment_id": pre.TARGET_KERNEL_COMMITMENT_ID,
        "swipe_world_model_id": swipe_v14.FACTORED_WORLD_MODEL_ID,
        "observed_raw_rank_constants": list(frozen_constants),
        "rows": rows,
        "context_count": len(rows),
        "expression_count_per_context": len(definitions),
        "all_structural_values_frozen_before_first_probability_query": True,
        "target_semantics_source_or_reveal_present": False,
        "named_target_specific_feature_present": False,
    }
    return {
        **payload,
        "blind_structural_pool_id": content_id(pre.FUTURE_DOMAINS["context_pool"], payload),
    }


def _expression_maps(pool: dict[str, Any]) -> tuple[tuple[str, dict[str, Any], tuple[int, ...]], ...]:
    first = pool["rows"][0]["expression_values"]
    result = []
    for index, expression in enumerate(first):
        key, ast = expression["expression_key"], expression["expression_ast"]
        values = []
        for row in pool["rows"]:
            item = row["expression_values"][index]
            if item["expression_key"] != key or item["expression_ast"] != ast:
                _fail("blind expression inventory order changed")
            values.append(item["value"])
        result.append((key, ast, tuple(values)))
    return tuple(result)


def _candidate_artifacts(
    pool: dict[str, Any], override: Fraction
) -> tuple[list[dict[str, Any]], tuple[Candidate, ...]]:
    artifacts = []
    native = []
    ordinal = 0
    for key, ast, values in _expression_maps(pool):
        for threshold in sorted(set(values)):
            predictions = tuple(override if value <= threshold else BASE_RATE for value in values)
            if len(set(predictions)) == 1:
                continue
            payload = {
                "schema": "acfqp.standard_2048_blind_expression_candidate.v22",
                "schema_version": SCHEMA_VERSION,
                "blind_expression_preregistration_id": pre.PREREGISTRATION_ID,
                "blind_structural_pool_id": pool["blind_structural_pool_id"],
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
                "target_formula_used_to_generate_candidate": False,
            }
            artifacts.append(
                {
                    **payload,
                    "blind_expression_candidate_id": content_id(
                        pre.FUTURE_DOMAINS["candidate"], payload
                    ),
                }
            )
            native.append((key, ast, threshold, override, predictions))
            ordinal += 1
    return artifacts, tuple(native)


def _query_record(
    *, pool: dict[str, Any], pool_ordinal: int, query_ordinal: int,
    before: int | None, after: int, generated: bool,
) -> dict[str, Any]:
    row = pool["rows"][pool_ordinal]
    post = tuple(row["post_swipe_board_ranks"])
    observed = kernel.query_rank_two_probability_v22(post)
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_acquisition.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "blind_structural_pool_id": pool["blind_structural_pool_id"],
        "target_kernel_commitment_id": pre.TARGET_KERNEL_COMMITMENT_ID,
        "query_ordinal": query_ordinal,
        "pool_ordinal": pool_ordinal,
        "structural_context_sha256": row["structural_context_sha256"],
        "observed_rank_two_probability": _fdoc(observed),
        "candidate_count_before": before,
        "candidate_count_after": after,
        "candidates_generated_after_this_query": generated,
        "context_and_all_expression_values_frozen_before_query": True,
        "query_interface_received_raw_post_swipe_board": True,
        "target_formula_used_by_acquisition_rule": False,
        "target_query_returns_scalar_label_only": True,
        "full_state_action_outcome_row_materialized": False,
    }
    return {
        **payload,
        "blind_expression_acquisition_id": content_id(
            pre.FUTURE_DOMAINS["acquisition"], payload
        ),
    }


def _active_acquire(
    pool: dict[str, Any], candidates: tuple[Candidate, ...], first: Fraction
) -> tuple[list[dict[str, Any]], Candidate]:
    remaining = tuple(candidate for candidate in candidates if candidate[4][0] == first)
    queried = [0]
    rows = [_query_record(pool=pool, pool_ordinal=0, query_ordinal=0, before=None, after=len(remaining), generated=True)]
    while len(remaining) > 1:
        choices = []
        for pool_ordinal in range(len(pool["rows"])):
            if pool_ordinal in queried:
                continue
            buckets: dict[Fraction, int] = {}
            for candidate in remaining:
                prediction = candidate[4][pool_ordinal]
                buckets[prediction] = buckets.get(prediction, 0) + 1
            if len(buckets) > 1:
                choices.append((max(buckets.values()), pool_ordinal))
        if not choices:
            _fail("transferred active rule cannot separate blind target candidates")
        _, pool_ordinal = min(choices)
        queried.append(pool_ordinal)
        before = remaining
        observed = kernel.query_rank_two_probability_v22(
            tuple(pool["rows"][pool_ordinal]["post_swipe_board_ranks"])
        )
        remaining = tuple(
            candidate for candidate in remaining if candidate[4][pool_ordinal] == observed
        )
        if not remaining or len(remaining) >= len(before):
            _fail("blind active query did not shrink the version space")
        rows.append(
            _query_record(
                pool=pool, pool_ordinal=pool_ordinal, query_ordinal=len(rows),
                before=len(before), after=len(remaining), generated=False,
            )
        )
        if len(rows) > pre.MAXIMUM_TARGET_PROBABILITY_QUERIES:
            _fail("blind expression query budget exhausted")
    return rows, remaining[0]


def _proposal(
    pool: dict[str, Any], artifacts: list[dict[str, Any]],
    acquisitions: list[dict[str, Any]], selected: Candidate,
) -> dict[str, Any]:
    selected_artifact = next(
        row for row in artifacts
        if row["expression_key"] == selected[0]
        and row["expression_ast"] == selected[1]
        and row["threshold"] == selected[2]
    )
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_proposal.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "blind_structural_pool_id": pool["blind_structural_pool_id"],
        "target_kernel_commitment_id": pre.TARGET_KERNEL_COMMITMENT_ID,
        "candidate_artifacts": artifacts,
        "candidate_count": len(artifacts),
        "acquisition_ids": [row["blind_expression_acquisition_id"] for row in acquisitions],
        "queried_pool_ordinals": [row["pool_ordinal"] for row in acquisitions],
        "version_space_counts_after_queries": [row["candidate_count_after"] for row in acquisitions],
        "selected_candidate_id": selected_artifact["blind_expression_candidate_id"],
        "selected_expression_key": selected[0],
        "selected_expression_ast": selected[1],
        "selected_threshold": selected[2],
        "selected_base_rank_two_probability": _fdoc(BASE_RATE),
        "selected_override_rank_two_probability": _fdoc(selected[3]),
        "unique_program_consistent_with_queried_contexts": True,
        "transferred_v21_grammar_and_query_rule_unchanged": True,
        "target_formula_used_to_select_program": False,
        "proposal_has_world_model_authority": False,
    }
    return {
        **payload,
        "blind_expression_proposal_id": content_id(pre.FUTURE_DOMAINS["proposal"], payload),
    }


def _proof(proposal: dict[str, Any]) -> dict[str, Any]:
    revealed = kernel.kernel_semantics_document_v22()
    if revealed["target_kernel_id"] != pre.TARGET_KERNEL_COMMITMENT_ID:
        _fail("revealed target failed its preregistered commitment")
    law = revealed["rank_two_law"]
    if proposal["selected_expression_ast"] != law["override_expression_ast"]:
        _fail("blind selected expression differs from revealed target expression")
    threshold = proposal["selected_threshold"]
    override = _fraction(proposal["selected_override_rank_two_probability"])
    rows = []
    for expression_value in range(17):
        predicted = override if expression_value <= threshold else BASE_RATE
        target = (
            law["override_probability"]
            if expression_value <= law["override_threshold"]
            else law["base_probability"]
        )
        rows.append(
            {
                "expression_value": expression_value,
                "predicted_rank_two_probability": _fdoc(predicted),
                "revealed_target_rank_two_probability": _fdoc(target),
                "exact_match": predicted == target,
            }
        )
    mismatch_count = sum(row["exact_match"] is not True for row in rows)
    if mismatch_count:
        _fail("blind expression proposal failed post-reveal exact proof")
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_proof.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "blind_expression_proposal_id": proposal["blind_expression_proposal_id"],
        "target_kernel_commitment_id": pre.TARGET_KERNEL_COMMITMENT_ID,
        "revealed_target_kernel": revealed,
        "proposal_frozen_before_postproposal_formula_comparison": True,
        "commitment_exactly_validated_before_proof": True,
        "proof_rows": rows,
        "proof_row_count": len(rows),
        "proof_mismatch_count": mismatch_count,
        "exact_expression_program_equivalence_proved": True,
        "proof_rows_not_counted_as_target_probability_queries": True,
    }
    return {
        **payload,
        "blind_expression_proof_id": content_id(pre.FUTURE_DOMAINS["proof"], payload),
    }


def _world_model(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_world_model.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "blind_expression_proposal_id": proposal["blind_expression_proposal_id"],
        "blind_expression_proof_id": proof["blind_expression_proof_id"],
        "target_kernel_id": pre.TARGET_KERNEL_COMMITMENT_ID,
        "swipe_world_model_id": swipe_v14.FACTORED_WORLD_MODEL_ID,
        "expression_ast": proposal["selected_expression_ast"],
        "threshold": proposal["selected_threshold"],
        "base_probability": proposal["selected_base_rank_two_probability"],
        "override_probability": proposal["selected_override_rank_two_probability"],
        "exact_over_committed_and_revealed_target": True,
        "reusable_across_fresh_states_actions_and_episodes": True,
        "serialized_full_state_action_table_present": False,
        "open_ended_expression_language_claimed": False,
    }
    return {
        **payload,
        "blind_expression_world_model_id": content_id(
            pre.FUTURE_DOMAINS["world_model"], payload
        ),
    }


def _episode(task: tuple[int, tuple[int, ...], str, dict[str, Any]]) -> dict[str, Any]:
    episode_index, initial_board, seed, world = task
    state = state_from_board_v1(initial_board)
    initial = _state_document(state)
    decisions = []
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model = expression_runtime.plan_expression_world_model_root_v1(
            state,
            expression_ast=world["expression_ast"],
            threshold=world["threshold"],
            base_probability=_fraction(world["base_probability"]),
            override_probability=_fraction(world["override_probability"]),
            horizon=pre.PLANNING_HORIZON,
        )
        certificate_payload = {
            "schema": "acfqp.standard_2048_blind_expression_certificate.v22",
            "schema_version": SCHEMA_VERSION,
            "blind_expression_preregistration_id": pre.PREREGISTRATION_ID,
            "blind_expression_world_model_id": world["blind_expression_world_model_id"],
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
            "status": "CERTIFIED_COMMIT_REVEAL_EXPRESSION_WORLD_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "blind_expression_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], certificate_payload
            ),
        }
        direct = expression_runtime.evaluate_ground_root_v1(
            state,
            outcome_provider=kernel.target_outcomes_v22,
            horizon=pre.PLANNING_HORIZON,
        )
        if (
            model["root_action_exact_values"] != direct["root_action_exact_values"]
            or model["selected_action"] != direct["selected_action"]
        ):
            _fail("blind expression model differs from revealed target-ground")
        outcome, tape = select_seeded_outcome_v1(
            kernel.target_outcomes_v22(state, Swipe2048Action(model["selected_action"])),
            seed=seed,
            decision_index=decision_index,
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "EXACT_COMMIT_REVEAL_EXPRESSION_MODEL_CERTIFIED",
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
        "schema": "acfqp.standard_2048_blind_expression_episode.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": pre.PREREGISTRATION_ID,
        "blind_expression_world_model_id": world["blind_expression_world_model_id"],
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial,
        "planning_horizon": pre.PLANNING_HORIZON,
        "decisions": decisions,
        "decision_count": len(decisions),
        "model_certificate_count": len(decisions),
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
        "blind_expression_episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_blind_expression_preregistration_v22()
    if kernel.verify_target_kernel_commitment_v22() != pre.TARGET_KERNEL_COMMITMENT_ID:
        _fail("revealed target commitment changed before acquisition")
    pool = _context_pool()
    first = kernel.query_rank_two_probability_v22(tuple(pool["rows"][0]["post_swipe_board_ranks"]))
    if first == BASE_RATE:
        _fail("first blind query did not reveal a nonbase value")
    artifacts, candidates = _candidate_artifacts(pool, first)
    acquisitions, selected = _active_acquire(pool, candidates, first)
    proposal = _proposal(pool, artifacts, acquisitions, selected)
    proof = _proof(proposal)
    world = _world_model(proposal, proof)
    tasks = tuple(
        (index, board, pre.TARGET_SEEDS[index], world)
        for index, board in enumerate(pre.TARGET_INITIAL_BOARDS)
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
        episodes = list(executor.map(_episode, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    if len(decisions) != 12:
        _fail("blind-expression workload did not retain all decisions")
    query_count = len(acquisitions)
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_campaign.v22",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "blind_expression_preregistration": preregistration.to_document(),
        "revealed_target_kernel": kernel.kernel_semantics_document_v22(),
        "structural_pool": pool,
        "acquisitions": acquisitions,
        "proposal": proposal,
        "proof": proof,
        "world_model": world,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "generated_primitive_expression_count": pool["expression_count_per_context"],
        "generated_expression_program_candidate_count": len(artifacts),
        "target_probability_query_count": query_count,
        "queried_pool_ordinals": [row["pool_ordinal"] for row in acquisitions],
        "version_space_counts_after_queries": [row["candidate_count_after"] for row in acquisitions],
        "selected_expression_key": proposal["selected_expression_key"],
        "selected_expression_ast": proposal["selected_expression_ast"],
        "selected_threshold": proposal["selected_threshold"],
        "postproposal_exact_proof_row_count": proof["proof_row_count"],
        "strict_no_prior_context_query_count": len(pool["rows"]),
        "query_reduction_against_no_prior": len(pool["rows"]) - query_count,
        "query_fraction_of_no_prior": Fraction(query_count, len(pool["rows"])),
        "git_ordered_commit_reveal_protocol_satisfied": True,
        "preregistration_commit_abbreviated_sha": "24194ad",
        "target_reveal_commit_abbreviated_sha": "42b45b4",
        "target_semantics_absent_from_preregistration_artifact": True,
        "transferred_v21_grammar_and_query_rule_unchanged": True,
        "blind_protocol_transfer_result": "POSITIVE_GIT_ORDERED_COMMIT_REVEAL_PROTOCOL_TRANSFER",
        "experimenter_cognitive_blinding_claimed": False,
        "runtime_target_source_access_isolation_enforced": False,
        "all_12_plans_in_blind_expression_world_model": True,
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
        "conditional_on_registered_depth_one_expression_grammar": True,
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
        "blind_expression_campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048BlindExpressionCampaignV22:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("blind expression campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("blind expression campaign bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "blind_expression_campaign_id"
        }
        if (
            document.get("blind_expression_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("blind expression campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("blind expression campaign is not an object")
        return document


@lru_cache(maxsize=1)
def run_standard_2048_blind_expression_campaign_v22() -> Standard2048BlindExpressionCampaignV22:
    document = _campaign_document()
    canonical_bytes = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["blind_expression_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen blind expression campaign outcome changed")
    return Standard2048BlindExpressionCampaignV22(
        _ISSUER, canonical_bytes, document["blind_expression_campaign_id"]
    )


def verify_standard_2048_blind_expression_campaign_v22(
    value: Standard2048BlindExpressionCampaignV22,
) -> Standard2048BlindExpressionCampaignV22:
    if type(value) is not Standard2048BlindExpressionCampaignV22:
        _fail("blind expression verifier rejects foreign campaign")
    value.__post_init__()
    if value.canonical_bytes != run_standard_2048_blind_expression_campaign_v22().canonical_bytes:
        _fail("blind expression campaign differs from semantic replay")
    document = value.to_document()
    if (
        document["target_probability_query_count"] > 4
        or document["selected_expression_key"] != "COUNT_EQ(POST_SWIPE_BOARD_RANKS,1)"
        or document["selected_threshold"] != 2
        or document["all_12_root_action_values_exactly_match_cold_target_ground"] is not True
        or document["git_ordered_commit_reveal_protocol_satisfied"] is not True
        or document["official_execution_allowed"] is not False
    ):
        _fail("blind expression result or claim locks changed")
    return value


__all__ = (
    "ConstructionK7Standard2048BlindExpressionCampaignV22Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048BlindExpressionCampaignV22",
    "run_standard_2048_blind_expression_campaign_v22",
    "verify_standard_2048_blind_expression_campaign_v22",
)
