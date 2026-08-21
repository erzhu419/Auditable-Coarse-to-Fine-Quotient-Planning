"""Producer for the preregistered legality-conditioned quotient V106 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_legality_conditioned_quotient_preregistration_v106 as pre
from acfqp.construction_k7_quotient_utilization_independent_verifier_v105 import (
    CAMPAIGN_BYTE_COUNT as V105_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V105_VERIFICATION_BYTE_COUNT,
    freeze_quotient_utilization_verification_v105,
    verify_quotient_utilization_campaign_bytes_v105,
)
from acfqp.legality_conditioned_quotient_campaign_core_v106 import (
    build_legality_conditioned_quotient_campaign_document_v106,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7LegalityConditionedQuotientCampaignV106Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LegalityConditionedQuotientCampaignV106Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LegalityConditionedQuotientCampaignV106:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "campaign_id"
        }
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v106(
                pre.domains.CONSTRUCTION_K7_LEGALITY_CONDITIONED_QUOTIENT_CAMPAIGN_V106_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V106 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: LegalityConditionedQuotientCampaignV106 | None = None


def run_legality_conditioned_quotient_campaign_v106(
    v105_campaign_raw: bytes,
    v105_verification_raw: bytes,
) -> LegalityConditionedQuotientCampaignV106:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V106 campaign exists; same identity will not be rerun")
    registration = (
        pre.verify_legality_conditioned_quotient_preregistration_v106(
            pre.freeze_legality_conditioned_quotient_preregistration_v106()
        )
    )
    try:
        verified_v105 = verify_quotient_utilization_campaign_bytes_v105(
            v105_campaign_raw
        )
        verification_v105 = loads_canonical_json(v105_verification_raw)
    except Exception as exc:
        _fail(f"V106 frozen V105 predecessor is unreadable: {exc}")
    if (
        len(v105_campaign_raw) != V105_CAMPAIGN_BYTE_COUNT
        or verified_v105.get("campaign_id") != pre.V105_CAMPAIGN_ID
        or verified_v105.get("registered_gate_independently_verified") is not True
        or verified_v105.get("actual_engine_ordering_not_posthoc_receipt_reclassification")
        is not True
        or canonical_json_bytes(verification_v105) != v105_verification_raw
        or len(v105_verification_raw) != V105_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v105_verification_raw).hexdigest()
        != pre.V105_VERIFICATION_SHA256
        or verification_v105.get("verification_id") != pre.V105_VERIFICATION_ID
        or verification_v105.get("registered_gate_independently_verified")
        is not True
        or freeze_quotient_utilization_verification_v105(v105_campaign_raw)
        != v105_verification_raw
    ):
        _fail("V106 frozen V105 evidence changed")
    document = build_legality_conditioned_quotient_campaign_document_v106(
        pre.campaign_config_v106(),
        preregistration_id=registration.preregistration_id,
        v105_campaign_id=pre.V105_CAMPAIGN_ID,
        v105_verification_id=pre.V105_VERIFICATION_ID,
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
        _fail("frozen V106 campaign changed")
    _CACHE = LegalityConditionedQuotientCampaignV106(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_legality_conditioned_quotient_campaign_v106",
)
