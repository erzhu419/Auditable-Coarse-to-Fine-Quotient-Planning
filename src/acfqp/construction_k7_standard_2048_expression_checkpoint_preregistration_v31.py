"""Outcome-free registration of the sixth exact 2048 checkpoint segment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V31_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V31_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V31_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V31_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V31_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "31.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.189"
PROFILE_KEY = "construction_k7_standard_2048_expression_exact_checkpoint_v31"
PREREGISTRATION_ID = "025effad49137ce04afef557494fa37f3d8b83bb5c62f35283fd5bba19c29151"
EXPECTED_CANONICAL_BYTE_COUNT = 3793
EXPECTED_CANONICAL_SHA256 = "9e089227d743e88bec2ce77dd23e142ef8a226a3c33d9c3cc8eb3dd9ea62fd91"
V30_PREREGISTRATION_ID = "a047f3e539cc669f4de0be9d8d63f6bf32959877d4745f8cea3aa61ea0cb9861"
V30_CAMPAIGN_ID = "5371b59f0d65097c7ceb2135d0e14671db42a156531a03cba8d21e95ec7485a7"
V30_VERIFICATION_ID = "1093868c130d68a77ad00d61ad0aa073455516449dc296701942591b3930a210"
WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
PLANNING_HORIZON = 3
SOURCE_DECISION_COUNT = 320
SEGMENT_DECISION_LIMIT = 256
GLOBAL_DECISION_START = 320
GLOBAL_DECISION_STOP_EXCLUSIVE = 576
LOCAL_COLD_CHECKPOINTS = (0, 127, 255)
GLOBAL_COLD_CHECKPOINTS = (320, 447, 575)
CHECKPOINT_EPISODE_IDS = (
    "60e1511ce97802cde21dbc7a628362feae958e27a5ed53883b2402ef7ab4785e",
    "d0c742044ffecb69c06a2baff39513a3e8e791f9e123867a20de49044391453a",
    "55d70342127fa7dfc85227b0357ab526ee779e484596b5f9ee9da3eebd93a854",
    "768097790de11460f5401b7c9662aa78492a48bfcfe025b83b26821bcba2eaae",
)
CHECKPOINT_BOARDS = (
    (0, 0, 1, 0, 0, 0, 7, 0, 0, 2, 9, 3, 0, 2, 3, 6),
    (0, 0, 0, 1, 0, 0, 4, 0, 1, 2, 9, 3, 2, 7, 4, 3),
    (2, 0, 0, 0, 3, 5, 0, 2, 9, 7, 1, 0, 4, 4, 2, 0),
    (1, 7, 2, 1, 1, 5, 0, 0, 5, 0, 0, 0, 9, 0, 0, 0),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V31_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V31_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V31_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V31_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V31_DOMAIN,
}


class ConstructionK7Standard2048ExpressionCheckpointPreregistrationV31Error(
    ValueError
):
    """The source checkpoint, exact segment, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionCheckpointPreregistrationV31Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_checkpoint_preregistration.v31",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v30_preregistration_id": V30_PREREGISTRATION_ID,
            "v30_checkpoint_campaign_id": V30_CAMPAIGN_ID,
            "v30_checkpoint_verification_id": V30_VERIFICATION_ID,
            "expression_world_model_id": WORLD_MODEL_ID,
            "all_source_checkpoints_have_320_certified_decisions": True,
        },
        "checkpoint_workload": {
            "source_episode_ids": list(CHECKPOINT_EPISODE_IDS),
            "checkpoint_boards": [list(board) for board in CHECKPOINT_BOARDS],
            "checkpoint_status": ["ACTIVE"] * len(CHECKPOINT_BOARDS),
            "episode_seeds": list(v23.EPISODE_SEEDS),
            "episode_count": len(CHECKPOINT_BOARDS),
            "source_decision_count": SOURCE_DECISION_COUNT,
            "global_decision_start_inclusive": GLOBAL_DECISION_START,
            "global_decision_stop_exclusive": GLOBAL_DECISION_STOP_EXCLUSIVE,
            "segment_decision_limit": SEGMENT_DECISION_LIMIT,
            "planning_horizon": PLANNING_HORIZON,
            "local_cold_checkpoint_indices": list(LOCAL_COLD_CHECKPOINTS),
            "global_cold_checkpoint_indices": list(GLOBAL_COLD_CHECKPOINTS),
            "early_terminal_closure_allowed": True,
        },
        "exact_checkpoint_protocol": {
            "one_empty_exact_subproof_cache_at_segment_start": True,
            "cache_reused_within_segment": True,
            "cache_not_required_to_cross_checkpoint_boundary": True,
            "cache_reset_changes_exact_values_or_action_selection": False,
            "fraction_or_precision_approximation_allowed": False,
            "certificate_frozen_before_target_transition": True,
            "target_seed_decision_index_uses_global_offset": True,
            "execution_transition_may_modify_world_model": False,
        },
        "sample_tax_contract": {
            "inherited_target_probability_label_count": 4,
            "additional_model_acquisition_label_budget": 0,
            "strict_no_prior_context_label_count": 8,
            "sample_count_and_planning_compute_remain_separate_axes": True,
            "positive_result_requires_all_certificates_and_transitions_to_replay": True,
        },
        "required_positive_conditions": [
            "ALL_SOURCE_CHECKPOINT_IDENTITIES_MATCH_V30",
            "ALL_SEGMENT_PLANS_USE_THE_FROZEN_EXPRESSION_WORLD_MODEL",
            "ZERO_ADDITIONAL_TARGET_PROBABILITY_LABELS",
            "ALL_REGISTERED_COLD_CHECKPOINTS_MATCH_EXACT_GROUND",
            "ALL_SEEDED_TRANSITIONS_USE_GLOBAL_DECISION_INDICES",
        ],
        "outcome_fields_present": False,
        "checkpoint_execution_performed": False,
        "terminal_or_tile_2048_reached": False,
        "full_standard_2048_game_claimed": False,
        "broad_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "expression_checkpoint_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionCheckpointPreregistrationV31:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("checkpoint preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("checkpoint preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "expression_checkpoint_preregistration_id"
        }
        if (
            document.get("expression_checkpoint_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("checkpoint preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("checkpoint preregistration is not an object")
        return document


def freeze_standard_2048_expression_checkpoint_preregistration_v31(
) -> Standard2048ExpressionCheckpointPreregistrationV31:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["expression_checkpoint_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen checkpoint preregistration changed")
    return Standard2048ExpressionCheckpointPreregistrationV31(
        _ISSUER, raw, identity
    )


def verify_standard_2048_expression_checkpoint_preregistration_v31(
    value: Standard2048ExpressionCheckpointPreregistrationV31,
) -> Standard2048ExpressionCheckpointPreregistrationV31:
    if type(value) is not Standard2048ExpressionCheckpointPreregistrationV31:
        _fail("checkpoint preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("checkpoint preregistration semantics changed")
    return value


__all__ = (
    "CHECKPOINT_BOARDS",
    "CHECKPOINT_EPISODE_IDS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "PREREGISTRATION_ID",
    "Standard2048ExpressionCheckpointPreregistrationV31",
    "freeze_standard_2048_expression_checkpoint_preregistration_v31",
    "verify_standard_2048_expression_checkpoint_preregistration_v31",
)
