"""Outcome-free protocol for the fresh V182r2 total-machine campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v182r2 as domains
from acfqp import construction_k7_open_world_machine_failure_freeze_v182r1 as predecessor
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PROTOCOL_ID = (
    "edd9f3626ce08600f4d1c6e0eb906675439cc2dbb45b0416f7c21d93168ae063"
)
EXPECTED_CANONICAL_BYTE_COUNT = 4_333
EXPECTED_CANONICAL_SHA256 = (
    "fedfd450ba8c9b6f48530b3a8735b6fe08494bf335fdf0d3fac1c58d1f315646"
)

MANIFEST_COMMITMENTS_V182R2 = (
    "7e129e5db7be03c8aab24d21a7e8a11dd9c39e4d1135ab3b5e20981ffeb6b9d5",
    "1e2e5ce866337113efa8c6d44d9c4f3ff1bcd7e412d5c754fdb50d20288a1776",
    "a5902469c682f7390180c0c5cb96d14c1eb537259d923504b900725e9446cd16",
)
MANIFEST_ROLES = (
    "FRESH_OFFLINE_SOURCE",
    "FRESH_MATCHED_TARGET",
    "FRESH_INCOMPATIBLE_SCHEMA_OOD",
)
ARMS = ("REVALIDATED_TOTAL_MACHINE_PRIOR", "EMPTY_ARCHIVE_NO_PRIOR")
ACQUISITION_BLOCK_SIZE = 6
ACQUISITION_REPEAT_COUNT = 2
MINIMUM_TARGET_LABELS = 12
MAXIMUM_TARGET_LABELS = 30
STABLE_CONFIRMATION_BLOCKS = 2
REVALIDATED_PRIOR_CONFIRMATION_CREDIT = 1
OFFLINE_SOURCE_LABELS = 18
MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR = 5_000
MAXIMUM_INSTRUCTION_COUNT = 3
MAXIMUM_EXECUTION_STEPS = 32
REGISTER_COUNT = 2
MAXIMUM_RESIDUAL_SUPPORT = 3
IID_OCCURRENCES_PER_ARM = 6
MAXIMUM_DECISIONS_PER_OCCURRENCE = 9
MAXIMUM_TARGET_GROUND_LABELS_PER_ARM = 6

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v182.py",
    "src/acfqp/construction_k7_domain_registry_extension_v182r1.py",
    "src/acfqp/construction_k7_domain_registry_extension_v182r2.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/open_world_machine_oracle_v182.py",
    "src/acfqp/open_world_total_machine_model_v182r2.py",
    "src/acfqp/open_world_total_machine_planner_v182r2.py",
    "src/acfqp/construction_k7_open_world_machine_failure_freeze_v182r1.py",
    "src/acfqp/phase3e_ids.py",
)


def _source_fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_total_machine_protocol_v182r2() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    payload = {
        "schema": "acfqp.open_world_total_machine_protocol.v182r2",
        "failed_predecessor_execution_preregistration_id": (
            "2228546812cd10948b1972eaa61e9d58dfd2a6f97b3de4bb244d2be8f05cf9ef"
        ),
        "failed_predecessor_failure_id": predecessor.EXPECTED_FAILURE_ID,
        "failed_predecessor_preserved_and_same_identity_rerun_forbidden": True,
        "fresh_successor_identity_required": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V182R2),
        "manifest_roles": list(MANIFEST_ROLES),
        "arms": list(ARMS),
        "acquisition_block_size": ACQUISITION_BLOCK_SIZE,
        "acquisition_repeat_count": ACQUISITION_REPEAT_COUNT,
        "minimum_target_labels": MINIMUM_TARGET_LABELS,
        "maximum_target_labels": MAXIMUM_TARGET_LABELS,
        "stable_confirmation_blocks": STABLE_CONFIRMATION_BLOCKS,
        "revalidated_prior_confirmation_credit": (
            REVALIDATED_PRIOR_CONFIRMATION_CREDIT
        ),
        "offline_source_labels": OFFLINE_SOURCE_LABELS,
        "maximum_enumeration_events_per_scalar": (
            MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR
        ),
        "maximum_instruction_count": MAXIMUM_INSTRUCTION_COUNT,
        "maximum_execution_steps": MAXIMUM_EXECUTION_STEPS,
        "register_count": REGISTER_COUNT,
        "maximum_residual_support": MAXIMUM_RESIDUAL_SUPPORT,
        "iid_occurrences_per_arm": IID_OCCURRENCES_PER_ARM,
        "maximum_decisions_per_occurrence": MAXIMUM_DECISIONS_PER_OCCURRENCE,
        "maximum_target_ground_labels_per_arm": (
            MAXIMUM_TARGET_GROUND_LABELS_PER_ARM
        ),
        "source_facts": [_source_fact(root, path) for path in _SOURCE_PATHS],
        "source_and_target_manifest_preimages_revealed": False,
        "source_or_target_transition_outcomes_accessed": False,
        "program_language": "UNBOUNDED_COUNTER_MACHINE_DESCRIPTION",
        "candidate_admission_requires_full_finite_carrier_totality": True,
        "full_finite_carrier_totality_is_not_unbounded_totality": True,
        "finite_candidate_program_catalog_used": False,
        "named_domain_family_used": False,
        "named_layout_used": False,
        "whole_program_template_used": False,
        "search_resource_bounded_per_occurrence": True,
        "witness_blind_acquisition_policy_same_in_both_arms": True,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "archive_mdl_discount_forbidden": True,
        "prior_credit_requires_current_row_revalidation": True,
        "planner_must_consume_only_totality_checked_compiled_model": True,
        "target_ground_rows_require_preceding_certificate_failure": True,
        "incompatible_schema_prior_rejected_before_target_query": True,
        "source_labels_target_labels_execution_steps_synthesis_planning_and_certificate_compute_separate": True,
        "partial_support_only_probability_authority_absent": True,
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
        "protocol_id": domains.extension_content_id_v182r2(
            domains.CONSTRUCTION_K7_PROTOCOL_V182R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldTotalMachineProtocolV182R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V182r2 protocol is not one canonical object")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_total_machine_protocol_v182r2() -> OpenWorldTotalMachineProtocolV182R2:
    document = build_open_world_total_machine_protocol_v182r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V182r2 protocol changed")
    return OpenWorldTotalMachineProtocolV182R2(
        _ISSUER,
        raw,
        document["protocol_id"],
    )


__all__ = (
    "ACQUISITION_BLOCK_SIZE",
    "ACQUISITION_REPEAT_COUNT",
    "ARMS",
    "EXPECTED_PROTOCOL_ID",
    "IID_OCCURRENCES_PER_ARM",
    "MANIFEST_COMMITMENTS_V182R2",
    "MAXIMUM_DECISIONS_PER_OCCURRENCE",
    "MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR",
    "MAXIMUM_EXECUTION_STEPS",
    "MAXIMUM_INSTRUCTION_COUNT",
    "MAXIMUM_RESIDUAL_SUPPORT",
    "MAXIMUM_TARGET_GROUND_LABELS_PER_ARM",
    "MAXIMUM_TARGET_LABELS",
    "MINIMUM_TARGET_LABELS",
    "OFFLINE_SOURCE_LABELS",
    "REGISTER_COUNT",
    "REVALIDATED_PRIOR_CONFIRMATION_CREDIT",
    "STABLE_CONFIRMATION_BLOCKS",
    "build_open_world_total_machine_protocol_v182r2",
    "freeze_open_world_total_machine_protocol_v182r2",
)
