"""Outcome-free preregistration for long real-start 2048 reuse and no-transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_LONG_CAMPAIGN_V11_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LONG_CERTIFICATE_V11_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LONG_DYNAMICS_IDENTITY_V11_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LONG_EPISODE_V11_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LONG_NO_TRANSFER_V11_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LONG_OPERATOR_BINDING_V11_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LONG_PREREGISTRATION_V11_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LONG_VERIFICATION_V11_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "11.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.168"
PROFILE_KEY = "construction_k7_standard_2048_long_episode_reuse_v11"
PREREGISTRATION_ID = (
    "e5b54b64a644c94c0d886ad9cd43f2a538e6af7000cc2ee5b0016228cd139328"
)
V167_META_ROUTE_CAMPAIGN_ID = (
    "6838c6ed5764d1f514247eee98f2d6d7a3992e3a29c0a4ac85ba8182b0afdcd0"
)
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 32
OFFLINE_OBSERVATION_COUNT = 192

PREREGISTERED_INITIAL_BOARDS = (
    (1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)
PREREGISTERED_EPISODE_SEEDS = tuple(
    f"standard-2048-v168-long-real-start-{index:02d}-20260813"
    for index in range(len(PREREGISTERED_INITIAL_BOARDS))
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_LONG_PREREGISTRATION_V11_DOMAIN,
    "dynamics_identity": (
        CONSTRUCTION_K7_STANDARD_2048_LONG_DYNAMICS_IDENTITY_V11_DOMAIN
    ),
    "operator_binding": (
        CONSTRUCTION_K7_STANDARD_2048_LONG_OPERATOR_BINDING_V11_DOMAIN
    ),
    "certificate": CONSTRUCTION_K7_STANDARD_2048_LONG_CERTIFICATE_V11_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_LONG_EPISODE_V11_DOMAIN,
    "no_transfer": CONSTRUCTION_K7_STANDARD_2048_LONG_NO_TRANSFER_V11_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_LONG_CAMPAIGN_V11_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_LONG_VERIFICATION_V11_DOMAIN,
}


class ConstructionK7Standard2048LongEpisodePreregistrationV11Error(ValueError):
    """The workload, dynamics identities, route, or result boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048LongEpisodePreregistrationV11Error(message)


def _dynamics_identity_document(kind: str) -> dict[str, Any]:
    if kind == "STANDARD_UNIFORM":
        semantics = {
            "board_shape": [4, 4],
            "transition_order": "DETERMINISTIC_SWIPE_THEN_ONE_SPAWN",
            "spawn_position": "UNIFORM_OVER_ALL_POST_SWIPE_EMPTY_CELLS",
            "spawn_rank_support": [1, 2],
            "rank_law": "ONE_SHARED_BERNOULLI_PARAMETER",
            "registered_family_member": True,
        }
    elif kind == "OOD_FIRST_EMPTY_BIASED":
        semantics = {
            "board_shape": [4, 4],
            "transition_order": "DETERMINISTIC_SWIPE_THEN_ONE_SPAWN",
            "spawn_position": (
                "FIRST_SORTED_POST_SWIPE_EMPTY_CELL_WITH_PROBABILITY_ONE_HALF_"
                "REMAINDER_UNIFORM"
            ),
            "spawn_rank_support": [1, 2],
            "rank_law": "ONE_SHARED_BERNOULLI_PARAMETER",
            "registered_family_member": False,
        }
    else:
        _fail("unknown dynamics identity kind")
    payload = {
        "schema": "acfqp.standard_2048_long_dynamics_identity.v11",
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "semantics": semantics,
    }
    return {
        **payload,
        "dynamics_identity_id": content_id(
            FUTURE_DOMAINS["dynamics_identity"], payload
        ),
    }


