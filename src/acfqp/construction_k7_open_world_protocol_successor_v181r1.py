"""Outcome-free V181r1 successor with retained fresh reveal commitments."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r1 as domains
from acfqp import construction_k7_open_world_manifest_failure_v181 as failure_v181
from acfqp import construction_k7_open_world_preregistration_v181 as prereg_v181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_COMMITMENTS_V181R1 = (
    "4532e5a85daf272dd4c208b1699beec286252f7295b87fc5569047bf04ad3d52",
    "3a996044afc443f2c8f6deee7e8e54d7544ac4bcd1c4b0727ecac2b586647f88",
    "565d06fed7549d1576030ff11466708869f18d2f7ef92b9fc8548bf8e14df724",
)
EXPECTED_SUCCESSOR_ID = (
    "eaac7f36271a953ad5f62ddb1cb52f16c3c57888bb8f9ec557725594d54698c1"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_402
EXPECTED_CANONICAL_SHA256 = (
    "94a74cb0f5c422a03e11d2de7e3a778886cfa8bdf7c70c1b0e1f173f68097e0b"
)


def build_open_world_protocol_successor_v181r1() -> dict[str, Any]:
    predecessor_preregistration = prereg_v181.freeze_open_world_preregistration_v181()
    predecessor_failure = failure_v181.freeze_open_world_manifest_failure_v181()
    payload = {
        "schema": "acfqp.open_world_protocol_successor.v181r1",
        "predecessor_v181_preregistration_id": predecessor_preregistration.preregistration_id,
        "preserved_v181_failure_id": predecessor_failure.failure_id,
        "predecessor_implementation_source_bytes_reused_without_mutation": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V181R1),
        "manifest_count": 3,
        "manifest_reveal_preimages_retained_off_artifact_before_execution": True,
        "manifest_reveal_bytes_embedded": False,
        "target_outcomes_accessed": False,
        "source_generation_witness_available_to_synthesizer": False,
        "source_policy_reads_only_opaque_schema_and_raw_transitions": True,
        "whole_program_candidate_catalog_present": False,
        "named_target_family_registry_present": False,
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
        "matched_acquisition": {
            "query_block_size": 16,
            "same_state_action_repeat_count": 2,
            "minimum_label_count": 32,
            "maximum_label_count": 512,
            "stable_zero_error_confirmation_blocks": 2,
            "same_synthesizer_and_stop_rule": True,
            "only_arm_switch": "REUSABLE_SUBPROGRAM_ARCHIVE_AVAILABLE",
        },
        "registered_execution": {
            "receding_abstract_planning_required": True,
            "planner_horizon_at_least_five": True,
            "certificate_failure_only_local_ground_distinctions": True,
            "producer_free_reconstruction_required": True,
            "strict_incompatible_schema_ood_no_transfer_required": True,
            "all_failures_and_unfavourable_results_retained": True,
            "maximum_simultaneous_worker_count": 2,
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
        "protocol_successor_id": domains.extension_content_id_v181r1(
            domains.CONSTRUCTION_K7_PROTOCOL_SUCCESSOR_V181R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldProtocolSuccessorV181R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_successor_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_protocol_successor_v181r1() -> OpenWorldProtocolSuccessorV181R1:
    document = build_open_world_protocol_successor_v181r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_SUCCESSOR_ID != "0" * 64 and not (
        document["protocol_successor_id"] == EXPECTED_SUCCESSOR_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r1 frozen outcome-free successor changed")
    return OpenWorldProtocolSuccessorV181R1(
        _ISSUER,
        raw,
        document["protocol_successor_id"],
    )


__all__ = (
    "EXPECTED_SUCCESSOR_ID",
    "MANIFEST_COMMITMENTS_V181R1",
    "freeze_open_world_protocol_successor_v181r1",
)
