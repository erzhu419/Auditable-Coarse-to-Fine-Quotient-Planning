"""Producer for the preregistered epoch-indexed quotient campaign V110."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_epoch_indexed_quotient_preregistration_v110 as pre
from acfqp.construction_k7_dependency_revalidated_quotient_independent_verifier_v109 import (
    CAMPAIGN_BYTE_COUNT as V109_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V109_VERIFICATION_BYTE_COUNT,
    freeze_dependency_revalidated_quotient_verification_v109,
    verify_dependency_revalidated_quotient_campaign_bytes_v109,
)
from acfqp.epoch_indexed_quotient_campaign_core_v110 import (
    build_epoch_indexed_quotient_campaign_document_v110,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7EpochIndexedQuotientCampaignV110Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7EpochIndexedQuotientCampaignV110Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class EpochIndexedQuotientCampaignV110:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v110(
                pre.domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_CAMPAIGN_V110_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V110 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: EpochIndexedQuotientCampaignV110 | None = None


def run_epoch_indexed_quotient_campaign_v110(
    v109_campaign_raw: bytes,
    v109_verification_raw: bytes,
) -> EpochIndexedQuotientCampaignV110:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V110 campaign exists; same identity will not be rerun")
    registration = pre.verify_epoch_indexed_quotient_preregistration_v110(
        pre.freeze_epoch_indexed_quotient_preregistration_v110()
    )
    try:
        verified_v109 = verify_dependency_revalidated_quotient_campaign_bytes_v109(
            v109_campaign_raw
        )
        verification_v109 = loads_canonical_json(v109_verification_raw)
    except Exception as exc:
        _fail(f"V110 frozen V109 predecessor is unreadable: {exc}")
    if (
        len(v109_campaign_raw) != V109_CAMPAIGN_BYTE_COUNT
        or verified_v109.get("campaign_id") != pre.V109_CAMPAIGN_ID
        or verified_v109.get("registered_gate_independently_verified") is not True
        or canonical_json_bytes(verification_v109) != v109_verification_raw
        or len(v109_verification_raw) != V109_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v109_verification_raw).hexdigest()
        != pre.V109_VERIFICATION_SHA256
        or verification_v109.get("verification_id") != pre.V109_VERIFICATION_ID
        or freeze_dependency_revalidated_quotient_verification_v109(
            v109_campaign_raw
        )
        != v109_verification_raw
    ):
        _fail("V110 frozen V109 evidence changed")
    document = build_epoch_indexed_quotient_campaign_document_v110(
        pre.campaign_config_v110(),
        preregistration_id=registration.preregistration_id,
        v109_campaign_id=pre.V109_CAMPAIGN_ID,
        v109_verification_id=pre.V109_VERIFICATION_ID,
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V110 campaign changed")
    _CACHE = EpochIndexedQuotientCampaignV110(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_epoch_indexed_quotient_campaign_v110",
)
