"""Outcome-free preregistration for H=3 targeted-model reuse."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.domains.standard_2048 import boards_from_rows_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_CAMPAIGN_V8_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_EPISODE_V8_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_PREREGISTRATION_V8_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_VERIFICATION_V8_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_INTERVAL_BINDING_V8_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_SUPPORT_PROPOSAL_V8_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_AUDIT_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_MATCHED_DIRECT_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_MODEL_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_ROW_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_ROBUST_PLAN_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "8.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.162"
PROFILE_KEY = "construction_k7_standard_2048_h3_targeted_reuse_v8"
PREDECESSOR_V161_CAMPAIGN_ID = (
    "34b184f1ab30567da483d3132331eacdac20b50648780bb828f13013102170ab"
)
PREDECESSOR_V161_PREREGISTRATION_ID = (
    "f3bfb0b24fb13e32dfc1592140bf92dc05167f5cd8df1ceba7a80498dc408e82"
)
PLANNING_HORIZON = 3
DECISIONS_PER_EPISODE = 8

PREREGISTERED_INITIAL_BOARDS = tuple(
    boards_from_rows_v1(rows)
    for rows in (
        ((0, 0, 0, 0), (0, 1, 1, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((0, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0)),
        ((1, 0, 0, 2), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((1, 0, 0, 0), (0, 0, 2, 0), (0, 0, 0, 0), (0, 0, 0, 0)),
    )
)
PREREGISTERED_EPISODE_SEEDS = tuple(
    f"standard-2048-v162-h3-reuse-{index:02d}-20260812"
    for index in range(len(PREREGISTERED_INITIAL_BOARDS))
)
FUTURE_DOMAINS = {
    "support_proposal": CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_SUPPORT_PROPOSAL_V8_DOMAIN,
    "interval_binding": CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_INTERVAL_BINDING_V8_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_EPISODE_V8_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_CAMPAIGN_V8_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_VERIFICATION_V8_DOMAIN,
}


class ConstructionK7Standard2048H3ReusePreregistrationV8Error(ValueError):
    """The frozen H=3 workload or reuse protocol changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048H3ReusePreregistrationV8Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_h3_reuse_preregistration.v8",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "predecessor_v161_campaign_id": PREDECESSOR_V161_CAMPAIGN_ID,
        "predecessor_v161_preregistration_id": PREDECESSOR_V161_PREREGISTRATION_ID,
        "reuse_targeted_raw_streams_and_final_count_vector": True,
        "reuse_v161_source_and_validation_archive_identities": True,
        "offline_observations_charged_once_at_shared_campaign_level": True,
        "v161_final_source_counts_by_cardinality": [
            8, 8, 8, 8, 8, 8, 8, 8, 256, 8192, 8192, 8192, 8192, 8192, 8192, 8
        ],
        "v161_final_validation_counts_by_cardinality": [
            4, 4, 4, 4, 4, 4, 4, 4, 128, 1024, 1024, 1024, 1024, 1024, 1024, 4
        ],
        "targeted_interval_binding_domain": (
            CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_INTERVAL_BINDING_V8_DOMAIN
        ),
        "targeted_support_proposal_domain": (
            CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_SUPPORT_PROPOSAL_V8_DOMAIN
        ),
        "unknown_support_mass_upper_within_registered_support_family": 0,
        "full_empty_cell_support_is_conditional_on_registered_candidate_family": True,
        "open_ended_support_completeness_claimed": False,
        "reused_partial_world_model_semantic_domains": {
            "row": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_ROW_V2_DOMAIN,
            "model": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_MODEL_V2_DOMAIN,
            "audit": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_AUDIT_V2_DOMAIN,
            "plan": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_ROBUST_PLAN_V2_DOMAIN,
            "direct": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_MATCHED_DIRECT_V2_DOMAIN,
        },
        "planning_horizon": PLANNING_HORIZON,
        "decisions_per_episode": DECISIONS_PER_EPISODE,
        "preregistered_initial_boards": [
            list(board) for board in PREREGISTERED_INITIAL_BOARDS
        ],
        "preregistered_episode_seeds": list(PREREGISTERED_EPISODE_SEEDS),
        "episode_count": len(PREREGISTERED_INITIAL_BOARDS),
        "decision_count": len(PREREGISTERED_INITIAL_BOARDS)
        * DECISIONS_PER_EPISODE,
        "persistent_partial_world_model_protocol": {
            "initial_row_count": 0,
            "audit_before_ground_support_materialization": True,
            "failed_proof_frontier_only_materialization": True,
            "maximum_recovery_transactions_per_decision": 4,
            "rows_reused_across_decisions_and_episodes": True,
            "successful_audit_executes_only_abstract_selected_action": True,
            "certificate_or_recovery_failure_route": "COLD_GROUND_FALLBACK",
        },
        "matched_cold_direct_control": {
            "horizon": PLANNING_HORIZON,
            "one_fresh_exact_model_per_decision": True,
            "evaluation_only_unless_selected_fallback": True,
            "no_model_construction_or_route_authority": True,
        },
        "required_positive_conditions": [
            "ALL_SELECTED_ACTIONS_EXACT_VALUE_AND_LOSS_EQUIVALENT_TO_COLD_DIRECT",
            "GROUND_SUPPORT_ROWS_ONLY_AFTER_FAILED_AUDIT",
            "PERSISTENT_ROWS_REUSED_ACROSS_MULTIPLE_DECISIONS",
        ],
        "if_required_condition_fails": (
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
        "h3_reuse_preregistration_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_PREREGISTRATION_V8_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048H3ReusePreregistrationV8:
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
            if key != "h3_reuse_preregistration_id"
        }
        if (
            document.get("h3_reuse_preregistration_id") != self.preregistration_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_PREREGISTRATION_V8_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("H3 preregistration root is not an object")
        return document


def freeze_standard_2048_h3_reuse_preregistration_v8(
) -> Standard2048H3ReusePreregistrationV8:
    document = _document()
    return Standard2048H3ReusePreregistrationV8(
        _ISSUER,
        canonical_json_bytes(document),
        document["h3_reuse_preregistration_id"],
    )


def verify_standard_2048_h3_reuse_preregistration_v8(
    value: Standard2048H3ReusePreregistrationV8,
) -> Standard2048H3ReusePreregistrationV8:
    if type(value) is not Standard2048H3ReusePreregistrationV8:
        _fail("verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("preregistration differs from frozen semantics")
    return value


__all__ = (
    "ConstructionK7Standard2048H3ReusePreregistrationV8Error",
    "DECISIONS_PER_EPISODE",
    "FUTURE_DOMAINS",
    "PLANNING_HORIZON",
    "PREREGISTERED_EPISODE_SEEDS",
    "PREREGISTERED_INITIAL_BOARDS",
    "PROFILE_KEY",
    "Standard2048H3ReusePreregistrationV8",
    "freeze_standard_2048_h3_reuse_preregistration_v8",
    "verify_standard_2048_h3_reuse_preregistration_v8",
)
