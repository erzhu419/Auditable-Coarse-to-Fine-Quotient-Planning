"""Exact outcome-free preregistration for targeted 2048 acquisition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.domains.standard_2048 import boards_from_rows_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_TARGETED_CAMPAIGN_V7_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_TARGETED_CERTIFICATE_V7_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_TARGETED_EPISODE_V7_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_TARGETED_PREREGISTRATION_V7_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_TARGETED_ROUTE_DECISION_V7_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_TARGETED_SOURCE_ARCHIVE_V7_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_TARGETED_VALIDATION_ARCHIVE_V7_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_TARGETED_VERIFICATION_V7_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "7.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.161"
PROFILE_KEY = "construction_k7_standard_2048_targeted_acquisition_v7"
PREDECESSOR_V160_PREREGISTRATION_ID = (
    "7e51518e2a81f6db89947b980677bb9b20b99f408ae4cc29be5164f88d853bb8"
)
SOURCE_STREAM_DOMAIN = "acfqp:standard-2048-targeted-source-stream:v7"
VALIDATION_STREAM_DOMAIN = "acfqp:standard-2048-targeted-validation-stream:v7"
SOURCE_SEED = "standard-2048-v161-targeted-source-20260812"
VALIDATION_SEED = "standard-2048-v161-targeted-validation-20260812"
SOURCE_RECORDS_PER_CARDINALITY = 8192
VALIDATION_RECORDS_PER_CARDINALITY = 1024
TARGETED_SOURCE_LEVELS = (8, 16, 64, 256, 1024, 4096, 8192)
GLOBAL_SOURCE_LEVELS = (8, 32, 128, 512, 2048, 8192)
GLOBAL_VALIDATION_LEVELS = (4, 16, 64, 256, 1024)
RADIUS_SQUARED_NUMERATOR = 8
RADIUS_GRID_DENOMINATOR = 65536
PLANNING_HORIZON = 2
DECISIONS_PER_EPISODE = 16
MAXIMUM_UNIQUE_OFFLINE_OBSERVATIONS = 147456
SUPPORT_CANDIDATES = (
    "ALL_SORTED_EMPTY_ORDINALS",
    "FIRST_EMPTY_ORDINAL_ONLY",
    "LAST_EMPTY_ORDINAL_ONLY",
    "EVEN_EMPTY_ORDINALS_ONLY",
)
SELECTED_SUPPORT_RULE = "ALL_SORTED_EMPTY_ORDINALS"

PREREGISTERED_INITIAL_BOARDS = tuple(
    boards_from_rows_v1(rows)
    for rows in (
        ((0, 1, 0, 0), (0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((0, 1, 0, 0), (0, 0, 0, 1), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((0, 1, 0, 0), (0, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 0)),
        ((0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0)),
        ((0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 0, 0)),
        ((0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 1, 0, 0)),
        ((0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 1, 0)),
    )
)
PREREGISTERED_EPISODE_SEEDS = tuple(
    f"standard-2048-v161-targeted-{index:02d}-20260812"
    for index in range(len(PREREGISTERED_INITIAL_BOARDS))
)
FUTURE_DOMAINS = {
    "source_archive": CONSTRUCTION_K7_STANDARD_2048_TARGETED_SOURCE_ARCHIVE_V7_DOMAIN,
    "validation_archive": CONSTRUCTION_K7_STANDARD_2048_TARGETED_VALIDATION_ARCHIVE_V7_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_TARGETED_CERTIFICATE_V7_DOMAIN,
    "route_decision": CONSTRUCTION_K7_STANDARD_2048_TARGETED_ROUTE_DECISION_V7_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_TARGETED_EPISODE_V7_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_TARGETED_CAMPAIGN_V7_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_TARGETED_VERIFICATION_V7_DOMAIN,
}


class ConstructionK7Standard2048TargetedAcquisitionPreregistrationV7Error(
    ValueError
):
    """The frozen V0-161 workload or exact acquisition protocol changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048TargetedAcquisitionPreregistrationV7Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_targeted_acquisition_preregistration.v7",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "predecessor_v160_preregistration_id": PREDECESSOR_V160_PREREGISTRATION_ID,
        "v160_used_for_development_only": True,
        "v160_not_eligible_as_v161_confirmatory_evidence": True,
        "source_stream_domain": SOURCE_STREAM_DOMAIN,
        "validation_stream_domain": VALIDATION_STREAM_DOMAIN,
        "source_seed": SOURCE_SEED,
        "validation_seed": VALIDATION_SEED,
        "source_records_per_cardinality": SOURCE_RECORDS_PER_CARDINALITY,
        "validation_records_per_cardinality": VALIDATION_RECORDS_PER_CARDINALITY,
        "raw_record_generator": (
            "SHA256_DOMAIN_NUL_SEED_NUL_CARDINALITY_NUL_INDEX_NUL_"
            "POSITION_OR_RANK_V1"
        ),
        "spawned_rank_two_rule": "UINT256_SHA256_TIMES_10_LT_2_POW_256",
        "position_ordinal_rule": "FLOOR_UINT256_SHA256_TIMES_CARDINALITY_DIV_2_POW_256",
        "targeted_source_levels": list(TARGETED_SOURCE_LEVELS),
        "targeted_validation_count_rule": "MIN_SOURCE_COUNT_DIV_2_1024",
        "global_source_levels": list(GLOBAL_SOURCE_LEVELS),
        "global_validation_levels": list(GLOBAL_VALIDATION_LEVELS),
        "position_radius_rule": (
            "CEIL_SQRT_8_DIV_SOURCE_COUNT_ON_1_DIV_65536_GRID"
        ),
        "rank_radius_rule": (
            "CEIL_SQRT_8_DIV_TOTAL_UNIQUE_SOURCE_COUNT_ON_1_DIV_65536_GRID"
        ),
        "radius_squared_numerator": RADIUS_SQUARED_NUMERATOR,
        "radius_grid_denominator": RADIUS_GRID_DENOMINATOR,
        "support_candidates": list(SUPPORT_CANDIDATES),
        "selected_support_rule": SELECTED_SUPPORT_RULE,
        "heldout_rule": "ALL_VALIDATION_EMPIRICAL_VALUES_MUST_LIE_IN_INTERVALS",
        "conditional_confidence_only": True,
        "physical_iid_randomness_claimed": False,
        "planning_horizon": PLANNING_HORIZON,
        "decisions_per_episode": DECISIONS_PER_EPISODE,
        "preregistered_initial_boards": [
            list(board) for board in PREREGISTERED_INITIAL_BOARDS
        ],
        "preregistered_episode_seeds": list(PREREGISTERED_EPISODE_SEEDS),
        "episode_count": len(PREREGISTERED_INITIAL_BOARDS),
        "decision_count": len(PREREGISTERED_INITIAL_BOARDS)
        * DECISIONS_PER_EPISODE,
        "frontier_conditioned_arm": {
            "initial_source_count_per_cardinality": 8,
            "initial_validation_count_per_cardinality": 4,
            "candidate_selection": (
                "MAXIMIZE_MINIMUM_ENDPOINT_PAIRWISE_MARGIN_THEN_ACTION_ORDER"
            ),
            "blocker_selection": "MOST_NEGATIVE_PAIRWISE_MARGIN_FOR_SELECTED_CANDIDATE",
            "frontier_cardinalities": (
                "CANDIDATE_AND_BLOCKER_POST_SWIPE_EMPTY_CARDINALITIES"
            ),
            "upgrade_rule": "EACH_FRONTIER_CARDINALITY_TO_NEXT_TARGETED_SOURCE_LEVEL",
            "unaffected_cardinalities_reused": True,
            "global_rank_interval_uses_all_unique_acquired_source_rows": True,
            "all_actions_must_have_zero_loss_structural_witness": True,
            "zero_loss_failure_is_not_sample_repairable": True,
            "hard_cap_route": "COLD_GROUND_FALLBACK",
        },
        "matched_global_prefix_control": {
            "initial_global_level": 8,
            "failed_certificate_upgrades_all_cardinalities_to_next_global_level": True,
            "checkpoint_persists_across_occurrences": True,
            "same_support_pairwise_certificate_and_fallback": True,
        },
        "matched_cold_direct_control": {
            "one_fresh_exact_model_per_decision": True,
            "evaluation_only_unless_selected_fallback": True,
            "no_certificate_acquisition_or_route_authority": True,
        },
        "maximum_unique_offline_transition_observation_count": (
            MAXIMUM_UNIQUE_OFFLINE_OBSERVATIONS
        ),
        "required_positive_conditions": [
            "ALL_SELECTED_ACTIONS_EXACT_VALUE_AND_LOSS_EQUIVALENT_TO_COLD_DIRECT",
            "TARGETED_UNIQUE_OFFLINE_OBSERVATIONS_LT_GLOBAL_CONTROL",
        ],
        "if_any_required_condition_fails": (
            "REPORT_PREREGISTERED_NEGATIVE_RESULT_AND_PRESERVE_FALLBACK"
        ),
        "outcome_fields_present": False,
        "raw_observation_streams_generated": False,
        "target_execution_performed": False,
        "algorithm_implementation_present": False,
        "external_timestamp_authority_present": False,
        "formal_confirmatory_gate_claimed": False,
        "full_standard_2048_game_claimed": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "targeted_acquisition_preregistration_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_PREREGISTRATION_V7_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048TargetedAcquisitionPreregistrationV7:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "targeted_acquisition_preregistration_id"
        }
        if (
            document.get("targeted_acquisition_preregistration_id")
            != self.preregistration_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_TARGETED_PREREGISTRATION_V7_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("targeted preregistration root is not an object")
        return document


def freeze_standard_2048_targeted_acquisition_preregistration_v7(
) -> Standard2048TargetedAcquisitionPreregistrationV7:
    document = _document()
    return Standard2048TargetedAcquisitionPreregistrationV7(
        _ISSUER,
        canonical_json_bytes(document),
        document["targeted_acquisition_preregistration_id"],
    )


def verify_standard_2048_targeted_acquisition_preregistration_v7(
    value: Standard2048TargetedAcquisitionPreregistrationV7,
) -> Standard2048TargetedAcquisitionPreregistrationV7:
    if type(value) is not Standard2048TargetedAcquisitionPreregistrationV7:
        _fail("verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("preregistration differs from frozen semantics")
    return value


__all__ = (
    "ConstructionK7Standard2048TargetedAcquisitionPreregistrationV7Error",
    "DECISIONS_PER_EPISODE",
    "FUTURE_DOMAINS",
    "GLOBAL_SOURCE_LEVELS",
    "GLOBAL_VALIDATION_LEVELS",
    "MAXIMUM_UNIQUE_OFFLINE_OBSERVATIONS",
    "PLANNING_HORIZON",
    "PREREGISTERED_EPISODE_SEEDS",
    "PREREGISTERED_INITIAL_BOARDS",
    "PROFILE_KEY",
    "RADIUS_GRID_DENOMINATOR",
    "RADIUS_SQUARED_NUMERATOR",
    "SELECTED_SUPPORT_RULE",
    "SOURCE_RECORDS_PER_CARDINALITY",
    "SOURCE_SEED",
    "SOURCE_STREAM_DOMAIN",
    "SUPPORT_CANDIDATES",
    "Standard2048TargetedAcquisitionPreregistrationV7",
    "TARGETED_SOURCE_LEVELS",
    "VALIDATION_RECORDS_PER_CARDINALITY",
    "VALIDATION_SEED",
    "VALIDATION_STREAM_DOMAIN",
    "freeze_standard_2048_targeted_acquisition_preregistration_v7",
    "verify_standard_2048_targeted_acquisition_preregistration_v7",
)
