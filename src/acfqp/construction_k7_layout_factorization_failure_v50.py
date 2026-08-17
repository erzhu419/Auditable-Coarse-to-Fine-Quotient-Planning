"""Frozen first-execution failure of the preregistered V50 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_layout_factorization_preregistration_v50 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


FAILURE_ID = "603e1e69ed5e4093675435ffda6aa1de82118d93b44232a9cfc0454a00424581"
EXPECTED_CANONICAL_BYTE_COUNT = 1_396
EXPECTED_CANONICAL_SHA256 = "5dd5297175bc712ce19ba0b707a48303e0ca395c7932e2ce1d58d98c87cb7720"
PREREGISTRATION_COMMIT = "5dd443f"
FIRST_EXECUTION_PRODUCER_BYTE_COUNT = 4_212
FIRST_EXECUTION_PRODUCER_SHA256 = (
    "2d1a8f947bd3ba185f7270c3928266f46d8cdff368a2a4eeadc981f4e04cf346"
)


class ConstructionK7LayoutFactorizationFailureV50Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LayoutFactorizationFailureV50Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.layout_factorization_registered_failure.v50",
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "first_execution_producer": {
            "relative_path": "src/acfqp/construction_k7_layout_factorization_campaign_v50.py",
            "byte_count": FIRST_EXECUTION_PRODUCER_BYTE_COUNT,
            "sha256": FIRST_EXECUTION_PRODUCER_SHA256,
        },
        "registered_outcome_execution_started": True,
        "failed_family": "STOCHASTIC_INVENTORY_ASSEMBLY",
        "failed_seed": 501_401,
        "failed_decision_index": 0,
        "exception_type": "LayoutFactorizedCampaignCoreV50Error",
        "root_exception_type": "GenericAtomicExpressionWorldModelV4Error",
        "root_exception_message": "atomic expression referenced an unavailable next column",
        "failure_classification": "TERMINAL_TREE_REFERENCED_ITS_OWN_UNAVAILABLE_NEXT_COLUMN",
        "registered_campaign_document_completed": False,
        "partial_campaign_artifact_published": False,
        "same_identity_rerun_forbidden": True,
        "required_successor_correction": (
            "EXCLUDE_TARGET_STATUS_COLUMN_FROM_TERMINAL_NEXT_COLUMN_PREDICATES"
        ),
        "v50_preregistration_preserved_without_correction": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "outcome": "REGISTERED_PROTOCOL_FAILURE_PRESERVED",
    }
    return {
        **payload,
        "failure_id": content_id(pre.FUTURE_DOMAINS["failed_certificate"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LayoutFactorizationFailureV50:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V50 failure is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V50 failure canonical bytes changed")
        payload = {key: value for key, value in document.items() if key != "failure_id"}
        if (
            document.get("failure_id") != self.failure_id
            or content_id(pre.FUTURE_DOMAINS["failed_certificate"], payload)
            != self.failure_id
        ):
            _fail("V50 failure identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_layout_factorization_failure_v50() -> LayoutFactorizationFailureV50:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["failure_id"]
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V50 failure changed")
    return LayoutFactorizationFailureV50(_ISSUER, raw, identity)


def verify_layout_factorization_failure_v50(
    value: LayoutFactorizationFailureV50,
) -> LayoutFactorizationFailureV50:
    if type(value) is not LayoutFactorizationFailureV50:
        _fail("V50 failure rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V50 failure semantics changed")
    return value


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FAILURE_ID",
    "FIRST_EXECUTION_PRODUCER_BYTE_COUNT",
    "FIRST_EXECUTION_PRODUCER_SHA256",
    "LayoutFactorizationFailureV50",
    "freeze_layout_factorization_failure_v50",
    "verify_layout_factorization_failure_v50",
)
