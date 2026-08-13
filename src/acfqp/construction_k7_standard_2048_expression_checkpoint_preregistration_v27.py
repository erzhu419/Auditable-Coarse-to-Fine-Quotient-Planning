"""Outcome-free registration of the second exact 2048 checkpoint segment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V27_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V27_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V27_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V27_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V27_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "27.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.185"
PROFILE_KEY = "construction_k7_standard_2048_expression_exact_checkpoint_v27"
PREREGISTRATION_ID = "1e4062516cd3c1af1ca6e4f959cd3352d9e305f56d6d4f0d836a09141e1c3419"
EXPECTED_CANONICAL_BYTE_COUNT = 3783
EXPECTED_CANONICAL_SHA256 = "73aa571d6018bf18334c44db37ce8d2e90cf5d3742c78b2c7a510e7be631b30b"
V26_PREREGISTRATION_ID = "7902930c25528fce6abb00576166cb1281bbc802868bfb60762abfc128d7f32e"
V26_CAMPAIGN_ID = "8e0ac13bbb7c242bd9b2f6aa1255856d1d72d92af67b94f8b806ff6f34199dd6"
V26_VERIFICATION_ID = "6637f9567e4b097e33520eae51a34ce47ab2fed4d470a50cfa13278b2e41debb"
WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
PLANNING_HORIZON = 3
SOURCE_DECISION_COUNT = 64
SEGMENT_DECISION_LIMIT = 32
GLOBAL_DECISION_START = 64
GLOBAL_DECISION_STOP_EXCLUSIVE = 96
LOCAL_COLD_CHECKPOINTS = (0, 15, 31)
GLOBAL_COLD_CHECKPOINTS = (64, 79, 95)
CHECKPOINT_EPISODE_IDS = (
    "a47351c743c5fec7254c72f2a1556c9758de81778e69db8359d37036c50d4092",
    "db5469d916b32c19f2b56a9c2d75e4566236962a825512c4bd84865a9e8a8b1d",
    "ca987bad2a783420016f81ee7a1a4988bd95575f81fb955f49b2556b5fec9d46",
    "7d772f05ba3bbd31478a4de03b4fec84681a08d64e8097a8fcba77f08253907b",
)
CHECKPOINT_BOARDS = (
    (1, 0, 1, 2, 0, 0, 3, 6, 0, 0, 0, 6, 0, 0, 0, 2),
    (0, 0, 0, 0, 0, 3, 5, 1, 1, 1, 6, 3, 3, 2, 4, 1),
    (0, 6, 2, 1, 0, 1, 5, 2, 0, 0, 5, 1, 0, 0, 1, 2),
    (0, 5, 5, 1, 0, 2, 6, 3, 0, 1, 2, 2, 0, 0, 0, 0),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V27_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V27_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V27_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V27_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V27_DOMAIN,
}


class ConstructionK7Standard2048ExpressionCheckpointPreregistrationV27Error(
    ValueError
):
    """The source checkpoint, exact segment, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionCheckpointPreregistrationV27Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_checkpoint_preregistration.v27",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v26_preregistration_id": V26_PREREGISTRATION_ID,
            "v26_checkpoint_campaign_id": V26_CAMPAIGN_ID,
            "v26_checkpoint_verification_id": V26_VERIFICATION_ID,
            "expression_world_model_id": WORLD_MODEL_ID,
            "all_source_checkpoints_have_64_certified_decisions": True,
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
            "ALL_SOURCE_CHECKPOINT_IDENTITIES_MATCH_V26",
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
class Standard2048ExpressionCheckpointPreregistrationV27:
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


def freeze_standard_2048_expression_checkpoint_preregistration_v27(
) -> Standard2048ExpressionCheckpointPreregistrationV27:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["expression_checkpoint_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen checkpoint preregistration changed")
    return Standard2048ExpressionCheckpointPreregistrationV27(
        _ISSUER, raw, identity
    )


def verify_standard_2048_expression_checkpoint_preregistration_v27(
    value: Standard2048ExpressionCheckpointPreregistrationV27,
) -> Standard2048ExpressionCheckpointPreregistrationV27:
    if type(value) is not Standard2048ExpressionCheckpointPreregistrationV27:
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
    "Standard2048ExpressionCheckpointPreregistrationV27",
    "freeze_standard_2048_expression_checkpoint_preregistration_v27",
    "verify_standard_2048_expression_checkpoint_preregistration_v27",
)
