"""Outcome-free authorization for one fresh full-ground-fallback occurrence."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r7 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = (
    "445851c4b3ceb25be1858e0c4c07e436631486efe12853db8fef4fdf9c5573e9"
)
EXPECTED_CANONICAL_BYTE_COUNT = 5_935
EXPECTED_CANONICAL_SHA256 = (
    "f9fd4b872b54548ccc25515728159d0352de5071f96f787bda35f98cb6933690"
)
LOGICAL_OCCURRENCE_ID = (
    "58e734a75fae219a40ada5077a4aca568ef5304ad12275a776f788d1ddb31bbb"
)
QUERY_ORDINAL = 7
EXPECTED_BINDING_BYTE_COUNT = 4_405
EXPECTED_BINDING_SHA256 = (
    "bf5d7f5292a4b38136b141745b9349bc4e86c2ab7e67592e8d25c19b5daa527f"
)
EXPECTED_SNAPSHOT_BYTE_COUNT = 388_638
EXPECTED_SNAPSHOT_SHA256 = (
    "18056b6f1aba853cb3b705041be93bce31700c79d45fa894fd956b144f0e7823"
)
EXPECTED_TRANSITION_BYTE_COUNT = 859_154
EXPECTED_TRANSITION_SHA256 = (
    "e2278f8b499b13f45ab1c8fcba29be9665d472d4cd9ab65e1ee124187bfbbe30"
)

_SOURCE_NAMES = (
    "construction_k7_full_ground_fallback_production_terminal_finalizer_v180r7.py",
    "construction_k7_recovery_eligible_occurrence_accounting_v1.py",
    "construction_k7_recovery_eligible_supervised_executor_v1.py",
    "construction_k7_recovery_eligible_stage_accounting_v1.py",
    "construction_output_bytes_fixed_point_v1.py",
    "construction_shared_resource_receipts_v1.py",
    "construction_accounting_registry_v6.py",
    "construction_accounting_registry_v9.py",
    "construction_k7_all_path_production_execution_protocol_v180r3.py",
    "construction_k7_domain_registry_extension_v180r7.py",
)
_INPUT_SPECS = (
    (
        ".tmp/recovery-eligible-retained-v1/SOURCE_BUNDLE_BINDING.json",
        EXPECTED_BINDING_BYTE_COUNT,
        EXPECTED_BINDING_SHA256,
    ),
    (
        ".tmp/recovery-eligible-retained-v1/REUSABLE_RAPM_SNAPSHOT.json",
        EXPECTED_SNAPSHOT_BYTE_COUNT,
        EXPECTED_SNAPSHOT_SHA256,
    ),
    (
        ".tmp/recovery-eligible-retained-v1/PROOF_DEPENDENCY_TRANSITION.json",
        EXPECTED_TRANSITION_BYTE_COUNT,
        EXPECTED_TRANSITION_SHA256,
    ),
)


def _source_fact(filename: str) -> dict[str, Any]:
    raw = (Path(__file__).resolve().parent / filename).read_bytes()
    return {
        "filename": filename,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _input_fact(
    relative_path: str, expected_bytes: int, expected_sha256: str
) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    raw = (root / relative_path).read_bytes()
    fact = {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if fact["byte_count"] != expected_bytes or fact["sha256"] != expected_sha256:
        raise ValueError("V180r7 retained predecessor input changed")
    return fact


def build_fallback_execution_authorization_v180r7() -> dict[str, Any]:
    frozen = protocol.freeze_all_path_production_execution_protocol_v180r3()
    slot = next(
        row
        for row in frozen.to_document()["production_execution_slots"]
        if row["terminal_code"] == "FULL_GROUND_FALLBACK"
    )
    payload = {
        "schema": "acfqp.full_ground_fallback_execution_authorization.v180r7",
        "production_execution_protocol_id": frozen.production_execution_protocol_id,
        "production_execution_slot": slot,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "query_ordinal": QUERY_ORDINAL,
        "source_facts": [_source_fact(filename) for filename in _SOURCE_NAMES],
        "retained_predecessor_input_facts": [
            _input_fact(path, byte_count, sha256)
            for path, byte_count, sha256 in _INPUT_SPECS
        ],
        "entrypoint": (
            "acfqp.construction_k7_full_ground_fallback_production_terminal_finalizer_v180r7:"
            "run_full_ground_fallback_production_occurrence_v180r7"
        ),
        "fresh_recovery_eligible_execution_required": True,
        "three_route_family_vectors_must_remain_separate": True,
        "registered_record_to_record_v6_to_v9_lift_required": True,
        "summary_to_counter_translation_forbidden": True,
        "additive_or_source_optional_paths_require_explicit_native_zero_lineage": True,
        "runtime_cas_root_must_be_absent": True,
        "output_root_must_be_absent": True,
        "execution_terminal_must_be_written_once": True,
        "same_authorization_rerun_after_progress_or_terminal_forbidden": True,
        "fresh_fallback_execution_started": False,
        "production_outcome_accessed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "fallback_execution_authorization_id": domains.extension_content_id_v180r7(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_AUTHORIZATION_V180R7_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FallbackExecutionAuthorizationV180r7:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


@lru_cache(maxsize=1)
def freeze_fallback_execution_authorization_v180r7() -> FallbackExecutionAuthorizationV180r7:
    document = build_fallback_execution_authorization_v180r7()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["fallback_execution_authorization_id"]
        == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r7 fallback execution authorization changed")
    return FallbackExecutionAuthorizationV180r7(
        _ISSUER,
        raw,
        document["fallback_execution_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "freeze_fallback_execution_authorization_v180r7",
)
