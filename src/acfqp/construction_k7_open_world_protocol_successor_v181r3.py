"""Outcome-free V181r3 successor after the retained V181r2 interruption."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r3 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PRESERVED_V181R2_FAILURE_ID = (
    "6033595cb16f33d473de02e2c2329a13411678f14e1a979c5976207de6de1e47"
)
PRESERVED_V181R2_FAILURE_VERIFICATION_ID = (
    "dc3a679cd46a5c56c7abddef6a84c8002777e9efb2b3c3573286de679534ba56"
)
V181R3_IMPLEMENTATION_COMMIT = "31df836"
MANIFEST_COMMITMENTS_V181R3 = (
    "441223899d8ddd44d45080b9ba40e3e04d0d6bb7ec7a56d0a4d4514ef30e6892",
    "8bb38b0a68ad8326928065a61f07f0edc81363b2e0fffb73e4c7f8c331df2d7d",
    "73eb1549e5d395cb7792784e8f5b4053b35c5c8f856885287ddc2ad3de3a9afa",
)
EXPECTED_SUCCESSOR_ID = (
    "482241c391ff81b7afd332fe1f5844b2e5fe126ce0382844af96aa6ae15efea9"
)
EXPECTED_CANONICAL_BYTE_COUNT = 3_063
EXPECTED_CANONICAL_SHA256 = (
    "1d05137523bb46eecbd6f6ea0e5b45e547bd7e392da03d62f003ee407666af94"
)


def build_open_world_protocol_successor_v181r3() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.open_world_protocol_successor.v181r3",
        "preserved_v181r2_failure_id": PRESERVED_V181R2_FAILURE_ID,
        "preserved_v181r2_failure_verification_id": (
            PRESERVED_V181R2_FAILURE_VERIFICATION_ID
        ),
        "v181r3_implementation_commit": V181R3_IMPLEMENTATION_COMMIT,
        "predecessor_interruption_reclassified_as_scientific_result": False,
        "same_v181r2_identity_rerun_forbidden": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V181R3),
        "manifest_count": 3,
        "manifest_reveal_bytes_embedded": False,
        "target_outcomes_accessed": False,
        "correction": {
            "cyclic_residual_search_applied_to_every_integer_coordinate": True,
            "one_point_modular_residual_support_allowed": True,
            "mdl_unseen_length_lower_bound_required": True,
            "duplicate_input_outcomes_prove_exact_program_impossible": True,
            "full_recompile_required_only_after_model_support_or_terminal_mismatch": True,
            "covered_confirmation_block_requires_zero_enumeration_events": True,
            "adaptive_episode_model_retained_within_arm_and_distribution": True,
            "maximum_enumeration_events_per_expression": 2_000_000,
            "resource_cap_increased_relative_to_v181r2": False,
            "finite_candidate_program_catalog_added": False,
            "named_domain_family_added": False,
        },
        "durable_progress_protocol": {
            "checkpoint_after_every_acquisition_block": True,
            "checkpoint_after_every_arm": True,
            "checkpoint_after_every_model_mismatch_recompile": True,
            "checkpoint_after_every_episode": True,
            "checkpoint_after_every_distribution": True,
            "exact_manifest_arm_occurrence_stage_required": True,
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
            "same_adaptive_episode_update_rule": True,
            "only_arm_switch": "REUSABLE_SUBPROGRAM_ARCHIVE_AVAILABLE",
            "strict_incompatible_schema_ood_no_transfer_required": True,
            "certificate_failure_only_local_ground_distinctions": True,
            "execution_observation_without_model_mismatch_cannot_trigger_recompile": True,
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
        "protocol_successor_id": domains.extension_content_id_v181r3(
            domains.CONSTRUCTION_K7_PROTOCOL_SUCCESSOR_V181R3_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldProtocolSuccessorV181R3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_successor_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_protocol_successor_v181r3() -> OpenWorldProtocolSuccessorV181R3:
    document = build_open_world_protocol_successor_v181r3()
    raw = canonical_json_bytes(document)
    if EXPECTED_SUCCESSOR_ID != "0" * 64 and not (
        document["protocol_successor_id"] == EXPECTED_SUCCESSOR_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r3 frozen outcome-free successor changed")
    return OpenWorldProtocolSuccessorV181R3(
        _ISSUER,
        raw,
        document["protocol_successor_id"],
    )


__all__ = (
    "EXPECTED_SUCCESSOR_ID",
    "MANIFEST_COMMITMENTS_V181R3",
    "freeze_open_world_protocol_successor_v181r3",
)
