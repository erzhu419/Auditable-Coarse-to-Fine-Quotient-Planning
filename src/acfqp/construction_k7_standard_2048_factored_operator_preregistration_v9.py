"""Outcome-free preregistration of a factored H3 spawn operator control."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.domains.standard_2048 import boards_from_rows_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_FACTORED_CAMPAIGN_V9_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FACTORED_EPISODE_V9_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FACTORED_OPERATOR_V9_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FACTORED_PREREGISTRATION_V9_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FACTORED_VERIFICATION_V9_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "9.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.164"
PROFILE_KEY = "construction_k7_standard_2048_factored_spawn_operator_v9"
PREREGISTRATION_ID = (
    "85aa54f3fa3cafbf3e9a68b77a666c2c7061df52e020144283ad2d32f8f8a822"
)
PREDECESSOR_V161_CAMPAIGN_ID = (
    "34b184f1ab30567da483d3132331eacdac20b50648780bb828f13013102170ab"
)
DEVELOPMENT_V163_CAMPAIGN_ID = (
    "e4cd9db57964ace8ba639a41fb76acda8c7e994a02de1e3e0bfa642fe5300b4e"
)
PLANNING_HORIZON = 3
DECISIONS_PER_EPISODE = 8

PREREGISTERED_INITIAL_BOARDS = tuple(
    boards_from_rows_v1(rows)
    for rows in (
        ((0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 2, 0), (0, 0, 0, 1)),
        ((0, 0, 1, 0), (2, 0, 0, 0), (0, 0, 0, 0), (0, 1, 0, 0)),
        ((0, 0, 0, 1), (0, 2, 0, 0), (1, 0, 0, 0), (0, 0, 0, 0)),
        ((0, 0, 0, 0), (1, 0, 0, 2), (0, 0, 3, 0), (0, 0, 0, 0)),
    )
)
PREREGISTERED_EPISODE_SEEDS = tuple(
    f"standard-2048-v164-factored-{index:02d}-20260813"
    for index in range(len(PREREGISTERED_INITIAL_BOARDS))
)

FUTURE_DOMAINS = {
    "preregistration": (
        CONSTRUCTION_K7_STANDARD_2048_FACTORED_PREREGISTRATION_V9_DOMAIN
    ),
    "operator": CONSTRUCTION_K7_STANDARD_2048_FACTORED_OPERATOR_V9_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_FACTORED_EPISODE_V9_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_FACTORED_CAMPAIGN_V9_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_FACTORED_VERIFICATION_V9_DOMAIN,
}


class ConstructionK7Standard2048FactoredOperatorPreregistrationV9Error(
    ValueError
):
    """The frozen factored-operator workload or comparison changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048FactoredOperatorPreregistrationV9Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_factored_operator_preregistration.v9",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "predecessor_v161_campaign_id": PREDECESSOR_V161_CAMPAIGN_ID,
        "development_v163_campaign_id": DEVELOPMENT_V163_CAMPAIGN_ID,
        "v163_used_for_algorithm_design_only": True,
        "v163_observed_63135_materialized_rows": True,
        "v163_observed_one_exact_value_mismatch": True,
        "fresh_target_identities_required": True,
        "planning_horizon": PLANNING_HORIZON,
        "decisions_per_episode": DECISIONS_PER_EPISODE,
        "preregistered_initial_boards": [
            list(board) for board in PREREGISTERED_INITIAL_BOARDS
        ],
        "preregistered_episode_seeds": list(PREREGISTERED_EPISODE_SEEDS),
        "episode_count": len(PREREGISTERED_INITIAL_BOARDS),
        "decision_count": len(PREREGISTERED_INITIAL_BOARDS)
        * DECISIONS_PER_EPISODE,
        "reused_offline_observation_count": 55788,
        "additional_offline_observation_budget": 0,
        "offline_observations_charged_once_at_shared_campaign_level": True,
        "factored_operator_semantics": {
            "deterministic_component": "WHOLE_BOARD_SWIPE",
            "support_component": (
                "ALL_SORTED_POST_SWIPE_EMPTY_ORDINALS_CROSS_RANKS_1_2"
            ),
            "position_component": (
                "V161_CARDINALITY_CONDITIONAL_INTERVAL_VECTOR"
            ),
            "rank_component": "V161_SHARED_RANK_TWO_INTERVAL",
            "unknown_support_mass_within_registered_family": 0,
            "state_action_rows_serialized_or_persisted": False,
            "successors_generated_lazily_inside_bellman_backup": True,
            "operator_identity_reused_across_all_decisions": True,
            "conditional_on_registered_support_candidate_family": True,
            "open_ended_operator_invention_claimed": False,
        },
        "matched_explicit_row_control": {
            "same_support_proposal_and_intervals": True,
            "same_exact_rational_robust_bellman_recurrence": True,
            "rows_materialized_only_in_evaluation_control": True,
            "control_has_no_route_or_target_authority": True,
        },
        "matched_cold_direct_control": {
            "horizon": PLANNING_HORIZON,
            "evaluation_only_unless_operational_fallback_selected": True,
            "quality_mismatch_reported_without_suppression": True,
        },
        "required_positive_conditions": [
            "FACTORED_AND_EXPLICIT_SELECTED_ACTIONS_AND_ROBUST_VALUES_IDENTICAL",
            "FACTORED_OPERATIONAL_SERIALIZED_STATE_ACTION_ROW_COUNT_EQUALS_ZERO",
            "ADDITIONAL_OFFLINE_OBSERVATION_COUNT_EQUALS_ZERO",
            "FACTORED_OPERATOR_IDENTITY_REUSED_ACROSS_ALL_DECISIONS",
        ],
        "exact_quality_mismatch_policy": (
            "REPORT_NEGATIVE_QUALITY_RESULT_AND_PRESERVE_COLD_FALLBACK"
        ),
        "sample_tax_claim_boundary": {
            "offline_acquisition_tax_measured": True,
            "serialized_local_distinction_tax_measured": True,
            "bellman_compute_tax_measured_separately": True,
            "total_operational_work_saving_claimed": False,
        },
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "factored_operator_implementation_present": False,
        "formal_confirmatory_gate_claimed": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "factored_operator_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048FactoredOperatorPreregistrationV9:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "factored_operator_preregistration_id"
        }
        if (
            document.get("factored_operator_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("factored preregistration root is not an object")
        return document


def freeze_standard_2048_factored_operator_preregistration_v9(
) -> Standard2048FactoredOperatorPreregistrationV9:
    document = _document()
    if document["factored_operator_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen preregistration identity changed")
    return Standard2048FactoredOperatorPreregistrationV9(
        _ISSUER,
        canonical_json_bytes(document),
        document["factored_operator_preregistration_id"],
    )


def verify_standard_2048_factored_operator_preregistration_v9(
    value: Standard2048FactoredOperatorPreregistrationV9,
) -> Standard2048FactoredOperatorPreregistrationV9:
    if type(value) is not Standard2048FactoredOperatorPreregistrationV9:
        _fail("verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("preregistration differs from frozen semantics")
    return value


__all__ = (
    "ConstructionK7Standard2048FactoredOperatorPreregistrationV9Error",
    "DECISIONS_PER_EPISODE",
    "FUTURE_DOMAINS",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "PREREGISTERED_EPISODE_SEEDS",
    "PREREGISTERED_INITIAL_BOARDS",
    "PROFILE_KEY",
    "Standard2048FactoredOperatorPreregistrationV9",
    "freeze_standard_2048_factored_operator_preregistration_v9",
    "verify_standard_2048_factored_operator_preregistration_v9",
)
