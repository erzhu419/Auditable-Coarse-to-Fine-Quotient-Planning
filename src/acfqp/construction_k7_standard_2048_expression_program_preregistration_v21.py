"""Outcome-free Gate for synthesizing a feature expression from raw contexts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACQUISITION_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CAMPAIGN_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CANDIDATE_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_EPISODE_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PLAN_CERTIFICATE_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROGRAM_PREREGISTRATION_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROOF_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROPOSAL_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_VERIFICATION_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_WORLD_MODEL_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STRUCTURAL_CONTEXT_POOL_V21_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "21.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.180"
PROFILE_KEY = "construction_k7_standard_2048_raw_context_expression_program_v21"
PREREGISTRATION_ID = "5a6aa3f7978445c695396bc7b3f4ab708d9f113e6ee0608e44bb255096d632e9"
V20_CAMPAIGN_ID = "4dc1d46cfac38aca4bf6e881dfaafea8550f84d535b51cc1f5ef273800b24df5"
V20_INDEPENDENT_VERIFICATION_ID = (
    "da1328e43ad293296df5e2021a24d244e77818b7bf888780e1bce974db299f3e"
)
TARGET_KERNEL_ID = "84d799a915676cee6ded5fac11597386a26c10c213c09a64164eb9a13e811d8a"
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 4
MAXIMUM_TARGET_PROBABILITY_QUERIES = 4
RAW_CONTEXT_POOL = (
    ((5, 2, 2, 6, 1, 5, 5, 4, 5, 1, 3, 2, 5, 2, 2, 1), "UP"),
    ((1, 4, 2, 6, 4, 4, 1, 3, 1, 2, 0, 0, 5, 5, 6, 5), "RIGHT"),
    ((5, 2, 2, 6, 4, 1, 0, 6, 0, 4, 3, 2, 5, 5, 3, 2), "UP"),
    ((0, 1, 5, 2, 0, 0, 3, 2, 0, 0, 0, 0, 2, 2, 4, 1), "LEFT"),
    ((3, 4, 6, 1, 6, 3, 2, 2, 3, 6, 2, 5, 0, 3, 2, 0), "DOWN"),
    ((0, 5, 3, 1, 6, 2, 6, 0, 5, 5, 5, 0, 6, 0, 5, 1), "DOWN"),
    ((0, 0, 4, 5, 6, 0, 2, 0, 1, 0, 0, 1, 2, 1, 0, 0), "LEFT"),
    ((0, 5, 4, 0, 0, 5, 0, 2, 0, 0, 6, 0, 2, 0, 5, 3), "RIGHT"),
)
TARGET_INITIAL_BOARDS = (
    (3, 2, 1, 0, 3, 0, 3, 0, 4, 6, 4, 1, 4, 3, 5, 2),
    (2, 1, 0, 3, 0, 5, 4, 4, 3, 2, 6, 1, 3, 0, 3, 0),
    (2, 3, 3, 0, 2, 1, 0, 0, 2, 1, 5, 0, 6, 0, 3, 5),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v180-expression-program-target-{index:02d}-20260813"
    for index in range(len(TARGET_INITIAL_BOARDS))
)
FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROGRAM_PREREGISTRATION_V21_DOMAIN,
    "context_pool": CONSTRUCTION_K7_STANDARD_2048_STRUCTURAL_CONTEXT_POOL_V21_DOMAIN,
    "candidate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CANDIDATE_V21_DOMAIN,
    "acquisition": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACQUISITION_V21_DOMAIN,
    "proposal": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROPOSAL_V21_DOMAIN,
    "proof": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROOF_V21_DOMAIN,
    "world_model": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_WORLD_MODEL_V21_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PLAN_CERTIFICATE_V21_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_EPISODE_V21_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CAMPAIGN_V21_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_VERIFICATION_V21_DOMAIN,
}


class ConstructionK7Standard2048ExpressionProgramPreregistrationV21Error(ValueError):
    """The raw context pool, expression grammar, active rule, or targets changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionProgramPreregistrationV21Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_program_preregistration.v21",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v20_context_program_campaign_id": V20_CAMPAIGN_ID,
            "v20_independent_verification_id": V20_INDEPENDENT_VERIFICATION_ID,
            "v20_result_available_during_v21_design": True,
            "blind_new_target_discovery_claimed": False,
            "v21_grammar_pool_and_query_rule_frozen_before_v21_probability_queries": True,
        },
        "target_kernel_id": TARGET_KERNEL_ID,
        "raw_context_pool_protocol": {
            "contexts": [
                {
                    "pool_ordinal": index,
                    "pre_state_board_ranks": list(board),
                    "action": action,
                }
                for index, (board, action) in enumerate(RAW_CONTEXT_POOL)
            ],
            "context_count": len(RAW_CONTEXT_POOL),
            "post_swipe_board_and_merge_computed_by_proved_v14_program": True,
            "all_structural_expression_values_frozen_before_first_probability_query": True,
            "target_probability_or_formula_absent_from_structural_pool": True,
        },
        "expression_grammar": {
            "raw_vector_sources": ["PRE_BOARD_RANKS", "POST_SWIPE_BOARD_RANKS"],
            "vector_reducers": [
                "COUNT_EQ_OBSERVED_CELL_VALUE",
                "MAX",
                "SUM",
                "DISTINCT_NONZERO_COUNT",
                "ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT",
            ],
            "count_eq_constants_generated_from_observed_raw_cell_values": True,
            "raw_scalar_sources": ["MERGE_SCORE", "ACTION_ORDINAL"],
            "named_empty_count_feature_supplied": False,
            "named_v20_feature_basis_supplied": False,
            "expression_composition_depth": 1,
            "open_ended_expression_language_claimed": False,
        },
        "program_and_active_acquisition_protocol": {
            "base_rank_two_probability": {"numerator": 1, "denominator": 10},
            "first_query_pool_ordinal": 0,
            "override_values_generated_from_observed_nonbase_query_values": True,
            "thresholds_generated_from_frozen_expression_values": True,
            "program_schema": "IF_EXPRESSION_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
            "constant_prediction_candidates_removed": True,
            "after_first_query_rule": (
                "MINIMIZE_MAXIMUM_REMAINING_VERSION_BUCKET_THEN_POOL_ORDINAL"
            ),
            "stop_rule": "UNIQUE_ZERO_MISMATCH_EXPRESSION_PROGRAM",
            "maximum_target_probability_queries": MAXIMUM_TARGET_PROBABILITY_QUERIES,
            "full_state_action_outcome_rows_forbidden": True,
        },
        "postproposal_exact_proof": {
            "proposal_frozen_before_target_formula_access": True,
            "selected_expression_normal_form_must_reduce_to_registered_context_statistic": True,
            "registered_post_swipe_empty_count_domain": list(range(1, 17)),
            "required_exact_formula_row_count": 16,
            "proof_rows_reported_separately_from_probability_queries": True,
        },
        "heldout_planning_workload": {
            "initial_boards": [list(board) for board in TARGET_INITIAL_BOARDS],
            "episode_seeds": list(TARGET_SEEDS),
            "episode_count": len(TARGET_INITIAL_BOARDS),
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "planning_horizon": PLANNING_HORIZON,
            "heldout_transitions_unread_before_preregistration": True,
        },
        "sample_tax_contract": {
            "v21_probability_query_budget": MAXIMUM_TARGET_PROBABILITY_QUERIES,
            "v19_actual_strict_no_prior_query_count": 10,
            "positive_condition": "V21_QUERIES_LE_4_AND_STRICTLY_LESS_THAN_10",
            "structural_pool_computation_not_counted_as_target_probability_query": True,
            "proof_rows_planning_compute_and_target_transitions_reported_separately": True,
            "scalar_sum_present": False,
        },
        "outcome_fields_present": False,
        "context_pool_materialized": False,
        "target_probability_query_count": 0,
        "expression_candidate_count": 0,
        "expression_or_program_selected": False,
        "exact_proof_executed": False,
        "heldout_planning_executed": False,
        "open_ended_coordinate_invention_claimed": False,
        "broad_sample_efficiency_claimed": False,
        "full_standard_2048_game_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "expression_program_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionProgramPreregistrationV21:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("expression-program preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("expression-program preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "expression_program_preregistration_id"
        }
        if (
            document.get("expression_program_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("expression-program preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("expression-program preregistration is not an object")
        return document


def freeze_standard_2048_expression_program_preregistration_v21(
) -> Standard2048ExpressionProgramPreregistrationV21:
    document = _document()
    if document["expression_program_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen expression-program preregistration identity changed")
    return Standard2048ExpressionProgramPreregistrationV21(
        _ISSUER,
        canonical_json_bytes(document),
        document["expression_program_preregistration_id"],
    )


def verify_standard_2048_expression_program_preregistration_v21(
    value: Standard2048ExpressionProgramPreregistrationV21,
) -> Standard2048ExpressionProgramPreregistrationV21:
    if type(value) is not Standard2048ExpressionProgramPreregistrationV21:
        _fail("expression-program preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("expression-program preregistration differs from frozen semantics")
    return value


__all__ = (
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "MAXIMUM_TARGET_PROBABILITY_QUERIES",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "RAW_CONTEXT_POOL",
    "Standard2048ExpressionProgramPreregistrationV21",
    "TARGET_INITIAL_BOARDS",
    "TARGET_SEEDS",
    "freeze_standard_2048_expression_program_preregistration_v21",
    "verify_standard_2048_expression_program_preregistration_v21",
)
