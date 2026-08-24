"""Outcome-free authorization for one fresh V36 local-recovery occurrence."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r6 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = (
    "14adfdeb41829d840d18e071189148bb587357134e0f97d101f5a6a71220acc2"
)
EXPECTED_CANONICAL_BYTE_COUNT = 5_420
EXPECTED_CANONICAL_SHA256 = (
    "048a11d00d1e2569abc406a7c8e16f2eeb6d0ea93c1096ba59805213b0d8517d"
)


_SOURCE_NAMES = (
    "construction_k7_v36_local_recovery_production_terminal_finalizer_v180r6.py",
    "construction_k7_standard_2048_adaptive_expression_campaign_v35.py",
    "construction_k7_standard_2048_adaptive_expression_independent_verifier_v35.py",
    "construction_k7_standard_2048_adaptive_expression_preregistration_v35.py",
    "construction_k7_standard_2048_adaptive_accounted_campaign_v36.py",
    "construction_k7_standard_2048_adaptive_accounted_independent_verifier_v36.py",
    "construction_k7_standard_2048_adaptive_accounting_artifacts_v36.py",
    "construction_k7_all_path_production_execution_protocol_v180r3.py",
    "construction_k7_domain_registry_extension_v180r6.py",
    "construction_accounting_registry_v9.py",
)


def _source_fact(filename: str) -> dict[str, Any]:
    raw = (Path(__file__).resolve().parent / filename).read_bytes()
    return {
        "filename": filename,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_v36_execution_authorization_v180r6() -> dict[str, Any]:
    frozen = protocol.freeze_all_path_production_execution_protocol_v180r3()
    slot = next(
        row
        for row in frozen.to_document()["production_execution_slots"]
        if row["terminal_code"] == "LOCAL_GROUND_RECOVERY"
    )
    payload = {
        "schema": "acfqp.v36_production_execution_authorization.v180r6",
        "production_execution_protocol_id": frozen.production_execution_protocol_id,
        "production_execution_slot": slot,
        "source_facts": [_source_fact(filename) for filename in _SOURCE_NAMES],
        "entrypoint": (
            "acfqp.construction_k7_v36_local_recovery_production_terminal_finalizer_v180r6:"
            "run_v36_local_ground_recovery_production_occurrence_v180r6"
        ),
        "v35_predecessor_regenerated_and_independently_verified": True,
        "v36_execution_and_independent_replay_required": True,
        "certificate_failure_before_local_recovery_required": True,
        "ground_distinctions_before_certificate_failure_forbidden": True,
        "output_root_must_be_absent": True,
        "campaign_output_must_be_created_exclusively": True,
        "execution_terminal_must_be_written_once": True,
        "same_authorization_rerun_after_progress_or_terminal_forbidden": True,
        "fresh_v36_execution_started": False,
        "production_outcome_accessed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "v36_execution_authorization_id": domains.extension_content_id_v180r6(
            domains.CONSTRUCTION_K7_V36_EXECUTION_AUTHORIZATION_V180R6_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V36ExecutionAuthorizationV180r6:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


@lru_cache(maxsize=1)
def freeze_v36_execution_authorization_v180r6() -> V36ExecutionAuthorizationV180r6:
    document = build_v36_execution_authorization_v180r6()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["v36_execution_authorization_id"] == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r6 V36 execution authorization changed")
    return V36ExecutionAuthorizationV180r6(
        _ISSUER,
        raw,
        document["v36_execution_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "freeze_v36_execution_authorization_v180r6",
)
