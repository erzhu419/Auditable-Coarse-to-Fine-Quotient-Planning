"""Outcome-free registration of the seventh exact 2048 checkpoint segment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V32_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V32_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V32_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V32_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V32_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "32.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.190"
PROFILE_KEY = "construction_k7_standard_2048_expression_exact_checkpoint_v32"
PREREGISTRATION_ID = "955ffbb97109dcb3ccb65cc6027ec9e5b70564bf40ed0d30a5527ebfa0220254"
EXPECTED_CANONICAL_BYTE_COUNT = 3932
EXPECTED_CANONICAL_SHA256 = "cece2715c1efa42be5c75956c812703e9657af45f99c4291e59ed2af311c7dcc"
V31_PREREGISTRATION_ID = "025effad49137ce04afef557494fa37f3d8b83bb5c62f35283fd5bba19c29151"
V31_CAMPAIGN_ID = "0496268bc764f091dee9db33a0542066df217e23f77da11511af1211f90ba4f1"
V31_VERIFICATION_ID = "48c9fcf95ed724f3e8297bfb109e466faab6dd19124cabf95d77f393672ed865"
WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
PLANNING_HORIZON = 3
SOURCE_DECISION_COUNTS = (576, 490, 576, 576)
SEGMENT_DECISION_LIMIT = 256
GLOBAL_DECISION_STARTS = SOURCE_DECISION_COUNTS
GLOBAL_DECISION_STOPS_EXCLUSIVE = tuple(start + SEGMENT_DECISION_LIMIT for start in GLOBAL_DECISION_STARTS)
LOCAL_COLD_CHECKPOINTS = (0, 127, 255)
GLOBAL_COLD_CHECKPOINTS_BY_EPISODE = tuple(
    tuple(start + index for index in LOCAL_COLD_CHECKPOINTS)
    for start in GLOBAL_DECISION_STARTS
)
CHECKPOINT_EPISODE_IDS = (
    "90f95d25f9338943767500918f0d9f1962f59833d755259fed379a2dfac3cd29",
    "c6ac2ca8788f903b7ffea61bc198b510c98aab750c15f7bf7a3073e43fba3f3a",
    "25af092405e4345f630520bd8565a72bf4cf19e65efb6a32cded6e908f4c7f26",
    "07c3b032d9d414273c7d58795719d4a82dbcf51ec662f4a386d665173372f6b2",
)
CHECKPOINT_STATUSES = ("ACTIVE", "LOST", "ACTIVE", "ACTIVE")
CHECKPOINT_BOARDS = (
    (0, 1, 0, 0, 2, 2, 0, 0, 10, 6, 6, 1, 1, 4, 7, 1),
    (5, 3, 2, 1, 1, 8, 9, 3, 3, 6, 4, 5, 2, 7, 3, 1),
    (0, 0, 0, 0, 1, 0, 1, 0, 3, 3, 10, 0, 3, 8, 1, 2),
    (1, 4, 4, 4, 1, 2, 6, 7, 0, 0, 5, 10, 0, 0, 1, 3),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V32_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V32_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V32_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V32_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V32_DOMAIN,
}


class ConstructionK7Standard2048ExpressionCheckpointPreregistrationV32Error(
    ValueError
):
    """The source checkpoint, exact segment, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionCheckpointPreregistrationV32Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_checkpoint_preregistration.v32",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v31_preregistration_id": V31_PREREGISTRATION_ID,
            "v31_checkpoint_campaign_id": V31_CAMPAIGN_ID,
            "v31_checkpoint_verification_id": V31_VERIFICATION_ID,
            "expression_world_model_id": WORLD_MODEL_ID,
            "source_checkpoint_decision_counts_are_identity_bound": True,
        },
        "checkpoint_workload": {
            "source_episode_ids": list(CHECKPOINT_EPISODE_IDS),
            "checkpoint_boards": [list(board) for board in CHECKPOINT_BOARDS],
            "checkpoint_status": list(CHECKPOINT_STATUSES),
            "episode_seeds": list(v23.EPISODE_SEEDS),
            "episode_count": len(CHECKPOINT_BOARDS),
            "source_decision_counts": list(SOURCE_DECISION_COUNTS),
            "source_terminal_occurrence_count": 1,
            "global_decision_starts_inclusive": list(GLOBAL_DECISION_STARTS),
            "global_decision_stops_exclusive": list(GLOBAL_DECISION_STOPS_EXCLUSIVE),
            "segment_decision_limit": SEGMENT_DECISION_LIMIT,
            "planning_horizon": PLANNING_HORIZON,
            "local_cold_checkpoint_indices": list(LOCAL_COLD_CHECKPOINTS),
            "global_cold_checkpoint_indices_by_episode": [
                list(indices) for indices in GLOBAL_COLD_CHECKPOINTS_BY_EPISODE
            ],
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
            "ALL_SOURCE_CHECKPOINT_IDENTITIES_MATCH_V31",
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
class Standard2048ExpressionCheckpointPreregistrationV32:
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


def freeze_standard_2048_expression_checkpoint_preregistration_v32(
) -> Standard2048ExpressionCheckpointPreregistrationV32:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["expression_checkpoint_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen checkpoint preregistration changed")
    return Standard2048ExpressionCheckpointPreregistrationV32(
        _ISSUER, raw, identity
    )


def verify_standard_2048_expression_checkpoint_preregistration_v32(
    value: Standard2048ExpressionCheckpointPreregistrationV32,
) -> Standard2048ExpressionCheckpointPreregistrationV32:
    if type(value) is not Standard2048ExpressionCheckpointPreregistrationV32:
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
    "Standard2048ExpressionCheckpointPreregistrationV32",
    "freeze_standard_2048_expression_checkpoint_preregistration_v32",
    "verify_standard_2048_expression_checkpoint_preregistration_v32",
)
