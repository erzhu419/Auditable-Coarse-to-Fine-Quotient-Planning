"""Outcome-free one-shot execution registration for the V182r1 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v182r1 as domains
from acfqp import construction_k7_open_world_machine_manifest_reveal_v182r1 as reveal
from acfqp import construction_k7_open_world_machine_protocol_v182 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PREREGISTRATION_ID = (
    "2228546812cd10948b1972eaa61e9d58dfd2a6f97b3de4bb244d2be8f05cf9ef"
)
EXPECTED_CANONICAL_BYTE_COUNT = 3_253
EXPECTED_CANONICAL_SHA256 = (
    "aa5077232063003313a6b193789571d1502342b5450adfccb77569a17043f56c"
)

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v182.py",
    "src/acfqp/construction_k7_domain_registry_extension_v182r1.py",
    "src/acfqp/construction_k7_open_world_machine_protocol_v182.py",
    "src/acfqp/construction_k7_open_world_machine_manifest_reveal_v182r1.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/open_world_machine_planner_v182.py",
    "src/acfqp/open_world_machine_oracle_v182.py",
    "src/acfqp/construction_k7_open_world_machine_campaign_v182r1.py",
    "scripts/run_v182r1_open_world_machine_campaign.py",
    "src/acfqp/phase3e_ids.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_machine_execution_preregistration_v182r1() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    protocol_document = protocol.freeze_open_world_machine_protocol_v182().to_document()
    reveal_document = reveal.freeze_open_world_machine_manifest_reveal_v182r1().to_document()
    payload = {
        "schema": "acfqp.open_world_machine_execution_preregistration.v182r1",
        "protocol_id": protocol_document["protocol_id"],
        "manifest_reveal_id": reveal_document["manifest_reveal_id"],
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V182),
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_open_world_machine_campaign_v182r1:"
            "run_open_world_machine_campaign_v182r1"
        ),
        "output_root_relative_path": ".tmp/v182r1-open-world-machine-campaign",
        "output_root_must_be_absent": True,
        "campaign_output_must_be_absent": True,
        "failure_output_must_be_absent": True,
        "same_identity_rerun_after_any_progress_forbidden": True,
        "source_and_target_outcome_execution_started": False,
        "source_or_target_outcomes_accessed": False,
        "two_worker_cap": 2,
        "actual_worker_process_count": 0,
        "fresh_campaign_required": True,
        "producer_free_verification_required": True,
        "all_failed_predecessors_must_remain_preserved": True,
        "partial_campaign_cannot_unlock_any_gate": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "execution_preregistration_id": domains.extension_content_id_v182r1(
            domains.CONSTRUCTION_K7_EXECUTION_PREREGISTRATION_V182R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldMachineExecutionPreregistrationV182R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    execution_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V182r1 execution preregistration is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_machine_execution_preregistration_v182r1() -> OpenWorldMachineExecutionPreregistrationV182R1:
    document = build_open_world_machine_execution_preregistration_v182r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_PREREGISTRATION_ID != "0" * 64 and not (
        document["execution_preregistration_id"] == EXPECTED_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V182r1 execution preregistration changed")
    return OpenWorldMachineExecutionPreregistrationV182R1(
        _ISSUER,
        raw,
        document["execution_preregistration_id"],
    )


__all__ = (
    "EXPECTED_PREREGISTRATION_ID",
    "freeze_open_world_machine_execution_preregistration_v182r1",
)
