"""Outcome-free authorization for one V180r12r1 production aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v180r12r1 as domains
from acfqp import construction_k7_ten_terminal_aggregation_protocol_v180r12r1 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = "cf1158297e790cfd5a794adbd2abc98819ff0f7ce736a4859a9795938ef1672f"
EXPECTED_CANONICAL_BYTE_COUNT = 6_041
EXPECTED_CANONICAL_SHA256 = "11f89eb57dfdb7e3e480fae93cf195f5ef7a30ec43b1751e59bfc7d3e38b2f83"
LOGICAL_OCCURRENCE_ID = "8a2df3b6c5d43fc73e56b11dc937ed6d3c63df71de168911865624f9ec084610"
WORKING_BYTES_HARD_CAP = 4 * 1024 * 1024 * 1024

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r1.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r1e.py",
    "src/acfqp/construction_k7_ten_terminal_aggregation_protocol_v180r12r1.py",
    "src/acfqp/construction_k7_ten_terminal_aggregation_finalizer_v180r12r1.py",
    "src/acfqp/construction_k7_ten_terminal_aggregation_independent_verifier_v180r12r1.py",
    "src/acfqp/construction_accounting_registry_v9.py",
    "src/acfqp/accounting_v1.py",
    "src/acfqp/actual_accounting_v1.py",
    "src/acfqp/phase3e_ids.py",
    "src/acfqp/construction_k7_remaining_terminal_execution_authorization_v180r9.py",
    "src/acfqp/construction_k7_remaining_terminal_independent_verifier_v180r9.py",
    "src/acfqp/construction_k7_v34_retained_recovery_authorization_v180r11.py",
    "src/acfqp/construction_k7_v34_retained_recovery_independent_verifier_v180r11.py",
    "src/acfqp/construction_k7_all_path_v36_resource_successor_authorization_v180r10.py",
    "src/acfqp/construction_k7_v36_local_recovery_resource_successor_independent_verifier_v180r10.py",
    "src/acfqp/construction_k7_all_path_fallback_execution_authorization_v180r7.py",
    "src/acfqp/construction_k7_full_ground_fallback_production_terminal_independent_verifier_v180r7.py",
    "src/acfqp/construction_k7_all_path_cached_execution_authorization_v180r8.py",
    "src/acfqp/construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8.py",
    "scripts/run_v180r12r1_ten_terminal_aggregation.py",
)

_INPUTS = (
    ("V180R11_RETAINED_V34_FINISH_FORWARD", ".tmp/exact-freeze/v180r11_v34_retained_terminal.json", ".tmp/exact-freeze/v180r11_v34_retained_verification.json"),
    ("V180R10_FRESH_V36_RESOURCE_SUCCESSOR", ".tmp/exact-freeze/v180r10_v36_resource_successor_terminal.json", ".tmp/exact-freeze/v180r10_v36_resource_successor_verification.json"),
    ("V180R7_FRESH_FULL_GROUND_FALLBACK", ".tmp/exact-freeze/v180r7_full_ground_fallback_terminal_bundle.json", ".tmp/exact-freeze/v180r7_full_ground_fallback_verification.json"),
    ("V180R8_FRESH_CACHED_EXACT", ".tmp/v180r8-cached-exact-production/TERMINAL.json", ".tmp/v180r8-cached-exact-verification/VERIFICATION.json"),
    ("V180R9_FRESH_SIX_TERMINAL_CAMPAIGN", ".tmp/exact-freeze/v180r9_remaining_terminal_production/TERMINAL.json", ".tmp/exact-freeze/v180r9_remaining_terminal_production/VERIFICATION.json"),
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_ten_terminal_aggregation_execution_authorization_v180r12r1() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    frozen = protocol.freeze_ten_terminal_aggregation_protocol_v180r12r1()
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_execution_authorization.v180r12r1",
        "aggregation_protocol_id": frozen.aggregation_protocol_id,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "input_roles": [
            {
                "source_kind": source_kind,
                "terminal_relative_path": terminal_path,
                "verification_relative_path": verification_path,
            }
            for source_kind, terminal_path, verification_path in _INPUTS
        ],
        "source_group_count": len(_INPUTS),
        "terminal_code_count": 10,
        "working_bytes_hard_cap": WORKING_BYTES_HARD_CAP,
        "maximum_worker_processes": 1,
        "all_source_independent_verifiers_must_replay": True,
        "counter_record_work_vector_comparison_vector_chain_required_per_terminal": True,
        "nine_shared_resource_receipts_required_per_terminal": True,
        "campaign_orchestration_v9_chain_required": True,
        "output_bytes_fixed_point_required": True,
        "producer_free_aggregate_reconstruction_required": True,
        "same_authorization_rerun_after_progress_or_terminal_forbidden": True,
        "source_outcomes_accessed_by_authorization": False,
        "aggregation_execution_started": False,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "execution_authorization_id": domains.extension_content_id_v180r12r1(
            domains.CONSTRUCTION_K7_EXECUTION_AUTHORIZATION_V180R12R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationExecutionAuthorizationV180R12R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:
            raise ValueError("V180r12r1 authorization is not canonical")
        return value


@lru_cache(maxsize=1)
def freeze_ten_terminal_aggregation_execution_authorization_v180r12r1() -> (
    TenTerminalAggregationExecutionAuthorizationV180R12R1
):
    document = build_ten_terminal_aggregation_execution_authorization_v180r12r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["execution_authorization_id"] == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r12r1 execution authorization changed")
    return TenTerminalAggregationExecutionAuthorizationV180R12R1(
        _ISSUER,
        raw,
        document["execution_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "LOGICAL_OCCURRENCE_ID",
    "WORKING_BYTES_HARD_CAP",
    "freeze_ten_terminal_aggregation_execution_authorization_v180r12r1",
)
