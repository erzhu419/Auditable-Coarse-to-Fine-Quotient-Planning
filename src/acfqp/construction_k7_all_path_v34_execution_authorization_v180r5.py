"""Fresh corrected V34 authorization preserving the V180r4 failure."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v34_failure_freeze_v180r4 as failure_v180r4
from acfqp import construction_k7_domain_registry_extension_v180r5 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


def _source_fact(filename: str) -> dict[str, Any]:
    raw = (Path(__file__).resolve().parent / filename).read_bytes()
    return {
        "filename": filename,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_v34_execution_authorization_v180r5() -> dict[str, Any]:
    frozen = protocol.freeze_all_path_production_execution_protocol_v180r3()
    failed = failure_v180r4.load_frozen_v34_failure_v180r4()
    slot = next(
        row
        for row in frozen.to_document()["production_execution_slots"]
        if row["terminal_code"] == "ABSTRACT_CERTIFIED"
    )
    source_facts = [
        _source_fact(filename)
        for filename in (
            "construction_k7_all_path_production_terminal_finalizer_v180r3.py",
            "construction_k7_standard_2048_expression_full_accounted_campaign_v34.py",
            "construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34.py",
            "construction_k7_all_path_v34_failure_freeze_v180r4.py",
            "construction_k7_domain_registry_extension_v180r3.py",
            "construction_k7_domain_registry_extension_v180r5.py",
            "construction_accounting_registry_v9.py",
        )
    ]
    payload = {
        "schema": "acfqp.v34_production_execution_authorization.v180r5",
        "production_execution_protocol_id": frozen.production_execution_protocol_id,
        "production_execution_slot": slot,
        "preserved_v180r4_failure_id": failed.failure_id,
        "v180r4_same_identity_rerun": False,
        "corrected_boundary": "PATH_SUBCLASS_ACCEPTED_BY_ISINSTANCE",
        "source_facts": source_facts,
        "entrypoint": (
            "acfqp.construction_k7_all_path_production_terminal_finalizer_v180r3:"
            "run_v34_abstract_certified_production_occurrence_v180r3"
        ),
        "output_root_must_be_absent": True,
        "campaign_output_must_be_created_exclusively": True,
        "execution_terminal_must_be_written_once": True,
        "same_authorization_rerun_after_progress_or_terminal_forbidden": True,
        "fresh_v34_execution_started": False,
        "production_outcome_accessed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "v34_execution_authorization_id": domains.extension_content_id_v180r5(
            domains.CONSTRUCTION_K7_V34_EXECUTION_AUTHORIZATION_V180R5_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V34ExecutionAuthorizationV180r5:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


@lru_cache(maxsize=1)
def freeze_v34_execution_authorization_v180r5() -> V34ExecutionAuthorizationV180r5:
    document = build_v34_execution_authorization_v180r5()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["v34_execution_authorization_id"] == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r5 V34 execution authorization changed")
    return V34ExecutionAuthorizationV180r5(
        _ISSUER,
        raw,
        document["v34_execution_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "freeze_v34_execution_authorization_v180r5",
)
