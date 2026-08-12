"""Outcome-free preregistration for the V0-159 exchangeability campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_spawn_support_observation_v2 as observations
from acfqp.domains.standard_2048 import boards_from_rows_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_CAMPAIGN_V5_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_CERTIFICATE_V5_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_EPISODE_V5_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_PREREGISTRATION_V5_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_ROUTE_DECISION_V5_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_VERIFICATION_V5_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "5.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.159"
PROFILE_KEY = "construction_k7_standard_2048_exchangeability_campaign_v5"
PREDECESSOR_V158_CAMPAIGN_ID = (
    "c97eb0a954aeb1cffe937a47b326bc8fd2a41ea27d319dffe817410870d5b6b6"
)
SOURCE_CHECKPOINTS_PER_CARDINALITY = (8, 32, 128, 512, 2048, 8192)
VALIDATION_CHECKPOINTS_PER_CARDINALITY = (4, 16, 64, 256, 1024)
POSITION_RADII = {
    8: Fraction(1),
    32: Fraction(1, 2),
    128: Fraction(1, 4),
    512: Fraction(1, 8),
    2048: Fraction(1, 16),
    8192: Fraction(1, 32),
}
RANK_RADII = {
    8: Fraction(1, 4),
    32: Fraction(1, 8),
    128: Fraction(1, 16),
    512: Fraction(1, 32),
    2048: Fraction(1, 64),
    8192: Fraction(1, 128),
}
PLANNING_HORIZON = 2
DECISIONS_PER_EPISODE = 12

PREREGISTERED_INITIAL_BOARDS = (
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 1, 0, 1))),
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (1, 0, 0, 1))),
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 2, 2))),
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 2, 0, 2))),
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 2, 1))),
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 2, 0, 1))),
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 1, 2))),
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 1, 0, 2))),
)
PREREGISTERED_EPISODE_SEEDS = tuple(
    f"standard-2048-v159-preregistered-{index:02d}-20260812"
    for index in range(len(PREREGISTERED_INITIAL_BOARDS))
)

FUTURE_DOMAINS = {
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_CERTIFICATE_V5_DOMAIN,
    "route_decision": CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_ROUTE_DECISION_V5_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_EPISODE_V5_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_CAMPAIGN_V5_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_VERIFICATION_V5_DOMAIN,
}


class ConstructionK7Standard2048ExchangeabilityPreregistrationV5Error(ValueError):
    """The frozen V0-159 target or algorithm protocol changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExchangeabilityPreregistrationV5Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _document() -> dict[str, Any]:
    evidence = observations.build_standard_2048_spawn_support_evidence_v2()
    payload = {
        "schema": "acfqp.standard_2048_exchangeability_preregistration.v5",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "predecessor_v158_campaign_id": PREDECESSOR_V158_CAMPAIGN_ID,
        "support_source_archive_id": evidence.source_archive_id,
        "support_validation_archive_id": evidence.validation_archive_id,
        "raw_observation_profile_key": observations.PROFILE_KEY,
        "source_checkpoints_per_cardinality": list(
            SOURCE_CHECKPOINTS_PER_CARDINALITY
        ),
        "validation_checkpoints_per_cardinality": list(
            VALIDATION_CHECKPOINTS_PER_CARDINALITY
        ),
        "position_radii": [
            {"checkpoint": count, "radius": _fdoc(POSITION_RADII[count])}
            for count in SOURCE_CHECKPOINTS_PER_CARDINALITY
        ],
        "rank_radii": [
            {"checkpoint": count, "radius": _fdoc(RANK_RADII[count])}
            for count in SOURCE_CHECKPOINTS_PER_CARDINALITY
        ],
        "nested_prefix_observations_charged_once": True,
        "maximum_offline_transition_observation_count": 16
        * (
            observations.SOURCE_RECORDS_PER_CARDINALITY
            + observations.VALIDATION_RECORDS_PER_CARDINALITY
        ),
        "planning_horizon": PLANNING_HORIZON,
        "decisions_per_episode": DECISIONS_PER_EPISODE,
        "preregistered_initial_boards": [
            list(board) for board in PREREGISTERED_INITIAL_BOARDS
        ],
        "preregistered_episode_seeds": list(PREREGISTERED_EPISODE_SEEDS),
        "episode_count": len(PREREGISTERED_INITIAL_BOARDS),
        "decision_count": len(PREREGISTERED_INITIAL_BOARDS)
        * DECISIONS_PER_EPISODE,
        "structural_meta_prior_arm": {
            "position_law_semantics": (
                "ONE_SHARED_SORTED_ORDINAL_DISTRIBUTION_PER_EMPTY_CARDINALITY"
            ),
            "pairwise_dominance_reducer": (
                "SHARED_CARDINALITY_POSITION_LAW_DIFFERENCE_BOX_LP"
            ),
            "rank_probability_semantics": "ONE_GLOBAL_SHARED_INTERVAL",
            "first_passing_checkpoint_stops": True,
            "failed_checkpoint_can_only_escalate_to_next_registered_prefix": True,
            "cap_failure_route": "COLD_GROUND_FALLBACK",
        },
        "strict_no_prior_arm": {
            "position_law_semantics": (
                "INDEPENDENT_STATE_ACTION_RECTANGULAR_POSITION_BOXES"
            ),
            "pairwise_dominance_reducer": (
                "CANDIDATE_LOWER_VERSUS_CHALLENGER_UPPER"
            ),
            "rank_probability_semantics": "ONE_GLOBAL_SHARED_INTERVAL",
            "same_prefixes_radii_cap_and_fallback": True,
        },
        "matched_cold_direct_control": {
            "one_fresh_model_per_decision": True,
            "evaluation_only": True,
            "no_route_or_stopping_authority": True,
        },
        "required_positive_condition": (
            "EVERY_SELECTED_ACTION_EXACT_VALUE_AND_LOSS_EQUIVALENT_TO_"
            "MATCHED_COLD_DIRECT"
        ),
        "required_comparison": (
            "META_PRIOR_ABSTRACT_ROUTE_COUNT_VERSUS_STRICT_NO_PRIOR_AND_DIRECT"
        ),
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "algorithm_implementation_present": False,
        "external_timestamp_authority_present": False,
        "local_git_preregistration_intended_before_v5_execution": True,
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
        "exchangeability_preregistration_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_PREREGISTRATION_V5_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExchangeabilityPreregistrationV5:
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
            or document.get("exchangeability_preregistration_id")
            != self.preregistration_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_PREREGISTRATION_V5_DOMAIN,
                {
                    key: value
                    for key, value in document.items()
                    if key != "exchangeability_preregistration_id"
                },
            )
            != self.preregistration_id
        ):
            _fail("preregistration bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("preregistration root is not an object")
        return document


def freeze_standard_2048_exchangeability_preregistration_v5(
) -> Standard2048ExchangeabilityPreregistrationV5:
    document = _document()
    return Standard2048ExchangeabilityPreregistrationV5(
        _ISSUER,
        canonical_json_bytes(document),
        document["exchangeability_preregistration_id"],
    )


def verify_standard_2048_exchangeability_preregistration_v5(
    preregistration: Standard2048ExchangeabilityPreregistrationV5,
) -> Standard2048ExchangeabilityPreregistrationV5:
    if type(preregistration) is not Standard2048ExchangeabilityPreregistrationV5:
        _fail("preregistration verifier rejects foreign values")
    preregistration.__post_init__()
    if preregistration.canonical_bytes != canonical_json_bytes(_document()):
        _fail("preregistration differs from exact replay")
    return preregistration


__all__ = (
    "ConstructionK7Standard2048ExchangeabilityPreregistrationV5Error",
    "FUTURE_DOMAINS",
    "PREREGISTERED_EPISODE_SEEDS",
    "PREREGISTERED_INITIAL_BOARDS",
    "PROFILE_KEY",
    "Standard2048ExchangeabilityPreregistrationV5",
    "freeze_standard_2048_exchangeability_preregistration_v5",
    "verify_standard_2048_exchangeability_preregistration_v5",
)
