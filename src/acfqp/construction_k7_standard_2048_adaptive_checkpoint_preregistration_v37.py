"""Outcome-free registration of the first V35 adaptive-model continuation.

The V35 expression model is already proved against its committed target and
V36 independently accounts its acquisition and 128-decision execution.  This
registration freezes the four live decision-128 checkpoints before extending
them.  No new target-probability label is permitted in this segment: a
certificate failure must close the segment rather than silently expanding the
learned model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as v35
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V37_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V37_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V37_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V37_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V37_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "37.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.200"
PROFILE_KEY = "construction_k7_standard_2048_adaptive_exact_checkpoint_v37"
PREREGISTRATION_ID = "21b57b71109fd4e562fbdbd1d3c124def39f951e86b6d810f3519e3154c7e6c1"
EXPECTED_CANONICAL_BYTE_COUNT = 5147
EXPECTED_CANONICAL_SHA256 = "500a3641fea366ee6dd1ff613a5ae4e7c1dbf3776b019f1f82760d9ada1322f0"

V35_PREREGISTRATION_ID = (
    "d2705f1b310b2f88f41799376a69f55b3355b53a54a2a103ba11e5dbf00491a9"
)
V35_CAMPAIGN_ID = (
    "c33002f8bac5415d94c5185876ce104ac859243e7b50ee5922c1be9b4a812d25"
)
V35_VERIFICATION_ID = (
    "0591b03140cb3e807b68ee4e90129c93863a45ef29ed44896df49c7d4caea348"
)
V36R4_PREREGISTRATION_ID = (
    "78494b3a611b198a99e00d324eb570ba3a6b6346e3c432c93a47d0456835de2a"
)
V36R4_CAMPAIGN_ID = (
    "758f01ac78789d25512b218ed16b8ca4bfaa95a08dc52e81fc15601b42662693"
)
V36R4_VERIFICATION_ID = (
    "ed3354625ab6c3e8928bdf0b0807ee7e7c47a2c5c84a0e364916fc1ac2e94c14"
)
TARGET_KERNEL_ID = (
    "e542f25f3929b78c3dd622beaf632df1fee75a775de99bead1232a8a8a936236"
)
ADAPTIVE_EXPRESSION_OVERLAY_ID = (
    "36996bf7b4394e51c1d8a0ef74c50dc9ce5157d28c39ba75d92aae84c9b9f178"
)
ADAPTIVE_EXPRESSION_PROPOSAL_ID = (
    "48abfadba373a858c8261864f77878c65c0f13e3c6f57f94100a9be23023f2b9"
)
ADAPTIVE_EXPRESSION_PROOF_ID = (
    "24e04000e8aa600ba9186618fc2e9fefa37df33fed57e088fef3ed26c83496d5"
)
ADAPTIVE_EXPRESSION_CANDIDATE_ID = (
    "d296cdeb05cc1be50970c7e131d556118b22060ab95a075a67ad4d03e43af82b"
)

PLANNING_HORIZON = 3
SOURCE_DECISION_COUNT = 128
SEGMENT_DECISION_LIMIT = 128
GLOBAL_DECISION_START = 128
GLOBAL_DECISION_STOP_EXCLUSIVE = 256
LOCAL_COLD_CHECKPOINTS = (0, 63, 127)
GLOBAL_COLD_CHECKPOINTS = (128, 191, 255)
INHERITED_TARGET_PROBABILITY_LABEL_COUNT = 6
STRICT_NO_PRIOR_CONTEXT_LABEL_COUNT = 2400

CHECKPOINT_EPISODE_IDS = (
    "4360c07cc8ec38300bd219fe5d1ecef79a09b5f7ef339f1558861227bdf16c8f",
    "846c6dd12ced07be34160c0485dea0853b0c72231b41fe5920e95a53e594045c",
    "3d863e5f8ff45f471c454f06105523aa7373bdec3e72e07245e5651624e9625d",
    "316a7b17dc40a459445519d76c7f1a54196b54eb60a4349686b331ec77ca9e73",
)
CHECKPOINT_BOARDS = (
    (0, 0, 0, 4, 0, 0, 0, 8, 0, 1, 2, 5, 1, 1, 2, 2),
    (5, 2, 0, 0, 8, 2, 1, 0, 2, 0, 0, 1, 1, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 3, 4, 0, 0, 5, 8, 1, 1, 1, 2),
    (0, 3, 4, 1, 0, 1, 7, 2, 1, 0, 7, 1, 0, 0, 3, 1),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V37_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V37_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V37_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V37_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V37_DOMAIN,
}


class ConstructionK7Standard2048AdaptiveCheckpointPreregistrationV37Error(
    ValueError
):
    """The checkpoint, learned model, continuation, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveCheckpointPreregistrationV37Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_checkpoint_preregistration.v37",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v35_adaptive_expression_preregistration_id": V35_PREREGISTRATION_ID,
            "v35_adaptive_expression_campaign_id": V35_CAMPAIGN_ID,
            "v35_adaptive_expression_verification_id": V35_VERIFICATION_ID,
            "v36r4_accounting_preregistration_id": V36R4_PREREGISTRATION_ID,
            "v36r4_accounted_campaign_id": V36R4_CAMPAIGN_ID,
            "v36r4_accounting_verification_id": V36R4_VERIFICATION_ID,
            "all_predecessor_identities_frozen_before_v37_execution": True,
        },
        "proved_reusable_world_model": {
            "target_kernel_id": TARGET_KERNEL_ID,
            "adaptive_expression_overlay_id": ADAPTIVE_EXPRESSION_OVERLAY_ID,
            "adaptive_expression_proposal_id": ADAPTIVE_EXPRESSION_PROPOSAL_ID,
            "adaptive_expression_proof_id": ADAPTIVE_EXPRESSION_PROOF_ID,
            "adaptive_expression_candidate_id": ADAPTIVE_EXPRESSION_CANDIDATE_ID,
            "expression_ast": {
                "operator": "COUNT_EQ",
                "vector_source": "POST_SWIPE_BOARD_RANKS",
                "constant": 2,
            },
            "direction": "LE_OVERRIDE",
            "threshold": 1,
            "base_rank_two_probability": {"numerator": 1, "denominator": 10},
            "override_rank_two_probability": {"numerator": 1, "denominator": 4},
            "selected_only_after_certificate_triggered_local_acquisition": True,
            "semantically_proved_exact_before_checkpoint_registration": True,
            "serialized_target_probability_table_present": False,
        },
        "checkpoint_workload": {
            "source_episode_ids": list(CHECKPOINT_EPISODE_IDS),
            "checkpoint_boards": [list(board) for board in CHECKPOINT_BOARDS],
            "checkpoint_status": ["ACTIVE"] * len(CHECKPOINT_BOARDS),
            "episode_seeds": list(v35.EPISODE_SEEDS),
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
            "fraction_or_precision_approximation_allowed": False,
            "certificate_frozen_before_target_transition": True,
            "target_seed_decision_index_uses_global_offset": True,
            "execution_transition_may_modify_world_model": False,
            "new_frontier_disagreement_may_be_hidden": False,
            "certificate_failure_closes_segment_before_any_unregistered_query": True,
        },
        "sample_tax_contract": {
            "inherited_target_probability_label_count": INHERITED_TARGET_PROBABILITY_LABEL_COUNT,
            "additional_model_acquisition_label_budget": 0,
            "strict_no_prior_context_label_count": STRICT_NO_PRIOR_CONTEXT_LABEL_COUNT,
            "inherited_label_fraction_of_no_prior": {
                "numerator": 1,
                "denominator": 400,
            },
            "sample_count_and_planning_compute_remain_separate_axes": True,
            "positive_result_requires_all_certificates_and_transitions_to_replay": True,
        },
        "required_positive_conditions": [
            "ALL_SOURCE_CHECKPOINT_IDENTITIES_MATCH_VERIFIED_V35",
            "V36R4_ACCOUNTING_VERIFICATION_PRECEDES_V37_EXECUTION",
            "ALL_SEGMENT_PLANS_USE_THE_PROVED_V35_EXPRESSION_MODEL",
            "ZERO_ADDITIONAL_TARGET_PROBABILITY_LABELS",
            "ALL_REGISTERED_COLD_CHECKPOINTS_MATCH_EXACT_GROUND",
            "ALL_SEEDED_TRANSITIONS_USE_GLOBAL_DECISION_INDICES",
        ],
        "outcome_fields_present": False,
        "checkpoint_execution_performed": False,
        "terminal_or_tile_2048_reached": False,
        "full_standard_2048_game_claimed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
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
        "adaptive_checkpoint_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveCheckpointPreregistrationV37:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("adaptive checkpoint preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("adaptive checkpoint preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_checkpoint_preregistration_id"
        }
        if (
            document.get("adaptive_checkpoint_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("adaptive checkpoint preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("adaptive checkpoint preregistration is not an object")
        return document


def freeze_standard_2048_adaptive_checkpoint_preregistration_v37(
) -> Standard2048AdaptiveCheckpointPreregistrationV37:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["adaptive_checkpoint_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen adaptive checkpoint preregistration changed")
    return Standard2048AdaptiveCheckpointPreregistrationV37(
        _ISSUER, raw, identity
    )


def verify_standard_2048_adaptive_checkpoint_preregistration_v37(
    value: Standard2048AdaptiveCheckpointPreregistrationV37,
) -> Standard2048AdaptiveCheckpointPreregistrationV37:
    if type(value) is not Standard2048AdaptiveCheckpointPreregistrationV37:
        _fail("adaptive checkpoint preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("adaptive checkpoint preregistration semantics changed")
    return value


__all__ = (
    "ADAPTIVE_EXPRESSION_CANDIDATE_ID",
    "ADAPTIVE_EXPRESSION_OVERLAY_ID",
    "ADAPTIVE_EXPRESSION_PROOF_ID",
    "ADAPTIVE_EXPRESSION_PROPOSAL_ID",
    "CHECKPOINT_BOARDS",
    "CHECKPOINT_EPISODE_IDS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "PREREGISTRATION_ID",
    "Standard2048AdaptiveCheckpointPreregistrationV37",
    "freeze_standard_2048_adaptive_checkpoint_preregistration_v37",
    "verify_standard_2048_adaptive_checkpoint_preregistration_v37",
)
