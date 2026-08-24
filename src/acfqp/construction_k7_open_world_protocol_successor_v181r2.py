"""Outcome-free V181r2 successor after the retained synthesis failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r2 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PRESERVED_V181R1_FAILURE_ID = (
    "51a28e11167bd114637520deb8235dd8974f7dd50742505b14b0454ed61e5b7b"
)
PRESERVED_V181R1_FAILURE_VERIFICATION_ID = (
    "a06e5b8bcfcbf772c0df12f562ccd18e0db8c794d1390de5c414e1395fa6ece5"
)
V181R2_IMPLEMENTATION_COMMIT = (
    "42c98f1c16e6486998ef89f98c8647adf2464de2"
)
MANIFEST_COMMITMENTS_V181R2 = (
    "c05de99884acecece9533d2fb3f16cf3da94c1767872b0e60f9d489679d90c3f",
    "6ced422fba28044a43e0a0fd95ada9aeb346e013210271d26e88302419855bef",
    "da369a24a673914edc4be60a4f41e3c166ddfea237cfe8e59d39001f3e852c0f",
)
EXPECTED_SUCCESSOR_ID = (
    "f7a53fad7da1ddc354a48649c8777db7cbde22505de800f6d4592705d60e7eff"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_619
EXPECTED_CANONICAL_SHA256 = (
    "02adf8ac5f4b5a96f1a69832750da8d3150c3622cfcdbfbb1d468208d49d4832"
)


def build_open_world_protocol_successor_v181r2() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.open_world_protocol_successor.v181r2",
        "preserved_v181r1_failure_id": PRESERVED_V181R1_FAILURE_ID,
        "preserved_v181r1_failure_verification_id": (
            PRESERVED_V181R1_FAILURE_VERIFICATION_ID
        ),
        "v181r2_implementation_commit": V181R2_IMPLEMENTATION_COMMIT,
        "predecessor_failure_reclassified_as_success": False,
        "same_v181r1_identity_rerun_forbidden": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V181R2),
        "manifest_count": 3,
        "manifest_reveal_bytes_embedded": False,
        "target_outcomes_accessed": False,
        "correction": {
            "failure_cause": "SIGNED_WRAPAROUND_RESIDUAL_SUPPORT_INFLATION",
            "cyclic_residual_carrier_derived_from_observed_coordinate": True,
            "shortest_length_residual_checked_before_longer_deterministic_frontier": True,
            "maximum_enumeration_events_per_expression": 2_000_000,
            "resource_cap_increased_relative_to_v181r1": False,
            "finite_candidate_program_catalog_added": False,
            "named_domain_family_added": False,
        },
        "durable_progress_protocol": {
            "checkpoint_after_every_acquisition_block": True,
            "checkpoint_after_every_arm": True,
            "checkpoint_after_every_distribution": True,
            "exact_manifest_arm_block_index_required": True,
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
            "minimum_horizon": 5,
        },
        "matched_protocol": {
            "same_acquisition_policy": True,
            "same_synthesizer": True,
            "same_stopping_rule": True,
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
        "protocol_successor_id": domains.extension_content_id_v181r2(
            domains.CONSTRUCTION_K7_PROTOCOL_SUCCESSOR_V181R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldProtocolSuccessorV181R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_successor_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_protocol_successor_v181r2() -> OpenWorldProtocolSuccessorV181R2:
    document = build_open_world_protocol_successor_v181r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_SUCCESSOR_ID != "0" * 64 and not (
        document["protocol_successor_id"] == EXPECTED_SUCCESSOR_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r2 frozen outcome-free successor changed")
    return OpenWorldProtocolSuccessorV181R2(
        _ISSUER,
        raw,
        document["protocol_successor_id"],
    )


__all__ = (
    "EXPECTED_SUCCESSOR_ID",
    "MANIFEST_COMMITMENTS_V181R2",
    "freeze_open_world_protocol_successor_v181r2",
)
