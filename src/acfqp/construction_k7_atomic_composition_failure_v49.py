"""Frozen terminal failure from the first registered V49 execution."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_atomic_composition_preregistration_v49 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "49.0.0"
FAILURE_ID = "d6031945c70f8547e4b1f4acaf07eab7feb2f6f8274066f6b10cba95b13f2473"
EXPECTED_CANONICAL_BYTE_COUNT = 1_484
EXPECTED_CANONICAL_SHA256 = "8d8e60fd34e3748d7a7d272dd460a2df6f06e284a282680aa93e359a7884031c"
FAILED_PRODUCER_RELATIVE_PATH = (
    "src/acfqp/construction_k7_atomic_composition_campaign_v49.py"
)
FAILED_PRODUCER_BYTE_COUNT = 30_335
FAILED_PRODUCER_SHA256 = "f0bb1c665aad46d707bea56bb6413d07c70f2668100ce8daf3b430f65c117fde"


class ConstructionK7AtomicCompositionFailureV49Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionFailureV49Error(message)


def _document() -> dict[str, Any]:
    producer = pre.SOURCE_ROOT / FAILED_PRODUCER_RELATIVE_PATH
    raw = producer.read_bytes()
    if (
        len(raw) != FAILED_PRODUCER_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != FAILED_PRODUCER_SHA256
    ):
        _fail("failed V49 producer source changed")
    payload = {
        "schema": "acfqp.atomic_composition_campaign_failure.v49",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "failed_producer_source": {
            "relative_path": FAILED_PRODUCER_RELATIVE_PATH,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "registered_execution_started": True,
        "source_occurrences_completed": 3,
        "source_support_labels_observed": 226,
        "source_raw_outcome_rows_observed": 452,
        "first_target_seed": pre.TARGET_SEEDS[0],
        "failed_certificate_constructed_in_memory": True,
        "target_local_ground_support_queries_performed": 1,
        "local_distinction_artifact_issued": False,
        "campaign_artifact_issued": False,
        "failure_stage": "LOCAL_RELATION_MODULUS_BINDING",
        "exception_type": "ConstructionK7AtomicCompositionCampaignV49Error",
        "exception_message": "V49 local recovery could not derive one anonymous modulus",
        "root_cause": "RECOVERY_EXPECTED_E03_DENOMINATOR_BUT_COMPOSER_SELECTED_EQUIVALENT_E00_CONSTANT_COLUMN",
        "correction_under_same_identity_forbidden": True,
        "successor_requires_fresh_preregistration_and_fresh_outcome_identities": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "status": "PRESERVED_REGISTERED_PROTOCOL_FAILURE_NONCERTIFICATE",
    }
    return {
        **payload,
        "atomic_composition_failure_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AtomicCompositionFailureV49:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49 failure is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49 failure bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "atomic_composition_failure_id"
        }
        if (
            document.get("atomic_composition_failure_id") != self.failure_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.failure_id
        ):
            _fail("V49 failure identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_atomic_composition_failure_v49() -> AtomicCompositionFailureV49:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_failure_id"]
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49 failure changed")
    return AtomicCompositionFailureV49(_ISSUER, raw, identity)


__all__ = (
    "AtomicCompositionFailureV49",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FAILED_PRODUCER_SHA256",
    "FAILURE_ID",
    "freeze_atomic_composition_failure_v49",
)
