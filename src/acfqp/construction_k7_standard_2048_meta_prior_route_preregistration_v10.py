"""Outcome-free H3 preregistration for a matched meta-prior sample-tax route."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.domains.standard_2048 import boards_from_rows_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_CAMPAIGN_V10_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_CERTIFICATE_V10_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_EPISODE_V10_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_OPERATOR_V10_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_PREREGISTRATION_V10_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_VERIFICATION_V10_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "10.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.166"
PROFILE_KEY = "construction_k7_standard_2048_meta_prior_route_v10"
PREREGISTRATION_ID = (
    "193f9ac5846beb31ffb5035461bb0ceb3562f1bed459e22356fbd32b5de523e5"
)
V159_EXCHANGEABILITY_CAMPAIGN_ID = (
    "aa617ad2caa6f59692e891f929cea386ff800fc0a0b52db53ebf10ac21a20225"
)
V161_TARGETED_CAMPAIGN_ID = (
    "34b184f1ab30567da483d3132331eacdac20b50648780bb828f13013102170ab"
)
V164_FACTORED_CAMPAIGN_ID = (
    "48c920ec560529c433b81cb24c784f52b67e6ce2acf9ad746edda8b5635e40d8"
)
PLANNING_HORIZON = 3
DECISIONS_PER_EPISODE = 16
META_PRIOR_SOURCE_PREFIX_PER_CARDINALITY = 8
META_PRIOR_VALIDATION_PREFIX_PER_CARDINALITY = 4
META_PRIOR_OFFLINE_OBSERVATION_COUNT = 16 * (
    META_PRIOR_SOURCE_PREFIX_PER_CARDINALITY
    + META_PRIOR_VALIDATION_PREFIX_PER_CARDINALITY
)
OBSERVATION_ONLY_OFFLINE_OBSERVATION_COUNT = 55788

PREREGISTERED_INITIAL_BOARDS = tuple(
    boards_from_rows_v1(rows)
    for rows in (
        ((1, 0, 0, 2), (0, 0, 1, 0), (0, 3, 0, 0), (0, 0, 0, 0)),
        ((0, 2, 0, 0), (1, 0, 0, 3), (0, 0, 1, 0), (0, 0, 0, 0)),
        ((0, 0, 3, 0), (0, 1, 0, 0), (2, 0, 0, 0), (0, 0, 0, 1)),
        ((0, 0, 0, 0), (0, 1, 0, 3), (2, 0, 0, 0), (0, 0, 1, 0)),
    )
)
PREREGISTERED_EPISODE_SEEDS = tuple(
    f"standard-2048-v166-meta-route-{index:02d}-20260813"
    for index in range(len(PREREGISTERED_INITIAL_BOARDS))
)

FUTURE_DOMAINS = {
    "preregistration": (
        CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_PREREGISTRATION_V10_DOMAIN
    ),
    "operator": CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_OPERATOR_V10_DOMAIN,
    "certificate": (
        CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_CERTIFICATE_V10_DOMAIN
    ),
    "episode": CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_EPISODE_V10_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_CAMPAIGN_V10_DOMAIN,
    "verification": (
        CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_VERIFICATION_V10_DOMAIN
    ),
}


class ConstructionK7Standard2048MetaPriorRoutePreregistrationV10Error(
    ValueError
):
    """The frozen workload, prior/control split, route, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048MetaPriorRoutePreregistrationV10Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_meta_prior_route_preregistration.v10",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "v159_exchangeability_campaign_id": V159_EXCHANGEABILITY_CAMPAIGN_ID,
        "v161_targeted_campaign_id": V161_TARGETED_CAMPAIGN_ID,
        "v164_factored_campaign_id": V164_FACTORED_CAMPAIGN_ID,
        "v159_v161_v164_are_frozen_predecessor_evidence_only": True,
        "fresh_target_identities_required": True,
        "planning_horizon": PLANNING_HORIZON,
        "decisions_per_episode": DECISIONS_PER_EPISODE,
        "preregistered_initial_boards": [
            list(board) for board in PREREGISTERED_INITIAL_BOARDS
        ],
        "preregistered_episode_seeds": list(PREREGISTERED_EPISODE_SEEDS),
        "episode_count": len(PREREGISTERED_INITIAL_BOARDS),
        "decision_count_per_arm": (
            len(PREREGISTERED_INITIAL_BOARDS) * DECISIONS_PER_EPISODE
        ),
        "matched_arms": {
            "STRUCTURAL_META_PRIOR": {
                "position_law": (
                    "REGISTERED_EXACT_UNIFORM_EXCHANGEABILITY_GIVEN_EMPTY_COUNT"
                ),
                "rank_law": "SHARED_BERNOULLI_INTERVAL_FROM_POOLED_PREFIX",
                "source_prefix_per_cardinality": (
                    META_PRIOR_SOURCE_PREFIX_PER_CARDINALITY
                ),
                "validation_prefix_per_cardinality": (
                    META_PRIOR_VALIDATION_PREFIX_PER_CARDINALITY
                ),
                "unique_offline_transition_observation_count": (
                    META_PRIOR_OFFLINE_OBSERVATION_COUNT
                ),
                "prior_training_observation_count": 0,
                "uniform_exchangeability_is_registered_prior": True,
                "uniform_exchangeability_proven_by_finite_samples": False,
                "conditional_on_registered_shared_law_family": True,
            },
            "STRICT_OBSERVATION_ONLY": {
                "position_law": "V161_CARDINALITY_SPECIFIC_INTERVAL_VECTOR",
                "rank_law": "V161_SHARED_BERNOULLI_INTERVAL",
                "unique_offline_transition_observation_count": (
                    OBSERVATION_ONLY_OFFLINE_OBSERVATION_COUNT
                ),
                "structural_uniform_position_prior_used": False,
                "v161_archive_and_identity_set_reused_exactly": True,
            },
        },
        "shared_factored_execution_semantics": {
            "deterministic_component": "WHOLE_BOARD_SWIPE",
            "support_component": "ALL_SORTED_EMPTY_ORDINALS_CROSS_RANKS_1_2",
            "successors_generated_lazily_inside_bellman_backup": True,
            "state_action_rows_serialized_or_persisted": False,
            "exact_rational_arithmetic_required": True,
            "operator_reused_across_all_decisions_in_each_arm": True,
        },
        "route_protocol": {
            "predecision_access": [
                "FROZEN_INITIAL_OR_PREVIOUS_TARGET_STATE",
                "FROZEN_OPERATOR_AND_INTERVAL_EVIDENCE",
                "FACTORED_H3_BELLMAN_SUBPROOFS",
            ],
            "certificate": (
                "ONE_ROOT_ACTION_SCORE_LOWER_STRICTLY_EXCEEDS_EVERY_"
                "CHALLENGER_SCORE_UPPER"
            ),
            "abstract_route_only_after_certificate": True,
            "certificate_failure_route": "COLD_EXACT_DIRECT_GROUND_FALLBACK",
            "ground_access_before_certificate_freeze": False,
            "fallback_work_not_rolled_back": True,
            "matched_cold_direct_has_no_certificate_or_route_authority": True,
        },
        "required_positive_conditions": [
            "META_PRIOR_OFFLINE_OBSERVATION_COUNT_LT_STRICT_OBSERVATION_ONLY",
            "ALL_ABSTRACT_ROUTES_HAVE_STRICT_ROOT_DOMINANCE_CERTIFICATES",
            "ALL_SELECTED_ACTIONS_EXACT_VALUE_AND_LOSS_EQUIVALENT",
            "GROUND_FALLBACK_OCCURS_ONLY_AFTER_CERTIFICATE_FAILURE",
            "FACTORED_OPERATIONAL_SERIALIZED_AND_PERSISTENT_ROWS_EQUAL_ZERO",
        ],
        "sample_tax_axes": {
            "offline_acquisition_observations": "SEPARATE_INTEGER_COUNT",
            "factored_successor_evaluations": "SEPARATE_INTEGER_COUNT",
            "ground_fallback_rows_and_outcomes": "SEPARATE_INTEGER_COUNTS",
            "process_and_io_accounting": "DEFERRED_TO_K7_COUNTER_CHAIN",
            "scalar_combination_forbidden": True,
        },
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "meta_route_implementation_present": False,
        "prior_guaranteed_correct_outside_registered_family": False,
        "physical_iid_randomness_claimed": False,
        "open_ended_operator_invention_claimed": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "formal_confirmatory_gate_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "meta_prior_route_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048MetaPriorRoutePreregistrationV10:
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
            if key != "meta_prior_route_preregistration_id"
        }
        if (
            document.get("meta_prior_route_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("meta-prior route preregistration is not an object")
        return document


def freeze_standard_2048_meta_prior_route_preregistration_v10(
) -> Standard2048MetaPriorRoutePreregistrationV10:
    document = _document()
    if document["meta_prior_route_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen preregistration identity changed")
    return Standard2048MetaPriorRoutePreregistrationV10(
        _ISSUER,
        canonical_json_bytes(document),
        document["meta_prior_route_preregistration_id"],
    )


def verify_standard_2048_meta_prior_route_preregistration_v10(
    value: Standard2048MetaPriorRoutePreregistrationV10,
) -> Standard2048MetaPriorRoutePreregistrationV10:
    if type(value) is not Standard2048MetaPriorRoutePreregistrationV10:
        _fail("verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("preregistration differs from frozen semantics")
    return value


__all__ = (
    "ConstructionK7Standard2048MetaPriorRoutePreregistrationV10Error",
    "DECISIONS_PER_EPISODE",
    "FUTURE_DOMAINS",
    "META_PRIOR_OFFLINE_OBSERVATION_COUNT",
    "OBSERVATION_ONLY_OFFLINE_OBSERVATION_COUNT",
    "PLANNING_HORIZON",
    "PREREGISTERED_EPISODE_SEEDS",
    "PREREGISTERED_INITIAL_BOARDS",
    "PREREGISTRATION_ID",
    "Standard2048MetaPriorRoutePreregistrationV10",
    "freeze_standard_2048_meta_prior_route_preregistration_v10",
    "verify_standard_2048_meta_prior_route_preregistration_v10",
)
