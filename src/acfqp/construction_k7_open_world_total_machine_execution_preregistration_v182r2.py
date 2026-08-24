"""Outcome-free one-shot execution registration for V182r2."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v182r2 as domains
from acfqp import construction_k7_open_world_total_machine_manifest_reveal_v182r2 as reveal
from acfqp import construction_k7_open_world_total_machine_protocol_v182r2 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PREREGISTRATION_ID = (
    "3015002e1ea1ac9eee5129ed13324b7e248bd62eeabcff059877269b4a90da9f"
)
EXPECTED_CANONICAL_BYTE_COUNT = 4_078
EXPECTED_CANONICAL_SHA256 = (
    "cdde1c10b0a0908c6c3df3e4911729f3b6e909d31693d0e4c98ad96a66ca8016"
)
FAILED_PREDECESSOR_FAILURE_ID = (
    "efa82614489dbe9b05ccd25a6d44022a96219df5b0ca5f8a139ec54e4bb805be"
)

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v182.py",
    "src/acfqp/construction_k7_domain_registry_extension_v182r1.py",
    "src/acfqp/construction_k7_domain_registry_extension_v182r2.py",
    "src/acfqp/construction_k7_open_world_total_machine_protocol_v182r2.py",
    "src/acfqp/construction_k7_open_world_total_machine_manifest_reveal_v182r2.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/open_world_machine_oracle_v182.py",
    "src/acfqp/open_world_total_machine_model_v182r2.py",
    "src/acfqp/open_world_total_machine_planner_v182r2.py",
    "src/acfqp/construction_k7_open_world_total_machine_campaign_v182r2.py",
    "src/acfqp/construction_k7_open_world_total_machine_campaign_independent_verifier_v182r2.py",
    "scripts/run_v182r2_open_world_total_machine_campaign.py",
    "src/acfqp/phase3e_ids.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_total_machine_execution_preregistration_v182r2() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    protocol_document = (
        protocol.freeze_open_world_total_machine_protocol_v182r2().to_document()
    )
    reveal_document = (
        reveal.freeze_open_world_total_machine_manifest_reveal_v182r2().to_document()
    )
    if protocol_document["failed_predecessor_failure_id"] != FAILED_PREDECESSOR_FAILURE_ID:
        raise ValueError("V182r2 failed-predecessor identity changed")
    payload = {
        "schema": "acfqp.open_world_total_machine_execution_preregistration.v182r2",
        "protocol_id": protocol_document["protocol_id"],
        "manifest_reveal_id": reveal_document["manifest_reveal_id"],
        "failed_predecessor_failure_id": FAILED_PREDECESSOR_FAILURE_ID,
        "failed_predecessor_output_must_remain_preserved": True,
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V182R2),
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_open_world_total_machine_campaign_v182r2:"
            "run_open_world_total_machine_campaign_v182r2"
        ),
        "output_root_relative_path": (
            ".tmp/v182r2-open-world-total-machine-campaign"
        ),
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
        "candidate_admission_requires_full_finite_carrier_totality": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "execution_preregistration_id": domains.extension_content_id_v182r2(
            domains.CONSTRUCTION_K7_EXECUTION_PREREGISTRATION_V182R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldTotalMachineExecutionPreregistrationV182R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    execution_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V182r2 execution preregistration is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_total_machine_execution_preregistration_v182r2() -> OpenWorldTotalMachineExecutionPreregistrationV182R2:
    document = build_open_world_total_machine_execution_preregistration_v182r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_PREREGISTRATION_ID != "0" * 64 and not (
        document["execution_preregistration_id"] == EXPECTED_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V182r2 execution preregistration changed")
    return OpenWorldTotalMachineExecutionPreregistrationV182R2(
        _ISSUER,
        raw,
        document["execution_preregistration_id"],
    )


__all__ = (
    "EXPECTED_PREREGISTRATION_ID",
    "FAILED_PREDECESSOR_FAILURE_ID",
    "build_open_world_total_machine_execution_preregistration_v182r2",
    "freeze_open_world_total_machine_execution_preregistration_v182r2",
)
