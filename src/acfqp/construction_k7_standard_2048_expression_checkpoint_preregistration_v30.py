"""Outcome-free registration of the fifth exact 2048 checkpoint segment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V30_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V30_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V30_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V30_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V30_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "30.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.188"
PROFILE_KEY = "construction_k7_standard_2048_expression_exact_checkpoint_v30"
PREREGISTRATION_ID = "a047f3e539cc669f4de0be9d8d63f6bf32959877d4745f8cea3aa61ea0cb9861"
EXPECTED_CANONICAL_BYTE_COUNT = 3792
EXPECTED_CANONICAL_SHA256 = "de3f775ab81c37bb064fcdafef7cd54bc151e879f64627019226b8298dd36c43"
V29_PREREGISTRATION_ID = "03e0141e47448310d5aac0ffa7b37d31856f362784df239039d4a72bde7dff9f"
V29_CAMPAIGN_ID = "25c89c42d40ee7753911f918387deaff4200f09424b513ecd646bdc307b9ebdc"
V29_VERIFICATION_ID = "2ccd55b10b1980551b1ea94223f8e74da8d7a889210a95e2cb00ccb48d7582f5"
WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
PLANNING_HORIZON = 3
SOURCE_DECISION_COUNT = 192
SEGMENT_DECISION_LIMIT = 128
GLOBAL_DECISION_START = 192
GLOBAL_DECISION_STOP_EXCLUSIVE = 320
LOCAL_COLD_CHECKPOINTS = (0, 63, 127)
GLOBAL_COLD_CHECKPOINTS = (192, 255, 319)
CHECKPOINT_EPISODE_IDS = (
    "32bf9be9245059c94526eab9d89635eeee12baaf5b2aec464c0d1c1a221bf333",
    "81f1a81444a467cf20b973969c101bae7d903c7e5e4903a1dcd495bf4ee579c2",
    "b31f6e30ca8238625ec26584e03473e22f3855503ff5afb20657103ad4901734",
    "4bd2511cec43c6b613bc4cf56db76dbb3ad1ef6c62c974eea70b2ab35c67b0c1",
)
CHECKPOINT_BOARDS = (
    (3, 3, 1, 0, 8, 7, 0, 1, 5, 0, 0, 0, 2, 0, 0, 0),
    (1, 8, 3, 1, 0, 1, 5, 3, 0, 1, 5, 6, 0, 1, 3, 1),
    (1, 3, 0, 1, 5, 2, 0, 0, 7, 2, 0, 0, 8, 0, 0, 0),
    (2, 3, 0, 0, 4, 7, 0, 0, 8, 2, 0, 1, 2, 1, 0, 0),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V30_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V30_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V30_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V30_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V30_DOMAIN,
}


class ConstructionK7Standard2048ExpressionCheckpointPreregistrationV30Error(
    ValueError
):
    """The source checkpoint, exact segment, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionCheckpointPreregistrationV30Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_checkpoint_preregistration.v30",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v29_preregistration_id": V29_PREREGISTRATION_ID,
            "v29_checkpoint_campaign_id": V29_CAMPAIGN_ID,
            "v29_checkpoint_verification_id": V29_VERIFICATION_ID,
            "expression_world_model_id": WORLD_MODEL_ID,
            "all_source_checkpoints_have_192_certified_decisions": True,
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
            "ALL_SOURCE_CHECKPOINT_IDENTITIES_MATCH_V29",
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
class Standard2048ExpressionCheckpointPreregistrationV30:
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


def freeze_standard_2048_expression_checkpoint_preregistration_v30(
) -> Standard2048ExpressionCheckpointPreregistrationV30:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["expression_checkpoint_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen checkpoint preregistration changed")
    return Standard2048ExpressionCheckpointPreregistrationV30(
        _ISSUER, raw, identity
    )


def verify_standard_2048_expression_checkpoint_preregistration_v30(
    value: Standard2048ExpressionCheckpointPreregistrationV30,
) -> Standard2048ExpressionCheckpointPreregistrationV30:
    if type(value) is not Standard2048ExpressionCheckpointPreregistrationV30:
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
    "Standard2048ExpressionCheckpointPreregistrationV30",
    "freeze_standard_2048_expression_checkpoint_preregistration_v30",
    "verify_standard_2048_expression_checkpoint_preregistration_v30",
)
