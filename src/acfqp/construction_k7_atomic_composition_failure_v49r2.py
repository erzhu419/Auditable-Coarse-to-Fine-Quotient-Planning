"""Frozen pre-query certificate failure from registered V49r2."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_atomic_composition_preregistration_v49r2 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


FAILURE_ID = "3d4189ef1c2d8640395e77aed9164ead32abf44c2adc56b7d8a0b29c1207695d"
EXPECTED_CANONICAL_BYTE_COUNT = 1_595
EXPECTED_CANONICAL_SHA256 = "29bc1af8bc55f25c08345b76e054bda7efc3f9da4eaec7c57e4d0276460fb27b"
FAILED_PRODUCER_RELATIVE_PATH = "src/acfqp/construction_k7_atomic_composition_campaign_v49r2.py"
FAILED_PRODUCER_BYTE_COUNT = 24_167
FAILED_PRODUCER_SHA256 = "f2193932622c2313f150a5a1ade0ef4e7f1c419a37cda48f41a2fdac8ece2e73"


class ConstructionK7AtomicCompositionFailureV49R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionFailureV49R2Error(message)


def _document() -> dict[str, Any]:
    raw = (pre.SOURCE_ROOT / FAILED_PRODUCER_RELATIVE_PATH).read_bytes()
    if len(raw) != FAILED_PRODUCER_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != FAILED_PRODUCER_SHA256:
        _fail("failed V49r2 producer source changed")
    payload = {
        "schema": "acfqp.atomic_composition_campaign_failure.v49r2",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "preserved_v49_failure_id": pre.V49_FAILURE_ID,
        "preserved_v49r1_failure_id": pre.V49R1_FAILURE_ID,
        "failed_producer_source": {
            "relative_path": FAILED_PRODUCER_RELATIVE_PATH,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "registered_execution_started": True,
        "source_occurrences_completed": 3,
        "source_support_labels_observed": 223,
        "source_raw_outcome_rows_observed": 446,
        "first_target_seed": pre.TARGET_SEEDS[0],
        "target_local_ground_support_queries_performed": 0,
        "campaign_artifact_issued": False,
        "failure_stage": "RELATION_TRANSPORT_CERTIFICATE_DEPENDENCY_EXTRACTION",
        "exception_type": "ConstructionK7AtomicCompositionCampaignV49R2Error",
        "exception_message": "V49r2 relation transport certificate unexpectedly passed",
        "root_cause": "CERTIFICATE_COMPARED_E03_BINDING_CONSTANTS_BUT_COMPILED_RELATION_DEPENDED_ON_E00_CONSTANT_COLUMN",
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
        "atomic_composition_failure_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AtomicCompositionFailureV49R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49r2 failure is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49r2 failure bytes changed")
        payload = {key: value for key, value in document.items() if key != "atomic_composition_failure_id"}
        if document.get("atomic_composition_failure_id") != self.failure_id or content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ) != self.failure_id:
            _fail("V49r2 failure identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_atomic_composition_failure_v49r2() -> AtomicCompositionFailureV49R2:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_failure_id"]
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r2 failure changed")
    return AtomicCompositionFailureV49R2(_ISSUER, raw, identity)


__all__ = (
    "AtomicCompositionFailureV49R2",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FAILED_PRODUCER_BYTE_COUNT",
    "FAILED_PRODUCER_RELATIVE_PATH",
    "FAILED_PRODUCER_SHA256",
    "FAILURE_ID",
    "freeze_atomic_composition_failure_v49r2",
)
