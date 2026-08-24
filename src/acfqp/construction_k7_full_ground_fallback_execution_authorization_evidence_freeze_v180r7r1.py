"""Post-preregistration freeze for the V180r7r1 authorization itself.

This module is deliberately prewired before authorization preregistration. Its
source and the authorization source are the only two static-closure exclusions;
the post-preregistration commit fills the zero sentinels below without changing
the already-bound execution or verification runners.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_domain_registry_extension_v180r7r1p as domains
from acfqp import (
    construction_k7_full_ground_fallback_execution_authorization_v180r7r1
    as authorization,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


AUTHORIZATION_EVIDENCE_DOMAIN = (
    domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_AUTHORIZATION_EVIDENCE_V180R7R1P_DOMAIN
)
EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "1a9ed5c0fa2bb07550e78d0c104eadbbd2ffe1442091f41b0244f6b4eca36667"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_384
EXPECTED_CANONICAL_SHA256 = (
    "ef68f263b92f2a1432535ead710e697be5e70d53b7cc57ea56c08ac3f060a906"
)
EXPECTED_AUTHORIZATION_ID = (
    "44c19c059e229b6d45b1a9cf4591bf5ee5a53a68ca33ba54b5f5b6ae1b115f6b"
)
EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT = 32_413
EXPECTED_AUTHORIZATION_CANONICAL_SHA256 = (
    "b22709dddd2d2354812d064086cb7f0a9edcffb215b4788015e39bea1f40bb3e"
)
EXPECTED_PROTOCOL_ID = (
    "0d037ddaa78b4f6fceca4409db55eeb0acb93d8c1d64953430debd108ef31889"
)
EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT = 22_697
EXPECTED_AUTHORIZATION_SOURCE_SHA256 = (
    "18a96df45a1d136fada59cf09d91b4f485dd7556d53cdd5532403d5229495b07"
)

_ROOT = Path(__file__).resolve().parents[2]
_AUTHORIZATION_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_full_ground_fallback_execution_authorization_v180r7r1.py"
)
_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_full_ground_fallback_execution_"
    "authorization_evidence_freeze_v180r7r1.py"
)
SOURCE_FACT_EXCLUSIONS = tuple(
    sorted((_AUTHORIZATION_RELATIVE_PATH, _EVIDENCE_RELATIVE_PATH))
)

# Filled once, after the outcome-free authorization is committed. These four
# paths are already included in the authorization static source closure.
EXPECTED_EXECUTION_CHAIN_SOURCE_FACTS = (
    (
        "scripts/run_v180r7r1_full_ground_fallback_occurrence.py",
        14_797,
        "469d537e009a1d973357fa56932f3b630e989fb6933cd975fa0ae02f75f8b828",
    ),
    (
        "scripts/verify_v180r7r1_full_ground_fallback_occurrence.py",
        8_560,
        "8b61b73de2cc4014f5c7ba6dcf4de774052f0d141fd92e17900412ea0cb159f8",
    ),
    (
        "src/acfqp/construction_k7_full_ground_fallback_"
        "production_terminal_finalizer_v180r7r1.py",
        35_642,
        "92bde4152813958d10367c1fa80b38d08cd2f02a4d7f9a6a8707cd28d1d5802e",
    ),
    (
        "src/acfqp/construction_k7_full_ground_fallback_"
        "production_terminal_independent_verifier_v180r7r1.py",
        85_468,
        "214ee363cdfc87760f9aabaceced89c48f29bc93f5f9b67a7d86d627c863207e",
    ),
)

AUTHORIZATION_EVIDENCE_FIELDS = frozenset(
    {
        "BREAK_EVEN_GATE",
        "COUNTER_COMPLETENESS_GATE",
        "SCALAR_CALIBRATION_GATE",
        "WORKLOAD_ECONOMICS_GATE",
        "authorization_canonical_byte_count",
        "authorization_canonical_sha256",
        "authorization_evidence_domain",
        "authorization_evidence_id",
        "authorization_preregistered_before_this_evidence",
        "authorization_self_source_bound_by_this_evidence",
        "authorization_source_fact",
        "evidence_wrapper_self_source_excluded_to_avoid_identity_cycle",
        "execution_chain_source_facts",
        "fallback_execution_authorization_id",
        "fallback_execution_protocol_id",
        "fresh_production_occurrence_count",
        "official_N_break_even",
        "official_execution_allowed",
        "official_scalar_cost",
        "outcome_free",
        "production_outcome_accessed",
        "schema",
        "source_fact_exclusions",
    }
)


class FullGroundFallbackAuthorizationEvidenceV180r7r1Error(ValueError):
    """The post-prereg authorization evidence is absent or changed."""


def _fail(message: str) -> NoReturn:
    raise FullGroundFallbackAuthorizationEvidenceV180r7r1Error(message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_regular_symlink_free(path: Path) -> bytes:
    try:
        return source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise FullGroundFallbackAuthorizationEvidenceV180r7r1Error(
            "authorization-evidence source is absent, linked, or nonregular"
        ) from error


def _source_fact(relative_path: str) -> dict[str, Any]:
    raw = _read_regular_symlink_free(_ROOT / relative_path)
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": _sha256(raw),
    }


def _expected_chain_source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": relative_path,
            "byte_count": byte_count,
            "sha256": sha256,
        }
        for relative_path, byte_count, sha256 in sorted(
            EXPECTED_EXECUTION_CHAIN_SOURCE_FACTS
        )
    ]


def _require_post_prereg_constants() -> None:
    identities = (
        EXPECTED_AUTHORIZATION_EVIDENCE_ID,
        EXPECTED_CANONICAL_SHA256,
        EXPECTED_AUTHORIZATION_ID,
        EXPECTED_AUTHORIZATION_CANONICAL_SHA256,
        EXPECTED_PROTOCOL_ID,
        EXPECTED_AUTHORIZATION_SOURCE_SHA256,
    )
    chain = _expected_chain_source_facts()
    if not (
        all(value != "0" * 64 for value in identities)
        and EXPECTED_CANONICAL_BYTE_COUNT > 0
        and EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT > 0
        and EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT > 0
        and len(chain) == 4
        and all(
            row["byte_count"] > 0 and row["sha256"] != "0" * 64
            for row in chain
        )
    ):
        _fail("post-prereg authorization evidence constants are not frozen")


def _build_authorization_evidence_document() -> dict[str, Any]:
    _require_post_prereg_constants()
    frozen = (
        authorization.freeze_full_ground_fallback_execution_authorization_v180r7r1()
    )
    authorization_document = frozen.to_document()
    authorization_raw = frozen.canonical_bytes
    authorization_source_fact = _source_fact(_AUTHORIZATION_RELATIVE_PATH)
    expected_chain_facts = _expected_chain_source_facts()
    execution_chain_source_facts = [
        _source_fact(row["relative_path"]) for row in expected_chain_facts
    ]
    authorization_bound_facts = {
        row["relative_path"]: row
        for row in authorization_document["source_facts"]
    }
    if not (
        frozen.authorization_id == EXPECTED_AUTHORIZATION_ID
        and authorization.EXPECTED_AUTHORIZATION_ID == EXPECTED_AUTHORIZATION_ID
        and len(authorization_raw) == EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT
        and _sha256(authorization_raw) == EXPECTED_AUTHORIZATION_CANONICAL_SHA256
        and authorization_document["fallback_execution_protocol_id"]
        == EXPECTED_PROTOCOL_ID
        and authorization_source_fact
        == {
            "relative_path": _AUTHORIZATION_RELATIVE_PATH,
            "byte_count": EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT,
            "sha256": EXPECTED_AUTHORIZATION_SOURCE_SHA256,
        }
        and execution_chain_source_facts == expected_chain_facts
        and all(
            authorization_bound_facts.get(row["relative_path"]) == row
            for row in execution_chain_source_facts
        )
        and authorization_document["source_fact_exclusions"]
        == list(SOURCE_FACT_EXCLUSIONS)
        and authorization_document[
            "authorization_self_source_bound_by_post_prereg_freeze"
        ]
        is False
        and authorization_document["self_identity_cycle_avoided"] is True
        and authorization_document[
            "post_prereg_authorization_evidence_freeze_required"
        ]
        is True
        and authorization_document["production_outcome_accessed"] is False
        and authorization_document["official_execution_allowed"] is False
    ):
        _fail("post-prereg authorization or its execution source chain changed")
    payload = {
        "schema": (
            "acfqp.full_ground_fallback_execution_authorization_evidence."
            "v180r7r1"
        ),
        "authorization_evidence_domain": AUTHORIZATION_EVIDENCE_DOMAIN,
        "fallback_execution_authorization_id": frozen.authorization_id,
        "fallback_execution_protocol_id": EXPECTED_PROTOCOL_ID,
        "authorization_canonical_byte_count": len(authorization_raw),
        "authorization_canonical_sha256": _sha256(authorization_raw),
        "authorization_source_fact": authorization_source_fact,
        "execution_chain_source_facts": execution_chain_source_facts,
        "source_fact_exclusions": list(SOURCE_FACT_EXCLUSIONS),
        "authorization_self_source_bound_by_this_evidence": True,
        "evidence_wrapper_self_source_excluded_to_avoid_identity_cycle": True,
        "authorization_preregistered_before_this_evidence": True,
        "production_outcome_accessed": False,
        "fresh_production_occurrence_count": 0,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
    }
    return {
        **payload,
        "authorization_evidence_id": domains.extension_content_id_v180r7r1p(
            AUTHORIZATION_EVIDENCE_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FullGroundFallbackAuthorizationEvidenceV180r7r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_evidence_id: str
    authorization_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = dict(document) if type(document) is dict else {}
        identity = payload.pop("authorization_evidence_id", None)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and set(document) == AUTHORIZATION_EVIDENCE_FIELDS
            and identity == self.authorization_evidence_id
            and identity
            == domains.extension_content_id_v180r7r1p(
                AUTHORIZATION_EVIDENCE_DOMAIN,
                payload,
            )
            and document.get("fallback_execution_authorization_id")
            == self.authorization_id
        ):
            _fail("authorization evidence is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@lru_cache(maxsize=1)
def freeze_full_ground_fallback_execution_authorization_evidence_v180r7r1(
) -> FullGroundFallbackAuthorizationEvidenceV180r7r1:
    document = _build_authorization_evidence_document()
    raw = canonical_json_bytes(document)
    if not (
        document["authorization_evidence_id"]
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and _sha256(raw) == EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen authorization evidence identity changed")
    return FullGroundFallbackAuthorizationEvidenceV180r7r1(
        _ISSUER,
        raw,
        document["authorization_evidence_id"],
        document["fallback_execution_authorization_id"],
    )


__all__ = (
    "AUTHORIZATION_EVIDENCE_DOMAIN",
    "AUTHORIZATION_EVIDENCE_FIELDS",
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_PROTOCOL_ID",
    "FullGroundFallbackAuthorizationEvidenceV180r7r1",
    "FullGroundFallbackAuthorizationEvidenceV180r7r1Error",
    "SOURCE_FACT_EXCLUSIONS",
    "freeze_full_ground_fallback_execution_authorization_evidence_v180r7r1",
)
