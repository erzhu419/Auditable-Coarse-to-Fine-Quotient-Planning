"""Producer for preregistered identity-bound quotient memoization V108."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_memoized_catalogue_quotient_preregistration_v108 as pre
from acfqp.construction_k7_catalogue_closed_legality_quotient_independent_verifier_v107 import (
    CAMPAIGN_BYTE_COUNT as V107_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V107_VERIFICATION_BYTE_COUNT,
    freeze_catalogue_closed_legality_quotient_verification_v107,
    verify_catalogue_closed_legality_quotient_campaign_bytes_v107,
)
from acfqp.memoized_catalogue_quotient_campaign_core_v108 import (
    build_memoized_catalogue_quotient_campaign_document_v108,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7MemoizedCatalogueQuotientCampaignV108Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MemoizedCatalogueQuotientCampaignV108Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class MemoizedCatalogueQuotientCampaignV108:
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
            or pre.domains.extension_content_id_v108(
                pre.domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_CAMPAIGN_V108_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V108 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: MemoizedCatalogueQuotientCampaignV108 | None = None


def run_memoized_catalogue_quotient_campaign_v108(
    v107_campaign_raw: bytes,
    v107_verification_raw: bytes,
) -> MemoizedCatalogueQuotientCampaignV108:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V108 campaign exists; same identity will not be rerun")
    registration = pre.verify_memoized_catalogue_quotient_preregistration_v108(
        pre.freeze_memoized_catalogue_quotient_preregistration_v108()
    )
    try:
        verified_v107 = verify_catalogue_closed_legality_quotient_campaign_bytes_v107(
            v107_campaign_raw
        )
        verification_v107 = loads_canonical_json(v107_verification_raw)
    except Exception as exc:
        _fail(f"V108 frozen V107 predecessor is unreadable: {exc}")
    if (
        len(v107_campaign_raw) != V107_CAMPAIGN_BYTE_COUNT
        or verified_v107.get("campaign_id") != pre.V107_CAMPAIGN_ID
        or verified_v107.get("registered_gate_independently_verified") is not True
        or verified_v107.get(
            "producer_free_observation_and_fallback_plan_reconstruction"
        )
        is not True
        or canonical_json_bytes(verification_v107) != v107_verification_raw
        or len(v107_verification_raw) != V107_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v107_verification_raw).hexdigest()
        != pre.V107_VERIFICATION_SHA256
        or verification_v107.get("verification_id") != pre.V107_VERIFICATION_ID
        or freeze_catalogue_closed_legality_quotient_verification_v107(
            v107_campaign_raw
        )
        != v107_verification_raw
    ):
        _fail("V108 frozen V107 evidence changed")
    document = build_memoized_catalogue_quotient_campaign_document_v108(
        pre.campaign_config_v108(),
        preregistration_id=registration.preregistration_id,
        v107_campaign_id=pre.V107_CAMPAIGN_ID,
        v107_verification_id=pre.V107_VERIFICATION_ID,
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
        _fail("frozen V108 campaign changed")
    _CACHE = MemoizedCatalogueQuotientCampaignV108(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_memoized_catalogue_quotient_campaign_v108")
