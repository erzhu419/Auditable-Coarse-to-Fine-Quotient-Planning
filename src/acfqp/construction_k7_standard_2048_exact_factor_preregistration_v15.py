"""Outcome-free Gate for exact factored planning with a synthesized swipe."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_coordinate_preregistration_v13 as v13
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CERTIFICATE_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_EPISODE_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_PREREGISTRATION_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_SOURCE_CLOSURE_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_VERIFICATION_V15_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "15.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.174"
PROFILE_KEY = "construction_k7_standard_2048_exact_factored_planning_v15"
PREREGISTRATION_ID = "0e64224ff82e1d19cd6695cf0774a937c69e55320d7787165ba641a362de18f5"

V14_PROGRAM_PREREGISTRATION_ID = "948020ab2f6ef639899a0913ce68b7cb2573eb8e8d4b6edd07c7550ff08aa62e"
V14_PROGRAM_PROPOSAL_ID = "7164a54cad13246a55c891a71a1a879b15be7116fbcb49998e8b7619f9c0ce72"
V14_PROGRAM_LINE_PROOF_ID = "3960ef8c496eb00a81d08bf29243ee7f5cd5f50f5302f2b91cb836618bc322b6"
V14_FACTORED_WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
V14_INDEPENDENT_VERIFICATION_ID = "f739865ab86c0a08bfff43492fa2ca73a10d0d0d6f3bf5732b5f419d7a5b4716"
STANDARD_2048_SOURCE_SHA256 = "0fabdec281cc94c53bceef37bdb5336da45c71c7339370d25d7dfa076aa7154c"
STANDARD_2048_SOURCE_BYTE_COUNT = 14739

PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 16
EPISODE_COUNT = 4
MAXIMUM_DECISION_COUNT = EPISODE_COUNT * MAXIMUM_DECISIONS_PER_EPISODE

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_PREREGISTRATION_V15_DOMAIN,
    "source_closure": CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_SOURCE_CLOSURE_V15_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CERTIFICATE_V15_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_EPISODE_V15_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_VERIFICATION_V15_DOMAIN,
}


class ConstructionK7Standard2048ExactFactorPreregistrationV15Error(ValueError):
    """The source-closure, exact-factor planner, workload, or Gate changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExactFactorPreregistrationV15Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_exact_factor_preregistration.v15",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "v13_coordinate_preregistration_id": v13.PREREGISTRATION_ID,
        "v14_program_preregistration_id": V14_PROGRAM_PREREGISTRATION_ID,
        "v14_program_proposal_id": V14_PROGRAM_PROPOSAL_ID,
        "v14_program_line_proof_id": V14_PROGRAM_LINE_PROOF_ID,
        "v14_factored_world_model_id": V14_FACTORED_WORLD_MODEL_ID,
        "v14_independent_verification_id": V14_INDEPENDENT_VERIFICATION_ID,
        "v14_outcomes_frozen_before_v15_target_execution": True,
        "v13_target_transition_or_route_outcomes_read_before_freeze": False,
        "exact_factor_source_closure": {
            "source_path": "src/acfqp/domains/standard_2048.py",
            "source_sha256": STANDARD_2048_SOURCE_SHA256,
            "source_byte_count": STANDARD_2048_SOURCE_BYTE_COUNT,
            "required_public_symbols": [
                "ACTION_ORDER",
                "GOAL_RANK",
                "SPAWN_DISTRIBUTION",
                "Swipe2048Action",
                "Swipe2048State",
                "Swipe2048Status",
                "select_seeded_outcome_v1",
                "state_from_board_v1",
                "step_v1",
            ],
            "spawn_distribution": [
                {"rank": 1, "probability": {"numerator": 9, "denominator": 10}},
                {"rank": 2, "probability": {"numerator": 1, "denominator": 10}},
            ],
            "spawn_cell_law": "UNIFORM_OVER_ALL_POST_SWIPE_EMPTY_CELLS",
            "spawn_rank_independent_of_cell_given_registered_law": True,
            "public_rule_is_domain_contract_not_statistically_inferred": True,
        },
        "exact_factored_operator": {
            "deterministic_component": "V14_OBSERVATION_PROPOSED_EXACT_PROVED_SWIPE_PROGRAM",
            "stochastic_component": "SOURCE_CLOSED_STANDARD_2048_SPAWN_CONTRACT",
            "successors_generated_lazily_inside_bellman_backup": True,
            "state_action_rows_serialized_or_persisted": False,
            "exact_rational_arithmetic_required": True,
            "d4_subproof_memoization_allowed": True,
            "model_reused_across_all_decisions_and_episodes": True,
            "rank_proof_scope": [0, 19],
        },
        "certificate_protocol": {
            "planning_horizon": PLANNING_HORIZON,
            "certificate_kind": "EXACT_FACTORED_H3_BELLMAN_OPTIMALITY",
            "selected_action_rule": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_THEN_ACTION_ORDER",
            "certificate_uses_ground_step_v1": False,
            "certificate_uses_target_transition_outcome": False,
            "certificate_frozen_before_target_transition": True,
            "out_of_scope_rank_or_source_closure_failure_route": "EXACT_LOCAL_OR_COLD_DIRECT_FALLBACK",
            "fallback_only_after_certificate_failure": True,
            "fallback_cap_exhaustion_is_not_infeasibility": True,
        },
        "target_workload": {
            "initial_boards": [list(board) for board in v13.TARGET_INITIAL_BOARDS],
            "episode_seeds": list(v13.TARGET_EPISODE_SEEDS),
            "episode_count": EPISODE_COUNT,
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "maximum_decision_count": MAXIMUM_DECISION_COUNT,
            "early_terminal_closure_allowed": True,
        },
        "matched_direct_control": {
            "cold_exact_ground_h3_planner": True,
            "evaluation_lane_only_for_factored_certified_routes": True,
            "operational_lane_for_certificate_failure_fallback": True,
            "no_route_or_certificate_authority": True,
            "selected_action_exact_value_and_loss_equivalence_required": True,
        },
        "sample_tax_gate": {
            "program_arm_offline_transition_observation_count": 768,
            "matched_fixed_observation_control_count": 8192,
            "registered_offline_observation_difference": 7424,
            "target_transition_count_reported_separately": True,
            "program_proof_compute_count_reported_separately": True,
            "ground_fallback_rows_and_outcomes_reported_separately": True,
            "positive_result_requires_all_target_action_value_loss_equivalence": True,
            "positive_result_is_conditional_on_source_closed_standard_2048_family": True,
            "broad_domain_or_physical_iid_sample_efficiency_claimed": False,
            "total_operational_work_saving_claimed": False,
        },
        "outcome_fields_present": False,
        "source_closure_materialized": False,
        "exact_factored_campaign_run": False,
        "target_execution_performed": False,
        "sample_tax_reduction_claimed": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "broad_world_model_synthesis_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "exact_factor_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExactFactorPreregistrationV15:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("exact-factor preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("exact-factor preregistration bytes changed")
        payload = {key: value for key, value in document.items() if key != "exact_factor_preregistration_id"}
        if (
            document.get("exact_factor_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("exact-factor preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("exact-factor preregistration is not an object")
        return document


def freeze_standard_2048_exact_factor_preregistration_v15(
) -> Standard2048ExactFactorPreregistrationV15:
    document = _document()
    if document["exact_factor_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen exact-factor preregistration identity changed")
    return Standard2048ExactFactorPreregistrationV15(
        _ISSUER,
        canonical_json_bytes(document),
        document["exact_factor_preregistration_id"],
    )


def verify_standard_2048_exact_factor_preregistration_v15(
    value: Standard2048ExactFactorPreregistrationV15,
) -> Standard2048ExactFactorPreregistrationV15:
    if type(value) is not Standard2048ExactFactorPreregistrationV15:
        _fail("exact-factor preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("exact-factor preregistration differs from frozen semantics")
    return value


__all__ = (
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "STANDARD_2048_SOURCE_BYTE_COUNT",
    "STANDARD_2048_SOURCE_SHA256",
    "Standard2048ExactFactorPreregistrationV15",
    "freeze_standard_2048_exact_factor_preregistration_v15",
    "verify_standard_2048_exact_factor_preregistration_v15",
)
