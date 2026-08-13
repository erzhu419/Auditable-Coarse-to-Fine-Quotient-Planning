"""Outcome-free registration of the next exact 2048 checkpoint segment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V26_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V26_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V26_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V26_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V26_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "26.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.184"
PROFILE_KEY = "construction_k7_standard_2048_expression_exact_checkpoint_v26"
PREREGISTRATION_ID = "7902930c25528fce6abb00576166cb1281bbc802868bfb60762abfc128d7f32e"
EXPECTED_CANONICAL_BYTE_COUNT = 3880
EXPECTED_CANONICAL_SHA256 = "97c941bd171b05d84feae743b281f215c4e3215d50b45888b01fced761fa1980"
V24_PREREGISTRATION_ID = "122fe5ae5121bc55bebafbac1208810c29b9486924985457f6636de2f9e4979d"
V24_CAMPAIGN_ID = "3eba16cb6db6d0797991acbde6103d423741668730313385e404949b5907ab72"
V24_ACCOUNTING_VERIFICATION_ID = "79749d6a1d689ee4cb8740d2b20393d11403d29471f9a218e4a4a5b36720aca7"
V25_SEMANTIC_VERIFICATION_ID = "0c9957d0d5a7832ef0a9e2f9cfe0bb2ab1e2329b990f89c5d12e2498957fe258"
WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
PLANNING_HORIZON = 3
SOURCE_DECISION_COUNT = 32
SEGMENT_DECISION_LIMIT = 32
GLOBAL_DECISION_START = 32
GLOBAL_DECISION_STOP_EXCLUSIVE = 64
LOCAL_COLD_CHECKPOINTS = (0, 15, 31)
GLOBAL_COLD_CHECKPOINTS = (32, 47, 63)
CHECKPOINT_EPISODE_IDS = (
    "c599ad7be3ef42d38c77097b1b320013d934453d0dc46857679542a1b98154a0",
    "282fcfe1dfc726552f3716dfba4b9495e3d87cd960895880cf967c8bdcbbda54",
    "aa3938abac41674be008ae8c0b81db41ac8a38a4e8db47808ae6e3d6836c50ea",
    "f9c68185d80edc4c78d90acd80d547aefe5458855666833c79d21223a4e4b59b",
)
CHECKPOINT_BOARDS = (
    (4, 4, 5, 3, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0),
    (5, 1, 0, 1, 5, 2, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0),
    (1, 1, 1, 6, 1, 0, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 5, 5, 0, 2, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V26_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V26_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V26_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V26_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V26_DOMAIN,
}


class ConstructionK7Standard2048ExpressionCheckpointPreregistrationV26Error(
    ValueError
):
    """The source checkpoint, exact segment, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionCheckpointPreregistrationV26Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_checkpoint_preregistration.v26",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v24_preregistration_id": V24_PREREGISTRATION_ID,
            "v24_accounted_campaign_id": V24_CAMPAIGN_ID,
            "v24_accounting_verification_id": V24_ACCOUNTING_VERIFICATION_ID,
            "v25_semantic_verification_id": V25_SEMANTIC_VERIFICATION_ID,
            "expression_world_model_id": WORLD_MODEL_ID,
            "all_source_checkpoints_have_32_certified_decisions": True,
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
            "ALL_SOURCE_CHECKPOINT_IDENTITIES_MATCH_V24",
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
class Standard2048ExpressionCheckpointPreregistrationV26:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("checkpoint preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
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


def freeze_standard_2048_expression_checkpoint_preregistration_v26(
) -> Standard2048ExpressionCheckpointPreregistrationV26:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["expression_checkpoint_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen checkpoint preregistration changed")
    return Standard2048ExpressionCheckpointPreregistrationV26(
        _ISSUER, raw, identity
    )


def verify_standard_2048_expression_checkpoint_preregistration_v26(
    value: Standard2048ExpressionCheckpointPreregistrationV26,
) -> Standard2048ExpressionCheckpointPreregistrationV26:
    if type(value) is not Standard2048ExpressionCheckpointPreregistrationV26:
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
    "Standard2048ExpressionCheckpointPreregistrationV26",
    "freeze_standard_2048_expression_checkpoint_preregistration_v26",
    "verify_standard_2048_expression_checkpoint_preregistration_v26",
)
