"""Outcome-free preregistration for frontier-conditioned 2048 acquisition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.domains.standard_2048 import boards_from_rows_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_CAMPAIGN_V6_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_CERTIFICATE_V6_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_EPISODE_V6_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_PREREGISTRATION_V6_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_ROUTE_DECISION_V6_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_VERIFICATION_V6_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "6.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.160"
PROFILE_KEY = "construction_k7_standard_2048_frontier_acquisition_v6"
PREDECESSOR_V159_CAMPAIGN_ID = (
    "aa617ad2caa6f59692e891f929cea386ff800fc0a0b52db53ebf10ac21a20225"
)
PLANNING_HORIZON = 2
DECISIONS_PER_EPISODE = 16
GLOBAL_PREFIX_CHECKPOINTS = (8, 32, 128, 512, 2048, 8192)
TARGETED_ADDITIONAL_CHECKPOINTS = (16, 64, 256, 1024, 4096, 16384)
MAXIMUM_UNIQUE_OFFLINE_OBSERVATIONS = 147456

PREREGISTERED_INITIAL_BOARDS = tuple(
    boards_from_rows_v1(rows)
    for rows in (
        ((1, 1, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((1, 0, 0, 0), (0, 0, 0, 1), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((1, 0, 0, 0), (0, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0)),
        ((1, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 0, 0)),
        ((0, 1, 1, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
    )
)
PREREGISTERED_EPISODE_SEEDS = tuple(
    f"standard-2048-v160-frontier-{index:02d}-20260812"
    for index in range(len(PREREGISTERED_INITIAL_BOARDS))
)
FUTURE_DOMAINS = {
    "certificate": CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_CERTIFICATE_V6_DOMAIN,
    "route_decision": CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_ROUTE_DECISION_V6_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_EPISODE_V6_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_CAMPAIGN_V6_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_VERIFICATION_V6_DOMAIN,
}


class ConstructionK7Standard2048FrontierAcquisitionPreregistrationV6Error(
    ValueError
):
    """The frozen V0-160 target, budget, or algorithm changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048FrontierAcquisitionPreregistrationV6Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_frontier_acquisition_preregistration.v6",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "predecessor_v159_campaign_id": PREDECESSOR_V159_CAMPAIGN_ID,
        "planning_horizon": PLANNING_HORIZON,
        "decisions_per_episode": DECISIONS_PER_EPISODE,
        "preregistered_initial_boards": [
            list(board) for board in PREREGISTERED_INITIAL_BOARDS
        ],
        "preregistered_episode_seeds": list(PREREGISTERED_EPISODE_SEEDS),
        "episode_count": len(PREREGISTERED_INITIAL_BOARDS),
        "decision_count": len(PREREGISTERED_INITIAL_BOARDS)
        * DECISIONS_PER_EPISODE,
        "global_prefix_checkpoints_per_cardinality": list(
            GLOBAL_PREFIX_CHECKPOINTS
        ),
        "targeted_additional_checkpoints": list(
            TARGETED_ADDITIONAL_CHECKPOINTS
        ),
        "maximum_unique_offline_transition_observation_count": (
            MAXIMUM_UNIQUE_OFFLINE_OBSERVATIONS
        ),
        "frontier_conditioned_arm": {
            "initial_global_checkpoint_per_cardinality": 8,
            "failed_certificate_frontier_definition": (
                "PAIRWISE_CANDIDATE_CHALLENGER_EMPTY_CARDINALITY_AND_"
                "SORTED_ORDINAL_DIFFERENCE_SUPPORT"
            ),
            "targeted_observation_selection": (
                "ONLY_REGISTERED_RAW_ROWS_RELEVANT_TO_FAILED_PAIRWISE_FRONTIER"
            ),
            "unaffected_rows_reused_without_resampling": True,
            "all_acquired_rows_charged_once_by_unique_raw_record_identity": True,
            "certificate_rebuilt_after_each_registered_targeted_checkpoint": True,
            "hard_cap_route": "COLD_GROUND_FALLBACK",
        },
        "matched_global_prefix_control": {
            "policy": "V159_GLOBAL_PER_CARDINALITY_ESCALATION",
            "same_hard_cap_and_fallback": True,
            "same_support_grammar_and_confidence_family": True,
        },
        "matched_cold_direct_control": {
            "one_fresh_exact_model_per_decision": True,
            "evaluation_only_unless_selected_fallback": True,
            "no_acquisition_or_route_authority": True,
        },
        "required_positive_conditions": [
            "ALL_SELECTED_ACTIONS_EXACT_VALUE_AND_LOSS_EQUIVALENT_TO_COLD_DIRECT",
            "FRONTIER_CONDITIONED_UNIQUE_OFFLINE_OBSERVATIONS_LT_GLOBAL_CONTROL",
        ],
        "if_sample_reduction_fails": (
            "REPORT_PREREGISTERED_NEGATIVE_RESULT_AND_PRESERVE_FALLBACK"
        ),
        "outcome_fields_present": False,
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
        "frontier_acquisition_preregistration_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_PREREGISTRATION_V6_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048FrontierAcquisitionPreregistrationV6:
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
            if key != "frontier_acquisition_preregistration_id"
        }
        if (
            document.get("frontier_acquisition_preregistration_id")
            != self.preregistration_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_PREREGISTRATION_V6_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("frontier preregistration root is not an object")
        return document


def freeze_standard_2048_frontier_acquisition_preregistration_v6(
) -> Standard2048FrontierAcquisitionPreregistrationV6:
    document = _document()
    return Standard2048FrontierAcquisitionPreregistrationV6(
        _ISSUER,
        canonical_json_bytes(document),
        document["frontier_acquisition_preregistration_id"],
    )


def verify_standard_2048_frontier_acquisition_preregistration_v6(
    value: Standard2048FrontierAcquisitionPreregistrationV6,
) -> Standard2048FrontierAcquisitionPreregistrationV6:
    if type(value) is not Standard2048FrontierAcquisitionPreregistrationV6:
        _fail("verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("preregistration differs from frozen semantics")
    return value


__all__ = (
    "ConstructionK7Standard2048FrontierAcquisitionPreregistrationV6Error",
    "DECISIONS_PER_EPISODE",
    "FUTURE_DOMAINS",
    "GLOBAL_PREFIX_CHECKPOINTS",
    "MAXIMUM_UNIQUE_OFFLINE_OBSERVATIONS",
    "PLANNING_HORIZON",
    "PREREGISTERED_EPISODE_SEEDS",
    "PREREGISTERED_INITIAL_BOARDS",
    "PROFILE_KEY",
    "Standard2048FrontierAcquisitionPreregistrationV6",
    "TARGETED_ADDITIONAL_CHECKPOINTS",
    "freeze_standard_2048_frontier_acquisition_preregistration_v6",
    "verify_standard_2048_frontier_acquisition_preregistration_v6",
)