def _document() -> dict[str, Any]:
    accepted = _dynamics_identity_document("STANDARD_UNIFORM")
    ood = _dynamics_identity_document("OOD_FIRST_EMPTY_BIASED")
    payload = {
        "schema": "acfqp.standard_2048_long_episode_preregistration.v11",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "v167_meta_route_campaign_id": V167_META_ROUTE_CAMPAIGN_ID,
        "v167_is_frozen_predecessor_evidence_only": True,
        "fresh_target_identities_required": True,
        "planning_horizon": PLANNING_HORIZON,
        "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
        "early_terminal_closure_allowed": True,
        "preregistered_initial_boards": [
            list(board) for board in PREREGISTERED_INITIAL_BOARDS
        ],
        "initial_board_contract": {
            "exactly_two_nonzero_tiles": True,
            "tile_ranks_limited_to_initial_spawn_support": [1, 2],
            "boards_are_fresh_and_d4_disjoint_from_development": True,
        },
        "preregistered_episode_seeds": list(PREREGISTERED_EPISODE_SEEDS),
        "episode_count": len(PREREGISTERED_INITIAL_BOARDS),
        "maximum_decision_count": (
            len(PREREGISTERED_INITIAL_BOARDS) * MAXIMUM_DECISIONS_PER_EPISODE
        ),
        "accepted_dynamics_identity": accepted,
        "ood_no_transfer_identity": ood,
        "operator_reuse_policy": {
            "exact_accepted_dynamics_identity_required": True,
            "operator_binding_frozen_before_target_execution": True,
            "offline_observation_count_charged_once": OFFLINE_OBSERVATION_COUNT,
            "additional_model_acquisition_observation_budget": 0,
            "factored_state_action_rows_serialized_or_persisted": False,
            "identity_mismatch_action": "NO_TRANSFER_BEFORE_OPERATOR_ACCESS",
            "identity_match_not_sufficient_for_certificate": True,
        },
        "route_protocol": {
            "abstract_route_requires_strict_root_interval_dominance": True,
            "certificate_failure_route": "COLD_EXACT_DIRECT_GROUND_FALLBACK",
            "ground_transition_access_before_certificate_freeze": False,
            "matched_cold_direct_has_no_route_authority": True,
            "all_selected_actions_must_be_exact_value_and_loss_equivalent": True,
        },
        "required_positive_conditions": [
            "STANDARD_IDENTITY_BINDS_OPERATOR_BEFORE_TARGET_EXECUTION",
            "OOD_IDENTITY_REJECTED_BEFORE_OPERATOR_OR_TARGET_ACCESS",
            "OFFLINE_OBSERVATION_COUNT_EQUALS_192_WITH_ZERO_ADDITIONAL",
            "ALL_ABSTRACT_ROUTES_HAVE_STRICT_CERTIFICATES",
            "ALL_SELECTED_ACTIONS_EXACT_VALUE_AND_LOSS_EQUIVALENT",
            "FALLBACK_ONLY_AFTER_CERTIFICATE_FAILURE",
            "OPERATIONAL_SERIALIZED_AND_PERSISTENT_STATE_ACTION_ROWS_EQUAL_ZERO",
        ],
        "sample_tax_axes": {
            "offline_observations": "SEPARATE_INTEGER_COUNT",
            "factored_successor_evaluations": "SEPARATE_INTEGER_COUNT",
            "ground_fallback_rows": "SEPARATE_INTEGER_COUNT",
            "ground_fallback_outcomes": "SEPARATE_INTEGER_COUNT",
            "scalar_combination_forbidden": True,
        },
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "long_episode_implementation_present": False,
        "ood_target_execution_performed": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "ood_generalization_claimed": False,
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
        "long_episode_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048LongEpisodePreregistrationV11:
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
            if key != "long_episode_preregistration_id"
        }
        if (
            document.get("long_episode_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("long-episode preregistration is not an object")
        return document


def freeze_standard_2048_long_episode_preregistration_v11(
) -> Standard2048LongEpisodePreregistrationV11:
    document = _document()
    if document["long_episode_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen preregistration identity changed")
    return Standard2048LongEpisodePreregistrationV11(
        _ISSUER,
        canonical_json_bytes(document),
        document["long_episode_preregistration_id"],
    )


def verify_standard_2048_long_episode_preregistration_v11(
    value: Standard2048LongEpisodePreregistrationV11,
) -> Standard2048LongEpisodePreregistrationV11:
    if type(value) is not Standard2048LongEpisodePreregistrationV11:
        _fail("verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("preregistration differs from frozen semantics")
    return value


__all__ = (
    "ConstructionK7Standard2048LongEpisodePreregistrationV11Error",
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "OFFLINE_OBSERVATION_COUNT",
    "PLANNING_HORIZON",
    "PREREGISTERED_EPISODE_SEEDS",
    "PREREGISTERED_INITIAL_BOARDS",
    "PREREGISTRATION_ID",
    "Standard2048LongEpisodePreregistrationV11",
    "freeze_standard_2048_long_episode_preregistration_v11",
    "verify_standard_2048_long_episode_preregistration_v11",
)
