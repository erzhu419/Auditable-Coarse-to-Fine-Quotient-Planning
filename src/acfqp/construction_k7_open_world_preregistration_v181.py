"""Final source-frozen preregistration before any V181 manifest reveal."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181 as domains
from acfqp import construction_k7_open_world_protocol_contract_v181 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("d97cfcb", "597d58b", "b21446a")
SOURCE_FILENAMES = (
    "construction_k7_domain_registry_extension_v181.py",
    "construction_k7_open_world_protocol_contract_v181.py",
    "open_world_universal_synthesizer_v181.py",
    "open_world_transition_oracle_v181.py",
    "open_world_compiled_model_v181.py",
)
EXPECTED_PREREGISTRATION_ID = (
    "eb7943553cbefca2068b54abcf0d897530eb6d576ec23fd2ed5746b2d261364b"
)
EXPECTED_CANONICAL_BYTE_COUNT = 4_227
EXPECTED_CANONICAL_SHA256 = (
    "570b61363adf71864b11749555167e7c234133d2f1eb8555ff8b0bb408aa043c"
)


def _source_facts() -> list[dict[str, Any]]:
    base = Path(__file__).resolve().parent
    rows = []
    for filename in SOURCE_FILENAMES:
        raw = (base / filename).read_bytes()
        rows.append(
            {
                "filename": filename,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def build_open_world_preregistration_v181() -> dict[str, Any]:
    contract = protocol.freeze_open_world_protocol_contract_v181()
    payload = {
        "schema": "acfqp.open_world_preregistration.v181",
        "open_world_protocol_contract_id": contract.contract_id,
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": _source_facts(),
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS),
        "manifest_reveal_bytes_embedded": False,
        "named_target_family_registry_present": False,
        "target_denominator": {
            "opaque_distribution_count": 3,
            "iid_occurrences_per_distribution": 12,
            "occurrence_indices": list(range(12)),
            "matched_arms": [
                "REUSED_SUBPROGRAM_PRIOR",
                "EMPTY_ARCHIVE_NO_PRIOR",
            ],
            "total_target_episode_count": 72,
            "strict_ood_negative_control_count": 3,
        },
        "source_acquisition_policy": {
            "policy_name": "HASHED_STATE_ACTION_DISAGREEMENT_WITH_STABILITY_STOP",
            "reads_manifest_program_or_generation_witness": False,
            "reads_only_opaque_state_legal_actions_and_raw_successor": True,
            "query_block_size": 16,
            "same_state_action_repeat_count": 2,
            "minimum_source_label_count": 32,
            "maximum_source_label_count": 512,
            "stability_confirmation_block_count": 2,
            "stop_requires_same_compiled_program_projection": True,
            "stop_requires_zero_confirmation_prediction_error": True,
            "same_stop_rule_for_both_arms": True,
            "prior_arm_only_switch": "REUSABLE_SUBPROGRAM_ARCHIVE_AVAILABLE",
        },
        "target_execution_policy": {
            "horizon_is_read_from_committed_opaque_oracle_schema": True,
            "minimum_horizon": 5,
            "maximum_decisions_per_occurrence": 64,
            "planner_input_is_compiled_model_and_opaque_actions_only": True,
            "raw_rows_passed_to_planner": False,
            "certificate_failure_precedes_every_local_ground_query": True,
            "unexpected_successor_invalidates_only_minimal_model_dependencies": True,
            "recompile_after_local_ground_query": True,
        },
        "registered_gates": {
            "all_72_target_episodes_must_terminalize": True,
            "all_three_opaque_distributions_must_pass": True,
            "partial_support_must_be_observed_in_every_distribution": True,
            "factor_boundaries_must_be_derived_from_program_dependencies": True,
            "strict_ood_must_reject_before_prior_or_outcome_access": True,
            "producer_free_reconstruction_required": True,
            "sample_tax_result_must_report_each_distribution_and_aggregate": True,
            "weight_agnostic_total_work_comparison_required": True,
            "unfavourable_or_tied_prior_result_must_be_retained": True,
        },
        "resource_schedule": {
            "maximum_simultaneous_worker_count": 2,
            "maximum_program_enumeration_events_per_expression": 2_000_000,
            "maximum_source_labels_per_distribution_and_arm": 512,
            "maximum_target_ground_labels_per_occurrence": 32,
            "maximum_decisions_per_occurrence": 64,
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
            "manifest_reveals_accessed": False,
            "target_outcomes_accessed": False,
            "implementation_source_frozen": True,
            "finite_candidate_program_catalog_used": False,
            "named_target_family_used": False,
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
        "open_world_preregistration_id": domains.extension_content_id_v181(
            domains.CONSTRUCTION_K7_PREREGISTRATION_V181_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldPreregistrationV181:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_preregistration_v181() -> OpenWorldPreregistrationV181:
    document = build_open_world_preregistration_v181()
    raw = canonical_json_bytes(document)
    if EXPECTED_PREREGISTRATION_ID != "0" * 64 and not (
        document["open_world_preregistration_id"] == EXPECTED_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181 frozen final preregistration changed")
    return OpenWorldPreregistrationV181(
        _ISSUER,
        raw,
        document["open_world_preregistration_id"],
    )


__all__ = (
    "EXPECTED_PREREGISTRATION_ID",
    "freeze_open_world_preregistration_v181",
)
