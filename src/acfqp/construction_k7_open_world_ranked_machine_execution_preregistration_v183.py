"""Outcome-free one-shot execution registration for V183."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v183 as domains
from acfqp import construction_k7_open_world_ranked_machine_manifest_reveal_v183 as reveal
from acfqp import construction_k7_open_world_ranked_machine_protocol_v183 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PREREGISTRATION_ID = "b22da9ff517fc4f9cb814b161ce47ecdce9e671fe2c72c08a8614dd3293f3e27"
EXPECTED_CANONICAL_BYTE_COUNT = 3764
EXPECTED_CANONICAL_SHA256 = "6607141ee49ffe2dd037fba900cc57e58f095690f9929097677e4dfa6755778f"

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v183.py",
    "src/acfqp/construction_k7_open_world_ranked_machine_protocol_v183.py",
    "src/acfqp/construction_k7_open_world_ranked_machine_manifest_reveal_v183.py",
    "src/acfqp/open_world_ranked_machine_v183.py",
    "src/acfqp/open_world_ranked_machine_planner_v183.py",
    "src/acfqp/open_world_ranked_machine_oracle_v183.py",
    "src/acfqp/construction_k7_open_world_ranked_machine_campaign_v183.py",
    "src/acfqp/construction_k7_open_world_ranked_machine_independent_verifier_v183.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/phase3e_ids.py",
    "scripts/run_v183_open_world_ranked_machine_campaign.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_ranked_machine_execution_preregistration_v183() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    protocol_document = protocol.freeze_open_world_ranked_machine_protocol_v183().to_document()
    reveal_document = reveal.freeze_open_world_ranked_machine_manifest_reveal_v183().to_document()
    payload = {
        "schema": "acfqp.open_world_ranked_machine_execution_preregistration.v183",
        "protocol_id": protocol_document["protocol_id"],
        "manifest_reveal_id": reveal_document["manifest_reveal_id"],
        "predecessor_campaign_id": protocol_document["predecessor_campaign_id"],
        "predecessor_verification_id": protocol_document["predecessor_verification_id"],
        "predecessor_evidence_preserved": True,
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V183),
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_open_world_ranked_machine_campaign_v183:"
            "run_open_world_ranked_machine_campaign_v183"
        ),
        "output_root_relative_path": ".tmp/exact-freeze/v183_ranked_machine_campaign",
        "output_root_must_be_absent": True,
        "campaign_output_must_be_absent": True,
        "verification_output_must_be_absent": True,
        "failure_output_must_be_absent": True,
        "same_identity_rerun_after_any_progress_forbidden": True,
        "source_or_target_execution_started": False,
        "source_or_target_outcomes_accessed": False,
        "actual_worker_process_count": 0,
        "producer_free_reconstruction_required": True,
        "partial_campaign_cannot_unlock_any_gate": True,
        "candidate_admission_requires_structural_ranking_proof": True,
        "finite_carrier_totality_enumeration_forbidden": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "execution_preregistration_id": domains.extension_content_id_v183(
            domains.CONSTRUCTION_K7_EXECUTION_PREREGISTRATION_V183_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldRankedMachineExecutionPreregistrationV183:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    execution_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V183 execution preregistration is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_ranked_machine_execution_preregistration_v183() -> OpenWorldRankedMachineExecutionPreregistrationV183:
    document = build_open_world_ranked_machine_execution_preregistration_v183()
    raw = canonical_json_bytes(document)
    if EXPECTED_PREREGISTRATION_ID != "0" * 64 and not (
        document["execution_preregistration_id"] == EXPECTED_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V183 execution preregistration changed")
    return OpenWorldRankedMachineExecutionPreregistrationV183(
        _ISSUER,
        raw,
        document["execution_preregistration_id"],
    )


__all__ = (
    "EXPECTED_PREREGISTRATION_ID",
    "build_open_world_ranked_machine_execution_preregistration_v183",
    "freeze_open_world_ranked_machine_execution_preregistration_v183",
)
