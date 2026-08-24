"""Outcome-free authorization for the V180r11 V34 finish-forward recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v34_failure_freeze_v180r5 as failure
from acfqp import construction_k7_domain_registry_extension_v180r11 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = "0935d168087af5adcb6bc6c31f7958502092ee8381d2bea030d89e1725f6906a"
EXPECTED_CANONICAL_BYTE_COUNT = 8_072
EXPECTED_CANONICAL_SHA256 = "c8af5a6b7158e122eee63f6f5b31045de1cdab952fb003e8ab3486f729b4e413"

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v180r11.py",
    "src/acfqp/construction_k7_all_path_v34_failure_freeze_v180r5.py",
    "src/acfqp/construction_k7_v34_retained_campaign_reconstructor_v180r11.py",
    "src/acfqp/construction_k7_v34_retained_recovery_terminal_v180r11.py",
    "src/acfqp/construction_k7_v34_retained_recovery_independent_verifier_v180r11.py",
    "src/acfqp/construction_k7_all_path_production_execution_protocol_v180r3.py",
    "src/acfqp/construction_k7_standard_2048_expression_full_accounted_campaign_v34.py",
    "src/acfqp/construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34.py",
    "src/acfqp/construction_k7_standard_2048_expression_full_accounting_preregistration_v34.py",
    "src/acfqp/construction_k7_standard_2048_expression_checkpoint_preregistration_v26.py",
    "src/acfqp/construction_k7_standard_2048_expression_checkpoint_preregistration_v27.py",
    "src/acfqp/construction_k7_standard_2048_expression_checkpoint_preregistration_v28.py",
    "src/acfqp/construction_k7_standard_2048_expression_checkpoint_preregistration_v29.py",
    "src/acfqp/construction_k7_standard_2048_expression_checkpoint_preregistration_v30.py",
    "src/acfqp/construction_k7_standard_2048_expression_checkpoint_preregistration_v31.py",
    "src/acfqp/construction_k7_standard_2048_expression_checkpoint_preregistration_v32.py",
    "src/acfqp/construction_k7_standard_2048_expression_checkpoint_preregistration_v33.py",
    "src/acfqp/construction_accounting_registry_v9.py",
    "src/acfqp/accounting_v1.py",
    "src/acfqp/actual_accounting_v1.py",
    "src/acfqp/phase3e_ids.py",
    "scripts/run_v180r11_v34_retained_recovery.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_v34_retained_recovery_authorization_v180r11() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    frozen_failure = failure.load_frozen_v34_failure_v180r5()
    protocol_document = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()
    slots = [
        row
        for row in protocol_document["production_execution_slots"]
        if row["terminal_code"] == "ABSTRACT_CERTIFIED"
    ]
    if len(slots) != 1:
        raise ValueError("V180r11 abstract-certified slot changed")
    payload = {
        "schema": "acfqp.v34_retained_recovery_authorization.v180r11",
        "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "production_execution_slot": slots[0],
        "preserved_v180r5_failure_id": frozen_failure.failure_id,
        "preserved_v180r5_failure_sha256": failure.EXPECTED_CANONICAL_SHA256,
        "preserved_v180r5_partial_inventory_sha256": failure.EXPECTED_PARTIAL_INVENTORY_SHA256,
        "same_failed_authorization_rerun": False,
        "successor_reason": "UPPERCASE_OPERATIONAL_LANE_LITERAL",
        "scientific_occurrence_rerun_forbidden": True,
        "retained_actual_occurrence_finish_forward_only": True,
        "retained_source_output_root_relative_path": ".tmp/exact-freeze/v180r5_v34_production_output",
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_v34_retained_recovery_terminal_v180r11:"
            "finish_forward_retained_v34_occurrence_v180r11"
        ),
        "runner_relative_path": "scripts/run_v180r11_v34_retained_recovery.py",
        "terminal_output_relative_path": ".tmp/exact-freeze/v180r11_v34_retained_terminal.json",
        "verification_output_relative_path": ".tmp/exact-freeze/v180r11_v34_retained_verification.json",
        "failure_output_relative_path": ".tmp/exact-freeze/v180r11_v34_retained_failure.json",
        "all_successor_output_paths_must_be_absent": True,
        "same_authorization_rerun_after_any_progress_forbidden": True,
        "recovery_execution_started": False,
        "new_scientific_outcome_accessed": False,
        "actual_worker_process_count": 0,
        "producer_free_replay_required": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "v34_retained_recovery_authorization_id": domains.extension_content_id_v180r11(
            domains.CONSTRUCTION_K7_V34_RETAINED_RECOVERY_AUTHORIZATION_V180R11_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V34RetainedRecoveryAuthorizationV180r11:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r11 authorization is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_v34_retained_recovery_authorization_v180r11() -> V34RetainedRecoveryAuthorizationV180r11:
    document = build_v34_retained_recovery_authorization_v180r11()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["v34_retained_recovery_authorization_id"]
        == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r11 recovery authorization changed")
    return V34RetainedRecoveryAuthorizationV180r11(
        _ISSUER,
        raw,
        document["v34_retained_recovery_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "build_v34_retained_recovery_authorization_v180r11",
    "freeze_v34_retained_recovery_authorization_v180r11",
)
