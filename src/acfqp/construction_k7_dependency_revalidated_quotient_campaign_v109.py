"""Producer for preregistered dependency-revalidated quotient campaign V109."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_dependency_revalidated_quotient_preregistration_v109 as pre
from acfqp.construction_k7_memoized_catalogue_quotient_independent_verifier_v108 import (
    CAMPAIGN_BYTE_COUNT as V108_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V108_VERIFICATION_BYTE_COUNT,
    freeze_memoized_catalogue_quotient_verification_v108,
    verify_memoized_catalogue_quotient_campaign_bytes_v108,
)
from acfqp.dependency_revalidated_quotient_campaign_core_v109 import (
    build_dependency_revalidated_quotient_campaign_document_v109,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "32de00511536f8cfd82bfa1b966290e36d589d1d7e910d4b20657a69937fa6d0"
EXPECTED_CANONICAL_BYTE_COUNT = 7_213_563
EXPECTED_CANONICAL_SHA256 = "46e00a6bf70ff12b010296ffdc01b341e8ce64abaf7f969747679533c7fdf4e1"


class ConstructionK7DependencyRevalidatedQuotientCampaignV109Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DependencyRevalidatedQuotientCampaignV109Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class DependencyRevalidatedQuotientCampaignV109:
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
            or pre.domains.extension_content_id_v109(
                pre.domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_CAMPAIGN_V109_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V109 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: DependencyRevalidatedQuotientCampaignV109 | None = None


def run_dependency_revalidated_quotient_campaign_v109(
    v108_campaign_raw: bytes,
    v108_verification_raw: bytes,
) -> DependencyRevalidatedQuotientCampaignV109:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V109 campaign exists; same identity will not be rerun")
    registration = pre.verify_dependency_revalidated_quotient_preregistration_v109(
        pre.freeze_dependency_revalidated_quotient_preregistration_v109()
    )
    try:
        verified_v108 = verify_memoized_catalogue_quotient_campaign_bytes_v108(
            v108_campaign_raw
        )
        verification_v108 = loads_canonical_json(v108_verification_raw)
    except Exception as exc:
        _fail(f"V109 frozen failed V108 predecessor is unreadable: {exc}")
    if (
        len(v108_campaign_raw) != V108_CAMPAIGN_BYTE_COUNT
        or verified_v108.get("campaign_id") != pre.V108_CAMPAIGN_ID
        or verified_v108.get("registered_gate_independently_verified") is not False
        or verified_v108.get("fresh_successor_required") is not True
        or verified_v108.get("verified_cache_hit_count") != 40
        or canonical_json_bytes(verification_v108) != v108_verification_raw
        or len(v108_verification_raw) != V108_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v108_verification_raw).hexdigest()
        != pre.V108_VERIFICATION_SHA256
        or verification_v108.get("verification_id") != pre.V108_VERIFICATION_ID
        or freeze_memoized_catalogue_quotient_verification_v108(
            v108_campaign_raw
        )
        != v108_verification_raw
    ):
        _fail("V109 frozen failed V108 evidence changed")
    document = build_dependency_revalidated_quotient_campaign_document_v109(
        pre.campaign_config_v109(),
        preregistration_id=registration.preregistration_id,
        v108_campaign_id=pre.V108_CAMPAIGN_ID,
        v108_verification_id=pre.V108_VERIFICATION_ID,
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
        _fail("frozen V109 campaign changed")
    _CACHE = DependencyRevalidatedQuotientCampaignV109(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_dependency_revalidated_quotient_campaign_v109",
)
