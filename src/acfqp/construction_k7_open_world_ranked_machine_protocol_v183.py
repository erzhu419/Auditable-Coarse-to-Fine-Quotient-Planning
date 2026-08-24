"""Outcome-free protocol for a fresh proof-carrying V183 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v183 as domains
from acfqp import construction_k7_open_world_total_machine_campaign_freeze_v182r2 as predecessor
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PROTOCOL_ID = (
    "3c61d4b161ed17ce6734f85574b94a1d70f6de672e36bf312f377a22430a1b19"
)
EXPECTED_CANONICAL_BYTE_COUNT = 3_896
EXPECTED_CANONICAL_SHA256 = (
    "cf6393659572fddfe835567db59cef82fd700dc405b09546da02f45fecba8e1f"
)

MANIFEST_COMMITMENTS_V183 = (
    "78330499f94ad92281c9e27b92709e98716da41a003566f095eb4bb87dc73575",
    "5ee1ca1aec7b61f77f5702bf14ca4c0179a4006046a70a6d034d75b26e07b7e3",
    "16a699b37f95ad20deb39aae19eb3d54322d0a6ec7ec1d4641dd3f06bfb32931",
)
MANIFEST_ROLES = (
    "FRESH_OFFLINE_SOURCE",
    "FRESH_MATCHED_TARGET",
    "FRESH_INCOMPATIBLE_SCHEMA_OOD",
)
ARMS = ("REVALIDATED_RANKED_PROGRAM_PRIOR", "EMPTY_ARCHIVE_NO_PRIOR")
ACQUISITION_BLOCK_SIZE = 6
MINIMUM_TARGET_LABELS = 12
MAXIMUM_TARGET_LABELS = 24
STABLE_CONFIRMATION_BLOCKS = 2
REVALIDATED_PRIOR_CONFIRMATION_CREDIT = 1
OFFLINE_SOURCE_LABELS = 18
MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR = 20_000
RESOURCE_STEP_CAP = 512
MAXIMUM_LOOP_INCREMENT_REPETITIONS = 3
REGISTER_COUNT = 3
MAXIMUM_RESIDUAL_SUPPORT = 3
IID_OCCURRENCES_PER_ARM = 4
MAXIMUM_DECISIONS_PER_OCCURRENCE = 5
MAXIMUM_TARGET_GROUND_LABELS_PER_ARM = 2
PLANNING_HORIZON = 3

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v183.py",
    "src/acfqp/open_world_ranked_machine_v183.py",
    "src/acfqp/open_world_ranked_machine_planner_v183.py",
    "src/acfqp/open_world_ranked_machine_oracle_v183.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/phase3e_ids.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_ranked_machine_protocol_v183() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    payload = {
        "schema": "acfqp.open_world_ranked_machine_protocol.v183",
        "predecessor_campaign_id": predecessor.EXPECTED_CAMPAIGN_ID,
        "predecessor_verification_id": predecessor.EXPECTED_VERIFICATION_ID,
        "predecessor_preserved": True,
        "fresh_successor_identity_required": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V183),
        "manifest_roles": list(MANIFEST_ROLES),
        "arms": list(ARMS),
        "acquisition_block_size": ACQUISITION_BLOCK_SIZE,
        "minimum_target_labels": MINIMUM_TARGET_LABELS,
        "maximum_target_labels": MAXIMUM_TARGET_LABELS,
        "stable_confirmation_blocks": STABLE_CONFIRMATION_BLOCKS,
        "revalidated_prior_confirmation_credit": REVALIDATED_PRIOR_CONFIRMATION_CREDIT,
        "offline_source_labels": OFFLINE_SOURCE_LABELS,
        "maximum_enumeration_events_per_scalar": MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR,
        "resource_step_cap": RESOURCE_STEP_CAP,
        "maximum_loop_increment_repetitions": MAXIMUM_LOOP_INCREMENT_REPETITIONS,
        "register_count": REGISTER_COUNT,
        "maximum_residual_support": MAXIMUM_RESIDUAL_SUPPORT,
        "iid_occurrences_per_arm": IID_OCCURRENCES_PER_ARM,
        "maximum_decisions_per_occurrence": MAXIMUM_DECISIONS_PER_OCCURRENCE,
        "maximum_target_ground_labels_per_arm": MAXIMUM_TARGET_GROUND_LABELS_PER_ARM,
        "planning_horizon": PLANNING_HORIZON,
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "manifest_preimages_revealed": False,
        "source_or_target_outcomes_accessed": False,
        "candidate_admission_requires_structural_ranking_proof": True,
        "totality_for_all_finite_nonnegative_values_of_frozen_schema_required": True,
        "finite_carrier_totality_enumeration_forbidden": True,
        "general_program_termination_decided": False,
        "proof_system_complete_for_all_terminating_programs": False,
        "proof_language_program_length_unbounded": True,
        "current_occurrence_candidate_set_finite": True,
        "generic_ranked_program_schema_enumerated": True,
        "domain_specific_whole_program_template_used": False,
        "witness_blind_acquisition_policy_same_in_both_arms": True,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "archive_mdl_discount_forbidden": True,
        "prior_credit_requires_current_row_revalidation": True,
        "planner_consumes_only_ranked_total_compiled_model": True,
        "planning_horizon_greater_than_two": True,
        "target_ground_rows_require_preceding_certificate_failure": True,
        "compute_cap_failure_cannot_request_ground_label": True,
        "incompatible_schema_prior_rejected_before_target_query": True,
        "source_labels_target_labels_execution_steps_synthesis_planning_and_certificate_compute_separate": True,
        "partial_support_probability_authority_present": False,
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "total_work_dominance_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "protocol_id": domains.extension_content_id_v183(
            domains.CONSTRUCTION_K7_PROTOCOL_V183_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldRankedMachineProtocolV183:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V183 protocol is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_ranked_machine_protocol_v183() -> OpenWorldRankedMachineProtocolV183:
    document = build_open_world_ranked_machine_protocol_v183()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V183 protocol changed")
    return OpenWorldRankedMachineProtocolV183(
        _ISSUER,
        raw,
        document["protocol_id"],
    )


__all__ = (
    "ACQUISITION_BLOCK_SIZE",
    "ARMS",
    "EXPECTED_PROTOCOL_ID",
    "IID_OCCURRENCES_PER_ARM",
    "MANIFEST_COMMITMENTS_V183",
    "MAXIMUM_DECISIONS_PER_OCCURRENCE",
    "MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR",
    "MAXIMUM_LOOP_INCREMENT_REPETITIONS",
    "MAXIMUM_RESIDUAL_SUPPORT",
    "MAXIMUM_TARGET_GROUND_LABELS_PER_ARM",
    "MAXIMUM_TARGET_LABELS",
    "MINIMUM_TARGET_LABELS",
    "OFFLINE_SOURCE_LABELS",
    "PLANNING_HORIZON",
    "REGISTER_COUNT",
    "RESOURCE_STEP_CAP",
    "REVALIDATED_PRIOR_CONFIRMATION_CREDIT",
    "STABLE_CONFIRMATION_BLOCKS",
    "build_open_world_ranked_machine_protocol_v183",
    "freeze_open_world_ranked_machine_protocol_v183",
)
