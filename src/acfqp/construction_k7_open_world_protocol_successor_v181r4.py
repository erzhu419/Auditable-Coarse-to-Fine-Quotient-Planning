"""Outcome-free V181r4 successor after the retained receding-plan failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r4 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PRESERVED_V181R3_CAMPAIGN_ID = (
    "499d6046ab3b12325c044b03374c5f377e9047d0b0d0b828a2dd628a585d4ce8"
)
PRESERVED_V181R3_VERIFICATION_ID = (
    "6a14973234274670ca77e166b6b982bca904361b1b626e88436e65be3bcda188"
)
V181R4_IMPLEMENTATION_COMMIT = "1bc8efd"
MANIFEST_COMMITMENTS_V181R4 = (
    "26a27f79b98f7bcf43bf277e5248696728539529db49ac906de5c9319c31b166",
    "d82ebbdd00ef492af3bd1b8e936300bb860b78ae5fb6141d5f7daf9b38553d34",
    "2df3d4b50d415a35e4991575da73fcd125aa6b917f6fba9351c032e9337c55fa",
)
EXPECTED_SUCCESSOR_ID = (
    "b3ac446fe6c144d13c7cd9e1a03b4c424f32df3fce716fb52df9a058fa1f9dff"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_906
EXPECTED_CANONICAL_SHA256 = (
    "6b005ae8b4dad79b73c1e9287bc0e15bc32243d75c403719feb1239010a09577"
)


def build_open_world_protocol_successor_v181r4() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.open_world_protocol_successor.v181r4",
        "preserved_v181r3_campaign_id": PRESERVED_V181R3_CAMPAIGN_ID,
        "preserved_v181r3_verification_id": PRESERVED_V181R3_VERIFICATION_ID,
        "v181r4_implementation_commit": V181R4_IMPLEMENTATION_COMMIT,
        "predecessor_registered_gate_reclassified_as_success": False,
        "same_v181r3_identity_rerun_forbidden": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V181R4),
        "manifest_count": 3,
        "manifest_reveal_bytes_embedded": False,
        "target_outcomes_accessed": False,
        "correction": {
            "failure_cause": "RESET_HORIZON_ALLOWED_NONDECREASING_WINNING_ACTION",
            "minimum_worst_case_terminal_distance_computed": True,
            "selected_action_requires_strict_rank_decrease_for_every_successor": True,
            "reset_horizon_cannot_increase_minimum_rank": True,
            "v181r3_carrier_aware_synthesizer_reused_unchanged": True,
            "mismatch_only_recompilation_reused_unchanged": True,
            "maximum_enumeration_events_per_expression": 2_000_000,
            "resource_cap_increased_relative_to_v181r3": False,
            "finite_candidate_program_catalog_added": False,
            "named_domain_family_added": False,
        },
        "durable_progress_protocol": {
            "checkpoint_after_every_acquisition_block": True,
            "checkpoint_after_every_model_mismatch_recompile": True,
            "checkpoint_after_every_episode": True,
            "checkpoint_after_every_distribution": True,
            "rank_before_and_successor_upper_bound_in_every_certificate": True,
            "finish_forward_existing_exact_checkpoint_required": True,
            "failure_must_reference_last_durable_checkpoint": True,
        },
        "target_denominator": {
            "distribution_count": 3,
            "iid_occurrences_per_distribution": 12,
            "matched_arms": [
                "REUSED_SUBPROGRAM_PRIOR",
                "EMPTY_ARCHIVE_NO_PRIOR",
            ],
            "total_episode_count": 72,
            "minimum_horizon": 6,
        },
        "matched_protocol": {
            "same_witness_blind_acquisition_policy": True,
            "same_synthesizer": True,
            "same_stopping_rule": True,
            "same_rank_decreasing_planner": True,
            "same_adaptive_episode_update_rule": True,
            "only_arm_switch": "REUSABLE_SUBPROGRAM_ARCHIVE_AVAILABLE",
            "strict_incompatible_schema_ood_no_transfer_required": True,
            "certificate_failure_only_local_ground_distinctions": True,
        },
        "accounting_axes": [
            "OFFLINE_SOURCE_LABELS",
            "TARGET_GROUND_LABELS",
            "EXECUTION_STEPS",
            "PROGRAM_ENUMERATION_EVENTS",
            "PLANNING_EVENTS",
            "CERTIFICATE_EVENTS",
            "MODEL_RECOMPILATIONS",
            "OUTPUT_BYTES",
        ],
        "claim_locks": {
            "open_world_campaign_completed": False,
            "open_ended_world_model_invention_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "broad_iid_sample_efficiency_claimed": False,
            "total_work_dominance_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "protocol_successor_id": domains.extension_content_id_v181r4(
            domains.CONSTRUCTION_K7_PROTOCOL_SUCCESSOR_V181R4_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldProtocolSuccessorV181R4:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_successor_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_protocol_successor_v181r4() -> OpenWorldProtocolSuccessorV181R4:
    document = build_open_world_protocol_successor_v181r4()
    raw = canonical_json_bytes(document)
    if EXPECTED_SUCCESSOR_ID != "0" * 64 and not (
        document["protocol_successor_id"] == EXPECTED_SUCCESSOR_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r4 frozen outcome-free successor changed")
    return OpenWorldProtocolSuccessorV181R4(
        _ISSUER,
        raw,
        document["protocol_successor_id"],
    )


__all__ = (
    "EXPECTED_SUCCESSOR_ID",
    "MANIFEST_COMMITMENTS_V181R4",
    "freeze_open_world_protocol_successor_v181r4",
)
