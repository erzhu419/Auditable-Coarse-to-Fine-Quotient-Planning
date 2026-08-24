"""Outcome-free protocol for the fresh V182 universal-machine campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v182 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PROTOCOL_ID = (
    "33a481538f9cd1b437494607ae1058982fd03976c921dbf30666e831a39f25ba"
)
EXPECTED_CANONICAL_BYTE_COUNT = 3_126
EXPECTED_CANONICAL_SHA256 = (
    "6de08191d4618d08b429c64c023d93f99750a868c0575197c744b8564d20d71d"
)

MANIFEST_COMMITMENTS_V182 = (
    "7a401b5c9840e0b611e8944452a1edbca343015810e9956cb070fb8f783053b7",
    "0d6dd9be3e5bd79dc9d9d3119d52c41b7fcfe9a85526916ef3a225fd6ec7afa0",
    "6c5f276967b12e518176b08d95e6a28ee3b3834aa5dcf21846b154643cfe2459",
)
MANIFEST_ROLES = (
    "OFFLINE_SOURCE",
    "FRESH_MATCHED_TARGET",
    "INCOMPATIBLE_SCHEMA_OOD",
)
ARMS = ("REVALIDATED_MACHINE_PRIOR", "EMPTY_ARCHIVE_NO_PRIOR")
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
MAXIMUM_DECISIONS_PER_OCCURRENCE = 8
MAXIMUM_TARGET_GROUND_LABELS_PER_ARM = 6

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v182.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/open_world_machine_planner_v182.py",
    "src/acfqp/open_world_machine_oracle_v182.py",
    "src/acfqp/phase3e_ids.py",
)


def _source_fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_machine_protocol_v182() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    payload = {
        "schema": "acfqp.open_world_machine_protocol.v182",
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V182),
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
        "finite_candidate_program_catalog_used": False,
        "named_domain_family_used": False,
        "named_layout_used": False,
        "whole_program_template_used": False,
        "search_resource_bounded_per_occurrence": True,
        "witness_blind_acquisition_policy_same_in_both_arms": True,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "archive_mdl_discount_forbidden": True,
        "prior_credit_requires_current-row_revalidation": True,
        "planner_must_consume_only_compiled_model": True,
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
        "protocol_id": domains.extension_content_id_v182(
            domains.CONSTRUCTION_K7_PREREGISTRATION_V182_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldMachineProtocolV182:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V182 protocol is not one canonical object")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_machine_protocol_v182() -> OpenWorldMachineProtocolV182:
    document = build_open_world_machine_protocol_v182()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V182 protocol changed")
    return OpenWorldMachineProtocolV182(
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
    "MANIFEST_COMMITMENTS_V182",
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
    "freeze_open_world_machine_protocol_v182",
)
