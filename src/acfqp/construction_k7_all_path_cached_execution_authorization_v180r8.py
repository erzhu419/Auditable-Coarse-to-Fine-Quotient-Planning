"""Outcome-free authorization for one fresh durable-cache occurrence."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r8 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = (
    "977f86ccbcef45b6117479ac63866bed57671764f23e4c8c391415a4b15349e3"
)
EXPECTED_CANONICAL_BYTE_COUNT = 9_422
EXPECTED_CANONICAL_SHA256 = (
    "3d150a049bd2b1e439bc5c25222592282a253652c5b63a03eac748d37d55a9e0"
)

LOGICAL_OCCURRENCE_ID = (
    "993a7c92fcb5e6b24f468a9411478f6b1c746b177ee917894f3750eb5d444ece"
)
SELECTED_PLAN_ID = (
    "46005036b53a71b09d793330f8213ad0f723a4d9b317406fd5d10b8541e6559a"
)
QUERY_ORDINAL = 8
WORKING_BYTES_HARD_CAP = 2 * 1024 * 1024 * 1024
EXPECTED_DURABLE_PROOF_BYTE_COUNT = 37_591
EXPECTED_DURABLE_PROOF_SHA256 = (
    "d795e6cdca04070632912c0f9cfe0a2e49f14710020fb2481c5a43aa892ed1ca"
)
EXPECTED_DURABLE_PROOF_ID = (
    "9f682a2c1b6e9ce1e697b9910e01b41180353eae24a9d5f720e071b802b6a6c8"
)

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_cached_exact_infeasibility_production_terminal_finalizer_v180r8.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r8.py",
    "src/acfqp/construction_k7_all_path_formalization_contract_v180.py",
    "src/acfqp/construction_k7_all_path_production_execution_protocol_v180r3.py",
    "src/acfqp/construction_accounting_registry_v9.py",
    "src/acfqp/accounting_v1.py",
    "src/acfqp/actual_accounting_v1.py",
    "src/acfqp/phase3e_exact_infeasibility_durable_proof_v1.py",
    "src/acfqp/phase3e_ids.py",
    "scripts/run_v180r8_cached_exact_infeasibility_occurrence.py",
)
_PROOF_ROOT = "artifacts/phase05/g2048"


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _proof_source_facts(root: Path) -> list[dict[str, Any]]:
    proof_root = root / _PROOF_ROOT
    return [
        _fact(root, path.relative_to(root).as_posix())
        for path in sorted(item for item in proof_root.rglob("*") if item.is_file())
    ]


def build_cached_execution_authorization_v180r8() -> dict[str, Any]:
    repository_root = Path(__file__).resolve().parents[2]
    frozen = protocol.freeze_all_path_production_execution_protocol_v180r3()
    slots = [
        row
        for row in frozen.to_document()["production_execution_slots"]
        if row["terminal_code"] == "CACHED_EXACT_INFEASIBLE"
    ]
    if len(slots) != 1:
        raise ValueError("V180r8 cached execution slot changed")
    payload = {
        "schema": "acfqp.cached_exact_infeasibility_execution_authorization.v180r8",
        "production_execution_protocol_id": frozen.production_execution_protocol_id,
        "production_execution_slot": slots[0],
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "selected_plan_id": SELECTED_PLAN_ID,
        "query_ordinal": QUERY_ORDINAL,
        "working_bytes_hard_cap": WORKING_BYTES_HARD_CAP,
        "source_facts": [_fact(repository_root, path) for path in _SOURCE_PATHS],
        "proof_source_root": _PROOF_ROOT,
        "proof_source_facts": _proof_source_facts(repository_root),
        "expected_durable_proof_byte_count": EXPECTED_DURABLE_PROOF_BYTE_COUNT,
        "expected_durable_proof_sha256": EXPECTED_DURABLE_PROOF_SHA256,
        "expected_durable_proof_id": EXPECTED_DURABLE_PROOF_ID,
        "entrypoint": (
            "acfqp.construction_k7_cached_exact_infeasibility_production_terminal_finalizer_v180r8:"
            "run_cached_exact_infeasibility_production_occurrence_v180r8"
        ),
        "proof_production_must_precede_online_measurement_window": True,
        "proof_source_must_be_the_frozen_phase05_g2048_bundle": True,
        "independent_durable_proof_replay_required": True,
        "fresh_plan_binding_required": True,
        "ground_solver_forbidden_in_online_window": True,
        "planner_forbidden_in_online_window": True,
        "proof_producer_forbidden_in_online_window": True,
        "all_269_v9_counter_paths_require_explicit_records": True,
        "all_nine_shared_resource_paths_require_source_closed_receipts": True,
        "historical_summary_to_counter_translation_forbidden": True,
        "proof_output_must_be_absent_before_execution": True,
        "terminal_output_must_be_absent_before_execution": True,
        "failure_output_must_be_absent_before_execution": True,
        "same_authorization_rerun_after_any_progress_forbidden": True,
        "fresh_cached_execution_started": False,
        "production_outcome_accessed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "cached_execution_authorization_id": domains.extension_content_id_v180r8(
            domains.CONSTRUCTION_K7_CACHED_EXECUTION_AUTHORIZATION_V180R8_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CachedExecutionAuthorizationV180r8:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            raise ValueError("V180r8 authorization is not issuer-created")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r8 authorization is not one canonical object")
        return document


@lru_cache(maxsize=1)
def freeze_cached_execution_authorization_v180r8() -> CachedExecutionAuthorizationV180r8:
    document = build_cached_execution_authorization_v180r8()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["cached_execution_authorization_id"] == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r8 cached execution authorization changed")
    return CachedExecutionAuthorizationV180r8(
        _ISSUER,
        raw,
        document["cached_execution_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "LOGICAL_OCCURRENCE_ID",
    "SELECTED_PLAN_ID",
    "QUERY_ORDINAL",
    "WORKING_BYTES_HARD_CAP",
    "freeze_cached_execution_authorization_v180r8",
)
