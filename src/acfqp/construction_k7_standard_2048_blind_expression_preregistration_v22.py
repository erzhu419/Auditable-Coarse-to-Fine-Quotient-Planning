"""Commit-only Gate for transferring raw-context expression synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_ACQUISITION_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CAMPAIGN_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CANDIDATE_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CERTIFICATE_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_EPISODE_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PREREGISTRATION_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROOF_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROPOSAL_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_VERIFICATION_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_WORLD_MODEL_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_STRUCTURAL_POOL_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COMMIT_REVEAL_TARGET_KERNEL_V22_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "22.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.181"
PROFILE_KEY = "construction_k7_standard_2048_commit_reveal_expression_transfer_v22"
PREREGISTRATION_ID = "ac5bc17b69aad50e7b87461891f5bfe39125d2bb33b56cd39d5cc33bba674831"
TARGET_KERNEL_COMMITMENT_ID = (
    "9c40dc9f4a33d2f8bdb008aad5af3fc43be228c7fb964cf137c53af03e962eb5"
)
V21_CAMPAIGN_ID = "264749b3f9b4bd44d289476f829b0fc88076828ae7747a2a3b6c12fb6af75d4f"
V21_VERIFICATION_ID = "a43a70731bbc56c24bef3974256c5e1beb73a2c97aeb04336b8796f2bbe1998b"
MAXIMUM_TARGET_PROBABILITY_QUERIES = 4
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 4
RAW_CONTEXT_POOL = (
    ((4, 3, 4, 3, 7, 5, 1, 5, 6, 2, 0, 7, 4, 1, 5, 5), "RIGHT"),
    ((0, 3, 5, 1, 3, 0, 7, 5, 6, 4, 2, 1, 7, 1, 6, 5), "RIGHT"),
    ((1, 0, 3, 5, 6, 6, 0, 7, 2, 1, 0, 1, 1, 1, 1, 6), "LEFT"),
    ((3, 0, 4, 0, 1, 4, 0, 0, 4, 4, 0, 4, 0, 0, 7, 5), "UP"),
    ((1, 0, 2, 1, 3, 6, 5, 5, 7, 7, 4, 5, 1, 5, 7, 7), "RIGHT"),
    ((0, 2, 4, 3, 4, 0, 4, 3, 0, 5, 0, 7, 4, 5, 0, 0), "UP"),
    ((2, 2, 0, 0, 7, 0, 0, 5, 0, 2, 5, 0, 3, 5, 2, 2), "LEFT"),
    ((4, 0, 5, 0, 3, 0, 0, 7, 7, 3, 0, 0, 5, 0, 0, 7), "RIGHT"),
)
TARGET_INITIAL_BOARDS = (
    (6, 1, 5, 1, 3, 6, 5, 6, 4, 2, 0, 2, 3, 1, 0, 4),
    (6, 0, 0, 3, 0, 2, 7, 4, 7, 2, 7, 0, 1, 2, 4, 7),
    (0, 4, 0, 3, 6, 2, 0, 5, 5, 0, 4, 0, 3, 2, 6, 0),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v181-blind-expression-target-{index:02d}-20260813"
    for index in range(3)
)
FUTURE_DOMAINS = {
    "target_kernel": CONSTRUCTION_K7_STANDARD_2048_COMMIT_REVEAL_TARGET_KERNEL_V22_DOMAIN,
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PREREGISTRATION_V22_DOMAIN,
    "context_pool": CONSTRUCTION_K7_STANDARD_2048_BLIND_STRUCTURAL_POOL_V22_DOMAIN,
    "candidate": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CANDIDATE_V22_DOMAIN,
    "acquisition": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_ACQUISITION_V22_DOMAIN,
    "proposal": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROPOSAL_V22_DOMAIN,
    "proof": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROOF_V22_DOMAIN,
    "world_model": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_WORLD_MODEL_V22_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CERTIFICATE_V22_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_EPISODE_V22_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CAMPAIGN_V22_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_VERIFICATION_V22_DOMAIN,
}


class ConstructionK7Standard2048BlindExpressionPreregistrationV22Error(ValueError):
    """The commitment, transferred grammar, raw pool, or workload changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048BlindExpressionPreregistrationV22Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_preregistration.v22",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v21_expression_campaign_id": V21_CAMPAIGN_ID,
            "v21_independent_verification_id": V21_VERIFICATION_ID,
            "v21_synthesis_protocol_transferred_without_semantic_change": True,
        },
        "target_commitment": {
            "target_kernel_domain": FUTURE_DOMAINS["target_kernel"],
            "target_kernel_commitment_id": TARGET_KERNEL_COMMITMENT_ID,
            "target_semantics_document_present": False,
            "target_kernel_source_present": False,
            "commitment_frozen_before_reveal_commit": True,
            "reveal_must_recompute_exact_committed_content_id": True,
            "experimenter_cognitive_blinding_claimed": False,
            "git_ordered_commit_reveal_protocol_claimed": True,
        },
        "raw_context_pool": [
            {
                "pool_ordinal": index,
                "pre_state_board_ranks": list(board),
                "action": action,
            }
            for index, (board, action) in enumerate(RAW_CONTEXT_POOL)
        ],
        "raw_context_count": len(RAW_CONTEXT_POOL),
        "transferred_expression_grammar": {
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
            "expression_composition_depth": 1,
            "program_schema": "IF_EXPRESSION_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
            "base_rank_two_probability": {"numerator": 1, "denominator": 10},
            "override_generated_from_first_observed_nonbase_value": True,
            "thresholds_generated_from_frozen_expression_values": True,
            "constant_prediction_candidates_removed": True,
            "named_feature_or_target_specific_expression_supplied": False,
        },
        "active_acquisition": {
            "first_query_pool_ordinal": 0,
            "later_query_rule": (
                "MINIMIZE_MAXIMUM_REMAINING_VERSION_BUCKET_THEN_POOL_ORDINAL"
            ),
            "stop_rule": "ONE_EXPRESSION_PROGRAM_REMAINS",
            "maximum_target_probability_queries": MAXIMUM_TARGET_PROBABILITY_QUERIES,
            "full_state_action_outcome_rows_forbidden": True,
        },
        "postproposal_reveal_and_proof": {
            "target_reveal_source_access_before_proposal_freeze": False,
            "reveal_commitment_validation_required_before_proof": True,
            "proof_domain_generated_from_selected_expression_normal_form": True,
            "proof_rows_reported_separately_from_probability_queries": True,
            "proof_failure_prevents_world_model_issuance": True,
        },
        "heldout_planning_workload": {
            "initial_boards": [list(board) for board in TARGET_INITIAL_BOARDS],
            "episode_seeds": list(TARGET_SEEDS),
            "episode_count": len(TARGET_INITIAL_BOARDS),
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "planning_horizon": PLANNING_HORIZON,
            "heldout_target_transitions_unread_before_preregistration": True,
        },
        "sample_tax_contract": {
            "target_probability_query_budget": MAXIMUM_TARGET_PROBABILITY_QUERIES,
            "strict_no_prior_context_query_count": len(RAW_CONTEXT_POOL),
            "positive_condition": "QUERY_COUNT_LE_4_AND_STRICTLY_LESS_THAN_8",
            "proof_compute_planning_compute_and_target_transitions_separate": True,
            "scalar_sum_present": False,
        },
        "outcome_fields_present": False,
        "target_revealed": False,
        "target_probability_query_count": 0,
        "expression_candidates_generated": False,
        "expression_program_selected": False,
        "exact_proof_executed": False,
        "heldout_planning_executed": False,
        "blind_protocol_transfer_claimed": False,
        "open_ended_expression_invention_claimed": False,
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
        "blind_expression_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048BlindExpressionPreregistrationV22:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("blind-expression preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("blind-expression preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "blind_expression_preregistration_id"
        }
        if (
            document.get("blind_expression_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("blind-expression preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("blind-expression preregistration is not an object")
        return document


def freeze_standard_2048_blind_expression_preregistration_v22(
) -> Standard2048BlindExpressionPreregistrationV22:
    document = _document()
    if document["blind_expression_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen blind-expression preregistration identity changed")
    return Standard2048BlindExpressionPreregistrationV22(
        _ISSUER,
        canonical_json_bytes(document),
        document["blind_expression_preregistration_id"],
    )


def verify_standard_2048_blind_expression_preregistration_v22(
    value: Standard2048BlindExpressionPreregistrationV22,
) -> Standard2048BlindExpressionPreregistrationV22:
    if type(value) is not Standard2048BlindExpressionPreregistrationV22:
        _fail("blind-expression preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("blind-expression preregistration differs from frozen semantics")
    return value


__all__ = (
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "MAXIMUM_TARGET_PROBABILITY_QUERIES",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "RAW_CONTEXT_POOL",
    "Standard2048BlindExpressionPreregistrationV22",
    "TARGET_INITIAL_BOARDS",
    "TARGET_KERNEL_COMMITMENT_ID",
    "TARGET_SEEDS",
    "freeze_standard_2048_blind_expression_preregistration_v22",
    "verify_standard_2048_blind_expression_preregistration_v22",
)
