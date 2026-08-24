"""Final V181r2 source/runner freeze before any fresh oracle query."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r2 as domains
from acfqp import construction_k7_open_world_manifest_reveals_v181r2 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r2 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SOURCE_FILENAMES = (
    "construction_k7_domain_registry_extension_v181.py",
    "open_world_transition_oracle_v181.py",
    "open_world_universal_synthesizer_v181.py",
    "construction_k7_domain_registry_extension_v181r2.py",
    "open_world_universal_synthesizer_v181r2.py",
    "open_world_compiled_model_v181r2.py",
    "construction_k7_open_world_protocol_successor_v181r2.py",
    "construction_k7_open_world_manifest_reveals_v181r2.py",
    "construction_k7_open_world_campaign_v181r2.py",
)
EXPECTED_EXECUTION_PREREGISTRATION_ID = (
    "cfd7076d7a5c93c403ad64e0d39e88d3918f28c6e92924a86fef5fa0148f4a2b"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_755
EXPECTED_CANONICAL_SHA256 = (
    "26bb4b1e881161a8f43c35340e474a51bdac03f41a5b3118cf4165accafaf1ad"
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


def build_open_world_execution_preregistration_v181r2() -> dict[str, Any]:
    successor = protocol.freeze_open_world_protocol_successor_v181r2()
    reveal = reveals.freeze_open_world_manifest_reveals_v181r2()
    payload = {
        "schema": "acfqp.open_world_execution_preregistration.v181r2",
        "protocol_successor_id": successor.protocol_successor_id,
        "manifest_reveal_id": reveal.manifest_reveal_id,
        "preserved_v181r1_failure_id": protocol.PRESERVED_V181R1_FAILURE_ID,
        "frozen_source_facts": _source_facts(),
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "runner_frozen_before_target_outcome_access": True,
        "same_runner_for_both_arms": True,
        "only_arm_switch": "REUSABLE_SUBPROGRAM_ARCHIVE_AVAILABLE",
        "query_block_size": 16,
        "same_input_repeat_count": 2,
        "minimum_source_labels": 32,
        "maximum_source_labels": 512,
        "stable_confirmation_blocks": 2,
        "maximum_enumeration_events_per_expression": 2_000_000,
        "resource_cap_increased_relative_to_v181r1": False,
        "durable_checkpoint_after_every_acquisition_block": True,
        "durable_checkpoint_after_every_arm_and_distribution": True,
        "failure_references_last_durable_checkpoint": True,
        "target_episode_denominator": 72,
        "maximum_simultaneous_worker_count": 2,
        "same_identity_rerun_after_failure_forbidden": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "execution_preregistration_id": domains.extension_content_id_v181r2(
            domains.CONSTRUCTION_K7_EXECUTION_PREREGISTRATION_V181R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldExecutionPreregistrationV181R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    execution_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_execution_preregistration_v181r2() -> OpenWorldExecutionPreregistrationV181R2:
    document = build_open_world_execution_preregistration_v181r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_EXECUTION_PREREGISTRATION_ID != "0" * 64 and not (
        document["execution_preregistration_id"]
        == EXPECTED_EXECUTION_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r2 frozen execution preregistration changed")
    return OpenWorldExecutionPreregistrationV181R2(
        _ISSUER,
        raw,
        document["execution_preregistration_id"],
    )


__all__ = (
    "EXPECTED_EXECUTION_PREREGISTRATION_ID",
    "freeze_open_world_execution_preregistration_v181r2",
)
