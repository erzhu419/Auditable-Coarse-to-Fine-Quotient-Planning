"""Final V181r1 runner/source freeze before any raw transition query."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r1 as domains
from acfqp import construction_k7_open_world_manifest_reveals_v181r1 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r1 as successor
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SOURCE_FILENAMES = (
    "construction_k7_domain_registry_extension_v181.py",
    "construction_k7_open_world_preregistration_v181.py",
    "open_world_universal_synthesizer_v181.py",
    "open_world_transition_oracle_v181.py",
    "open_world_compiled_model_v181.py",
    "construction_k7_domain_registry_extension_v181r1.py",
    "construction_k7_open_world_protocol_successor_v181r1.py",
    "construction_k7_open_world_manifest_reveals_v181r1.py",
    "construction_k7_open_world_campaign_v181r1.py",
)
EXPECTED_EXECUTION_PREREGISTRATION_ID = (
    "eba05c4d67ecb4506a510ded4cd42dca47fd9c896773e774b1d1f49e049ee736"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_345
EXPECTED_CANONICAL_SHA256 = (
    "88b1c1091f2eb854e56861845f3540b215a2e27a933edb27de5cae159cce0835"
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


def build_open_world_execution_preregistration_v181r1() -> dict[str, Any]:
    successor_value = successor.freeze_open_world_protocol_successor_v181r1()
    reveal_value = reveals.freeze_open_world_manifest_reveals_v181r1()
    payload = {
        "schema": "acfqp.open_world_execution_preregistration.v181r1",
        "protocol_successor_id": successor_value.protocol_successor_id,
        "manifest_reveal_id": reveal_value.manifest_reveal_id,
        "frozen_source_facts": _source_facts(),
        "manifest_reveals_accessed": True,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "runner_frozen_before_target_outcome_access": True,
        "same_runner_for_both_arms": True,
        "only_arm_switch": "REUSABLE_SUBPROGRAM_ARCHIVE_AVAILABLE",
        "source_generation_witness_passed_to_runner": False,
        "maximum_simultaneous_worker_count": 2,
        "target_episode_denominator": 72,
        "failure_under_this_identity_must_be_retained": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "execution_preregistration_id": domains.extension_content_id_v181r1(
            domains.CONSTRUCTION_K7_EXECUTION_PREREGISTRATION_V181R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldExecutionPreregistrationV181R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    execution_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_execution_preregistration_v181r1() -> OpenWorldExecutionPreregistrationV181R1:
    document = build_open_world_execution_preregistration_v181r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_EXECUTION_PREREGISTRATION_ID != "0" * 64 and not (
        document["execution_preregistration_id"]
        == EXPECTED_EXECUTION_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r1 frozen execution preregistration changed")
    return OpenWorldExecutionPreregistrationV181R1(
        _ISSUER,
        raw,
        document["execution_preregistration_id"],
    )


__all__ = (
    "EXPECTED_EXECUTION_PREREGISTRATION_ID",
    "freeze_open_world_execution_preregistration_v181r1",
)
