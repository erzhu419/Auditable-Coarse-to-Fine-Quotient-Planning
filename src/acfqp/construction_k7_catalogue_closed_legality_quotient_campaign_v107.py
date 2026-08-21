"""Producer for the preregistered catalogue-closed quotient V107 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_catalogue_closed_legality_quotient_preregistration_v107 as pre
from acfqp.catalogue_closed_legality_conditioned_quotient_campaign_core_v107 import (
    build_catalogue_closed_legality_quotient_campaign_document_v107,
)
from acfqp.construction_k7_legality_conditioned_quotient_independent_verifier_v106 import (
    CAMPAIGN_BYTE_COUNT as V106_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V106_VERIFICATION_BYTE_COUNT,
    freeze_legality_conditioned_quotient_verification_v106,
    verify_legality_conditioned_quotient_campaign_bytes_v106,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7CatalogueClosedLegalityQuotientCampaignV107Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CatalogueClosedLegalityQuotientCampaignV107Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CatalogueClosedLegalityQuotientCampaignV107:
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
            or pre.domains.extension_content_id_v107(
                pre.domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_CAMPAIGN_V107_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V107 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CatalogueClosedLegalityQuotientCampaignV107 | None = None


def run_catalogue_closed_legality_quotient_campaign_v107(
    v106_campaign_raw: bytes,
    v106_verification_raw: bytes,
) -> CatalogueClosedLegalityQuotientCampaignV107:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V107 campaign exists; same identity will not be rerun")
    registration = pre.verify_catalogue_closed_legality_quotient_preregistration_v107(
        pre.freeze_catalogue_closed_legality_quotient_preregistration_v107()
    )
    try:
        verified_v106 = verify_legality_conditioned_quotient_campaign_bytes_v106(
            v106_campaign_raw
        )
        verification_v106 = loads_canonical_json(v106_verification_raw)
    except Exception as exc:
        _fail(f"V107 frozen failed V106 predecessor is unreadable: {exc}")
    if (
        len(v106_campaign_raw) != V106_CAMPAIGN_BYTE_COUNT
        or verified_v106.get("campaign_id") != pre.V106_CAMPAIGN_ID
        or verified_v106.get("registered_gate_independently_verified") is not False
        or verified_v106.get("fresh_successor_required") is not True
        or verified_v106.get(
            "fallback_plan_receipt_count_without_complete_catalogue_closure"
        )
        != 128
        or canonical_json_bytes(verification_v106) != v106_verification_raw
        or len(v106_verification_raw) != V106_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v106_verification_raw).hexdigest()
        != pre.V106_VERIFICATION_SHA256
        or verification_v106.get("verification_id") != pre.V106_VERIFICATION_ID
        or freeze_legality_conditioned_quotient_verification_v106(
            v106_campaign_raw
        )
        != v106_verification_raw
    ):
        _fail("V107 frozen failed V106 evidence changed")
    document = build_catalogue_closed_legality_quotient_campaign_document_v107(
        pre.campaign_config_v107(),
        preregistration_id=registration.preregistration_id,
        v106_campaign_id=pre.V106_CAMPAIGN_ID,
        v106_verification_id=pre.V106_VERIFICATION_ID,
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
        _fail("frozen V107 campaign changed")
    _CACHE = CatalogueClosedLegalityQuotientCampaignV107(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_catalogue_closed_legality_quotient_campaign_v107",
)
