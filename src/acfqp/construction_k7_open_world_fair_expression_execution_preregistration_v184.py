"""Outcome-free one-shot execution registration for V184."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v184 as domains
from acfqp import construction_k7_open_world_fair_expression_manifest_reveal_v184 as reveal
from acfqp import construction_k7_open_world_fair_expression_protocol_v184 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PREREGISTRATION_ID = "0241b8146e23bfba1bc6adc39f5232b22894eb11af4fb40373f7aec126dd9496"
EXPECTED_CANONICAL_BYTE_COUNT = 4_108
EXPECTED_CANONICAL_SHA256 = "e1244d591369968487b3c91d6f9d44e0ab6a30b7d4d08a77cc4bba359d5e9308"

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v184.py",
    "src/acfqp/construction_k7_open_world_fair_expression_protocol_v184.py",
    "src/acfqp/construction_k7_open_world_fair_expression_manifest_reveal_v184.py",
    "src/acfqp/open_world_fair_expression_machine_v184.py",
    "src/acfqp/open_world_fair_expression_oracle_v184.py",
    "src/acfqp/construction_k7_open_world_fair_expression_campaign_v184.py",
    "src/acfqp/construction_k7_open_world_fair_expression_independent_verifier_v184.py",
    "src/acfqp/open_world_ranked_machine_v183.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/phase3e_ids.py",
    "scripts/run_v184_open_world_fair_expression_campaign.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_fair_expression_execution_preregistration_v184() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    protocol_document = protocol.freeze_open_world_fair_expression_protocol_v184().to_document()
    reveal_document = reveal.freeze_open_world_fair_expression_manifest_reveal_v184().to_document()
    payload = {
        "schema": "acfqp.open_world_fair_expression_execution_preregistration.v184",
        "protocol_id": protocol_document["protocol_id"],
        "manifest_reveal_id": reveal_document["manifest_reveal_id"],
        "predecessor_campaign_id": protocol_document["predecessor_campaign_id"],
        "predecessor_verification_id": protocol_document[
            "predecessor_verification_id"
        ],
        "predecessor_evidence_preserved": True,
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V184),
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_open_world_fair_expression_campaign_v184:"
            "run_open_world_fair_expression_campaign_v184"
        ),
        "output_root_relative_path": ".tmp/exact-freeze/v184_fair_expression_campaign",
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
        "countably_infinite_candidate_language_required": True,
        "finite_actual_search_prefix_required": True,
        "structural_totality_certificate_required": True,
        "resource_cap_exhaustion_is_not_infeasibility": True,
        "new_primitive_opcode_invention_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "execution_preregistration_id": domains.extension_content_id_v184(
            domains.CONSTRUCTION_K7_EXECUTION_PREREGISTRATION_V184_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldFairExpressionExecutionPreregistrationV184:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    execution_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V184 execution preregistration is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_fair_expression_execution_preregistration_v184() -> OpenWorldFairExpressionExecutionPreregistrationV184:
    document = build_open_world_fair_expression_execution_preregistration_v184()
    raw = canonical_json_bytes(document)
    if EXPECTED_PREREGISTRATION_ID != "0" * 64 and not (
        document["execution_preregistration_id"] == EXPECTED_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V184 execution preregistration changed")
    return OpenWorldFairExpressionExecutionPreregistrationV184(
        _ISSUER,
        raw,
        document["execution_preregistration_id"],
    )


__all__ = (
    "EXPECTED_PREREGISTRATION_ID",
    "build_open_world_fair_expression_execution_preregistration_v184",
    "freeze_open_world_fair_expression_execution_preregistration_v184",
)
