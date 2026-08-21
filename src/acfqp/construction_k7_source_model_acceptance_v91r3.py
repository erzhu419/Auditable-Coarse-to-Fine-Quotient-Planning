"""Producer for the preregistered V91r3 source-model acceptance."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_source_model_acceptance_preregistration_v91r3 as pre
from acfqp.construction_k7_prior_only_occurrence_source_independent_verifier_v91r2 import (
    CAMPAIGN_BYTE_COUNT as V91R2_CAMPAIGN_BYTE_COUNT,
    CAMPAIGN_SHA256 as V91R2_CAMPAIGN_SHA256,
    VERIFICATION_ID as V91R2_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.source_model_acceptance_core_v91r3 import (
    build_source_model_acceptance_document_v91r3,
)


ACCEPTANCE_ID = (
    "59371553fe2e1a9898f1da41abc2c94d860e6833bdada98bc10ffe699d7d444c"
)
EXPECTED_CANONICAL_BYTE_COUNT = 39_427
EXPECTED_CANONICAL_SHA256 = (
    "f91d44c4230aff47ac8346727924247c09d8cc45e804728aaf3b68fd4ee4e597"
)


class ConstructionK7SourceModelAcceptanceV91R3Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceModelAcceptanceV91R3Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SourceModelAcceptanceV91R3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    acceptance_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "acceptance_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("acceptance_id") != self.acceptance_id
            or pre.domains.extension_content_id_v91r3(
                pre.domains.CONSTRUCTION_K7_SOURCE_MODEL_ACCEPTANCE_RESULT_V91R3_DOMAIN,
                payload,
            )
            != self.acceptance_id
        ):
            _fail("V91r3 acceptance bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: SourceModelAcceptanceV91R3 | None = None


def run_source_model_acceptance_v91r3(
    v91r2_campaign_raw: bytes,
) -> SourceModelAcceptanceV91R3:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ACCEPTANCE_ID != "0" * 64:
        _fail("frozen V91r3 acceptance exists; same identity will not be rerun")
    if (
        type(v91r2_campaign_raw) is not bytes
        or len(v91r2_campaign_raw) != V91R2_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v91r2_campaign_raw).hexdigest()
        != V91R2_CAMPAIGN_SHA256
    ):
        _fail("V91r3 predecessor bytes changed")
    predecessor = loads_canonical_json(v91r2_campaign_raw)
    preregistration = pre.verify_source_model_acceptance_preregistration_v91r3(
        pre.freeze_source_model_acceptance_preregistration_v91r3()
    )
    document = build_source_model_acceptance_document_v91r3(
        predecessor,
        preregistration_id=preregistration.preregistration_id,
        v91r2_verification_id=V91R2_VERIFICATION_ID,
    )
    raw = canonical_json_bytes(document)
    identity = document["acceptance_id"]
    if ACCEPTANCE_ID != "0" * 64 and (
        identity != ACCEPTANCE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91r3 acceptance changed")
    _CACHE = SourceModelAcceptanceV91R3(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("ACCEPTANCE_ID", "run_source_model_acceptance_v91r3")
