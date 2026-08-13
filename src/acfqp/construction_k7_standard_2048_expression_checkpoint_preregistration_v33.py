"""Outcome-free registration of the eighth exact 2048 checkpoint segment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V33_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V33_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V33_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V33_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V33_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "33.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.191"
PROFILE_KEY = "construction_k7_standard_2048_expression_exact_checkpoint_v33"
PREREGISTRATION_ID = "00c9afa984008a065e31b955b3ff8802cb94b5c5e2998e78ced9827a9b83c66b"
EXPECTED_CANONICAL_BYTE_COUNT = 3936
EXPECTED_CANONICAL_SHA256 = "d08cebf19fbbc539f2e8ebfb5ffca3d4c00157cee0322960c80d49553bc6be75"
V32_PREREGISTRATION_ID = "955ffbb97109dcb3ccb65cc6027ec9e5b70564bf40ed0d30a5527ebfa0220254"
V32_CAMPAIGN_ID = "11a06b90547d352a077b91432daad7d134cf41e5b72d5dde9a66a8d3e130044d"
V32_VERIFICATION_ID = "0bf70e8d228f25fcb503b9b243e4b229b1deb1feefeb205836ab500ed2e88b16"
WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
PLANNING_HORIZON = 3
SOURCE_DECISION_COUNTS = (832, 490, 829, 832)
SEGMENT_DECISION_LIMIT = 256
GLOBAL_DECISION_STARTS = SOURCE_DECISION_COUNTS
GLOBAL_DECISION_STOPS_EXCLUSIVE = tuple(start + SEGMENT_DECISION_LIMIT for start in GLOBAL_DECISION_STARTS)
LOCAL_COLD_CHECKPOINTS = (0, 127, 255)
GLOBAL_COLD_CHECKPOINTS_BY_EPISODE = tuple(
    tuple(start + index for index in LOCAL_COLD_CHECKPOINTS)
    for start in GLOBAL_DECISION_STARTS
)
CHECKPOINT_EPISODE_IDS = (
    "8470c8564bd11d590a3ea523278fd6286b0429313f1b48e36fe4ee29b2311ed7",
    "6661f6bb5529c4ef00f3ec1aab0a39b6aa3279f5929d37e2e5b2e8620797d82b",
    "fff9e7ee089fce71ba63336991555b78e7cbddbbba4cee34abb6162d45c2db46",
    "a8f87061818e9feeaca0624e332439cb97071b301f4fff8bb03ec307cbd44f3e",
)
CHECKPOINT_STATUSES = ("ACTIVE", "LOST", "LOST", "ACTIVE")
CHECKPOINT_BOARDS = (
    (3, 3, 0, 0, 6, 10, 1, 1, 4, 8, 0, 0, 9, 0, 0, 0),
    (5, 3, 2, 1, 1, 8, 9, 3, 3, 6, 4, 5, 2, 7, 3, 1),
    (3, 5, 3, 4, 4, 7, 6, 9, 3, 5, 10, 2, 2, 4, 3, 1),
    (10, 4, 0, 0, 1, 6, 1, 1, 9, 1, 8, 0, 2, 0, 0, 0),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V33_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V33_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V33_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V33_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V33_DOMAIN,
}


class ConstructionK7Standard2048ExpressionCheckpointPreregistrationV33Error(
    ValueError
):
    """The source checkpoint, exact segment, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionCheckpointPreregistrationV33Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_checkpoint_preregistration.v33",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v32_preregistration_id": V32_PREREGISTRATION_ID,
            "v32_checkpoint_campaign_id": V32_CAMPAIGN_ID,
            "v32_checkpoint_verification_id": V32_VERIFICATION_ID,
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
            "source_terminal_occurrence_count": 2,
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
            "ALL_SOURCE_CHECKPOINT_IDENTITIES_MATCH_V32",
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
class Standard2048ExpressionCheckpointPreregistrationV33:
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


def freeze_standard_2048_expression_checkpoint_preregistration_v33(
) -> Standard2048ExpressionCheckpointPreregistrationV33:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["expression_checkpoint_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen checkpoint preregistration changed")
    return Standard2048ExpressionCheckpointPreregistrationV33(
        _ISSUER, raw, identity
    )


def verify_standard_2048_expression_checkpoint_preregistration_v33(
    value: Standard2048ExpressionCheckpointPreregistrationV33,
) -> Standard2048ExpressionCheckpointPreregistrationV33:
    if type(value) is not Standard2048ExpressionCheckpointPreregistrationV33:
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
    "Standard2048ExpressionCheckpointPreregistrationV33",
    "freeze_standard_2048_expression_checkpoint_preregistration_v33",
    "verify_standard_2048_expression_checkpoint_preregistration_v33",
)
