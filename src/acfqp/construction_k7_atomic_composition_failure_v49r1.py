"""Frozen terminal failure from the fresh V49r1 registered execution."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_atomic_composition_preregistration_v49r1 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


FAILURE_ID = "7a6287e3f844fc3d9910495ceb1f7fd0a692e0114c71c790ca572ea13bb4bd1b"
EXPECTED_CANONICAL_BYTE_COUNT = 1_600
EXPECTED_CANONICAL_SHA256 = "c1d5f0573b63c6d6f14ab64b795a6a32d69437483a73201d4613fefeb56b7116"
FAILED_PRODUCER_RELATIVE_PATH = "src/acfqp/construction_k7_atomic_composition_campaign_v49r1.py"
FAILED_PRODUCER_BYTE_COUNT = 28_495
FAILED_PRODUCER_SHA256 = "97a09fed675b53befc7f299155fa247873c2c44eee51c8bf2dd82effa5a2bfc8"


class ConstructionK7AtomicCompositionFailureV49R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionFailureV49R1Error(message)


def _document() -> dict[str, Any]:
    raw = (pre.SOURCE_ROOT / FAILED_PRODUCER_RELATIVE_PATH).read_bytes()
    if len(raw) != FAILED_PRODUCER_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != FAILED_PRODUCER_SHA256:
        _fail("failed V49r1 producer source changed")
    payload = {
        "schema": "acfqp.atomic_composition_campaign_failure.v49r1",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "preserved_v49_failure_id": pre.V49_FAILURE_ID,
        "failed_producer_source": {
            "relative_path": FAILED_PRODUCER_RELATIVE_PATH,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "registered_execution_started": True,
        "source_occurrences_completed": 3,
        "source_support_labels_observed": 214,
        "source_raw_outcome_rows_observed": 428,
        "first_target_seed": pre.TARGET_SEEDS[0],
        "failed_certificates_constructed_in_memory": 1,
        "target_local_ground_support_queries_performed": 1,
        "local_relation_rows_recovered_in_memory": 1,
        "campaign_artifact_issued": False,
        "failure_stage": "ABSTRACT_ROBUST_PLANNING_AFTER_MISSING_RELATION_RECOVERY",
        "exception_type": "GenericAtomicExpressionWorldModelV4Error",
        "exception_message": "generic atomic program found no robust continuation",
        "root_cause": "TARGET_CHANGED_AN_EXISTING_RELATION_VALUE_IN_ADDITION_TO_ADDING_A_NEW_VALUE",
        "missing_only_recovery_insufficient": True,
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
class AtomicCompositionFailureV49R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49r1 failure is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49r1 failure bytes changed")
        payload = {key: value for key, value in document.items() if key != "atomic_composition_failure_id"}
        if document.get("atomic_composition_failure_id") != self.failure_id or content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ) != self.failure_id:
            _fail("V49r1 failure identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_atomic_composition_failure_v49r1() -> AtomicCompositionFailureV49R1:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_failure_id"]
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r1 failure changed")
    return AtomicCompositionFailureV49R1(_ISSUER, raw, identity)


__all__ = (
    "AtomicCompositionFailureV49R1",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FAILURE_ID",
    "freeze_atomic_composition_failure_v49r1",
)
