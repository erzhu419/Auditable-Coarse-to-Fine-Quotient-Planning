"""Outcome-free V181r5 successor after retained V181r4 negative transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r5 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PRESERVED_V181R4_CAMPAIGN_ID = (
    "defda4e4b216105cbadae6ddc50c9cc9a2bf6b17d31a4a59f7395d401743a6d9"
)
PRESERVED_V181R4_VERIFICATION_ID = (
    "6cda784e10eecb1e2a9879b8c341b4c7f2cf0b86446e00221f6590283e506789"
)
V181R5_IMPLEMENTATION_COMMIT = "744c1ec"
MANIFEST_COMMITMENTS_V181R5 = (
    "3e8b9b56d3efc5afa962a63107a8111494850fcb0ac72630b5b2b6da334e8e23",
    "957722e41ea93e81de435e9777c56a9f69a254c6232da249975acaac91f08e86",
    "0f632e72ee9a7d72321c00fc4079d4c20c25eb136fbf7ca8238a8be0614ddf49",
)
EXPECTED_SUCCESSOR_ID = (
    "9d4a6159f2e0edf31e976c7bf7f3c62ea867437f5a2ea61a5301d456ef0b79b4"
)
EXPECTED_CANONICAL_BYTE_COUNT = 3_304
EXPECTED_CANONICAL_SHA256 = (
    "a53a0bac509a8769e6413e883802a8d88bc81852a5125f8651df2c7da03de6fc"
)


def build_open_world_protocol_successor_v181r5() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.open_world_protocol_successor.v181r5",
        "preserved_v181r4_campaign_id": PRESERVED_V181R4_CAMPAIGN_ID,
        "preserved_v181r4_verification_id": PRESERVED_V181R4_VERIFICATION_ID,
        "v181r5_implementation_commit": V181R5_IMPLEMENTATION_COMMIT,
        "predecessor_registered_gate_reclassified_as_success": False,
        "same_v181r4_identity_rerun_forbidden": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V181R5),
        "manifest_count": 3,
        "manifest_reveal_bytes_embedded": False,
        "target_outcomes_accessed": False,
        "correction": {
            "failure_cause": "ARCHIVE_MDL_DISCOUNT_NEGATIVE_TRANSFER_AND_EAGER_RANK_RECOMPUTATION",
            "v181r4_prior_labels_avoided": -32,
            "v181r4_weight_agnostic_total_work_dominance_observed": False,
            "archive_mdl_discount_removed": True,
            "archive_expression_must_belong_to_current_typed_grammar": True,
            "archive_reference_revalidated_on_current_rows": True,
            "same_mdl_objective_both_arms": True,
            "revalidated_prior_confirmation_credit_cap": 1,
            "persistent_model_bound_rank_cache_added": True,
            "cache_discarded_on_compiled_model_identity_change": True,
            "mismatch_only_recompilation_reused_unchanged": True,
            "maximum_enumeration_events_per_expression": 2_000_000,
            "resource_cap_increased_relative_to_v181r4": False,
            "finite_candidate_program_catalog_added": False,
            "named_domain_family_added": False,
        },
        "durable_progress_protocol": {
            "checkpoint_after_every_acquisition_block": True,
            "checkpoint_after_every_model_mismatch_recompile": True,
            "checkpoint_after_every_episode": True,
            "checkpoint_after_every_distribution": True,
            "rank_before_and_successor_upper_bound_in_every_certificate": True,
            "persistent_rank_cache_usage_in_every_certificate": True,
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
            "minimum_horizon": 8,
        },
        "matched_protocol": {
            "same_witness_blind_acquisition_policy": True,
            "same_synthesizer": True,
            "same_stopping_rule": True,
            "same_confidence_formula_both_arms": True,
            "prior_credit_requires_selected_archive_reference_revalidated_on_current_rows": True,
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
        "protocol_successor_id": domains.extension_content_id_v181r5(
            domains.CONSTRUCTION_K7_PROTOCOL_SUCCESSOR_V181R5_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldProtocolSuccessorV181R5:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_successor_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_protocol_successor_v181r5() -> OpenWorldProtocolSuccessorV181R5:
    document = build_open_world_protocol_successor_v181r5()
    raw = canonical_json_bytes(document)
    if EXPECTED_SUCCESSOR_ID != "0" * 64 and not (
        document["protocol_successor_id"] == EXPECTED_SUCCESSOR_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r5 frozen outcome-free successor changed")
    return OpenWorldProtocolSuccessorV181R5(
        _ISSUER,
        raw,
        document["protocol_successor_id"],
    )


__all__ = (
    "EXPECTED_SUCCESSOR_ID",
    "MANIFEST_COMMITMENTS_V181R5",
    "freeze_open_world_protocol_successor_v181r5",
)
