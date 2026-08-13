"""Outcome-free Gate for proposing a repair coordinate and program from context rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_OBSERVATION_ARCHIVE_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PLAN_CERTIFICATE_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CAMPAIGN_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CANDIDATE_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_EPISODE_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PREREGISTRATION_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROOF_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROPOSAL_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_VERIFICATION_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_WORLD_MODEL_V20_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "20.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.179"
PROFILE_KEY = "construction_k7_standard_2048_observation_proposed_context_program_v20"
PREREGISTRATION_ID = "52cc4ca629df1080843293eaf57cdefa351197dd66e11d4049dbbaeecff13fc6"
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 4
V19_CAMPAIGN_ID = "1154337025f11c493a1805744f27ea7e9057fd2f2b4884c8e3eb46e4535847b7"
V19_INDEPENDENT_VERIFICATION_ID = "123b803fff1d7a9a9acf638150d0c5d0f9212757dabb0d1e23419bddeea731c7"
TARGET_KERNEL_ID = "84d799a915676cee6ded5fac11597386a26c10c213c09a64164eb9a13e811d8a"
SOURCE_WITNESSES = (
    (
        (0, 0, 1, 2, 4, 5, 4, 1, 2, 3, 2, 4, 1, 2, 3, 6),
        "UP",
        2,
    ),
    (
        (0, 0, 2, 2, 5, 1, 3, 3, 2, 5, 2, 6, 1, 3, 3, 1),
        "LEFT",
        5,
    ),
    (
        (0, 1, 2, 4, 1, 1, 3, 5, 3, 2, 4, 2, 6, 4, 1, 2),
        "DOWN",
        3,
    ),
    (
        (0, 0, 2, 1, 5, 5, 3, 2, 2, 3, 2, 3, 1, 1, 3, 6),
        "LEFT",
        4,
    ),
)
FEATURE_BASIS = (
    "POST_SWIPE_EMPTY_COUNT",
    "PRE_STATE_EMPTY_COUNT",
    "POST_SWIPE_MAX_RANK",
    "PRE_STATE_MAX_RANK",
    "MERGE_OCCURRED",
    "ACTION_AXIS_HORIZONTAL",
)
TARGET_INITIAL_BOARDS = (
    (2, 6, 5, 0, 6, 1, 0, 0, 0, 2, 3, 1, 6, 5, 5, 4),
    (2, 0, 0, 1, 5, 1, 4, 3, 5, 3, 4, 4, 3, 0, 3, 2),
    (1, 0, 2, 5, 0, 2, 6, 0, 6, 0, 2, 2, 0, 1, 4, 1),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v179-context-program-target-{index:02d}-20260813"
    for index in range(len(TARGET_INITIAL_BOARDS))
)
FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PREREGISTRATION_V20_DOMAIN,
    "archive": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_OBSERVATION_ARCHIVE_V20_DOMAIN,
    "candidate": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CANDIDATE_V20_DOMAIN,
    "proposal": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROPOSAL_V20_DOMAIN,
    "proof": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROOF_V20_DOMAIN,
    "world_model": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_WORLD_MODEL_V20_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PLAN_CERTIFICATE_V20_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_EPISODE_V20_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CAMPAIGN_V20_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_VERIFICATION_V20_DOMAIN,
}


class ConstructionK7Standard2048ContextProgramPreregistrationV20Error(ValueError):
    """The raw witnesses, feature basis, proposal rule, or targets changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ContextProgramPreregistrationV20Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_context_program_preregistration.v20",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v19_matched_repair_campaign_id": V19_CAMPAIGN_ID,
            "v19_independent_verification_id": V19_INDEPENDENT_VERIFICATION_ID,
            "v19_result_frozen_before_v20_observation_archive": True,
        },
        "target_kernel_id": TARGET_KERNEL_ID,
        "source_context_protocol": {
            "witnesses": [
                {
                    "source_observation_index": index,
                    "pre_state_board_ranks": list(board),
                    "action": action,
                    "structurally_expected_post_swipe_empty_count": empty_count,
                }
                for index, (board, action, empty_count) in enumerate(SOURCE_WITNESSES)
            ],
            "source_observation_count": len(SOURCE_WITNESSES),
            "witnesses_frozen_before_target_probability_queries": True,
            "post_swipe_board_and_features_computed_before_probability_query": True,
            "target_probability_or_kernel_rule_available_to_proposer": False,
            "observed_target_field": "RANK_TWO_PROBABILITY_FOR_EXACT_CONTEXT",
            "full_state_action_outcome_row_materialized": False,
        },
        "feature_basis": list(FEATURE_BASIS),
        "feature_basis_kind": "FINITE_STRUCTURAL_PRIMITIVE_BASIS",
        "program_proposal_protocol": {
            "base_rank_two_probability_from_frozen_v16_model": {
                "numerator": 1,
                "denominator": 10,
            },
            "override_values_generated_from_observed_nonbase_values": True,
            "threshold_values_generated_from_observed_feature_values": True,
            "normalized_program_schema": "IF_FEATURE_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
            "preenumerated_feature_threshold_program_candidates": False,
            "source_score": "EXACT_RATIONAL_MISMATCH_COUNT",
            "required_result": "UNIQUE_ZERO_MISMATCH_PROGRAM",
            "proposal_frozen_before_target_source_or_heldout_access": True,
        },
        "postproposal_exact_proof": {
            "target_source_access_before_proposal_freeze": False,
            "verify_selected_feature_and_program_against_target_kernel_semantics": True,
            "registered_post_swipe_empty_count_domain": list(range(1, 17)),
            "required_exact_formula_row_count": 16,
            "proof_compute_not_counted_as_transition_observation": True,
            "proof_failure_prevents_world_model_authority": True,
        },
        "heldout_planning_workload": {
            "initial_boards": [list(board) for board in TARGET_INITIAL_BOARDS],
            "episode_seeds": list(TARGET_SEEDS),
            "episode_count": len(TARGET_INITIAL_BOARDS),
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "planning_horizon": PLANNING_HORIZON,
            "heldout_target_transitions_unread_before_preregistration": True,
        },
        "matched_direct_control": {
            "cold_exact_target_ground_h3_at_every_decision": True,
            "standalone_evaluation_lane_only": True,
            "route_or_certificate_authority": False,
            "all_root_values_and_actions_must_match": True,
        },
        "sample_tax_axes": {
            "raw_context_probability_observation_count": 4,
            "v19_matched_program_query_count": 4,
            "v19_no_prior_query_count": 10,
            "postproposal_formula_proof_rows": 16,
            "target_transitions_reported_separately": True,
            "planning_compute_reported_separately": True,
            "total_work_scalar_present": False,
        },
        "outcome_fields_present": False,
        "observation_archive_materialized": False,
        "feature_or_program_selected": False,
        "exact_postproposal_proof_executed": False,
        "world_model_issued": False,
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
        "context_program_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ContextProgramPreregistrationV20:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("context-program preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("context-program preregistration bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "context_program_preregistration_id"
        }
        if (
            document.get("context_program_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload) != self.preregistration_id
        ):
            _fail("context-program preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("context-program preregistration is not an object")
        return document


def freeze_standard_2048_context_program_preregistration_v20(
) -> Standard2048ContextProgramPreregistrationV20:
    document = _document()
    if document["context_program_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen context-program preregistration identity changed")
    return Standard2048ContextProgramPreregistrationV20(
        _ISSUER, canonical_json_bytes(document), document["context_program_preregistration_id"]
    )


def verify_standard_2048_context_program_preregistration_v20(
    value: Standard2048ContextProgramPreregistrationV20,
) -> Standard2048ContextProgramPreregistrationV20:
    if type(value) is not Standard2048ContextProgramPreregistrationV20:
        _fail("context-program preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("context-program preregistration differs from frozen semantics")
    return value


__all__ = (
    "FEATURE_BASIS",
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "SOURCE_WITNESSES",
    "Standard2048ContextProgramPreregistrationV20",
    "TARGET_INITIAL_BOARDS",
    "TARGET_SEEDS",
    "freeze_standard_2048_context_program_preregistration_v20",
    "verify_standard_2048_context_program_preregistration_v20",
)
