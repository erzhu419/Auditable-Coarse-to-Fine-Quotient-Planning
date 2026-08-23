"""One-shot producer for the corrected preregistered V178r1 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_indexed_lazy_invalidation_preregistration_v178r1 as pre
from acfqp.indexed_lazy_invalidation_campaign_core_v178r1 import (
    build_indexed_lazy_invalidation_campaign_v178r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "43e174c7ffd17c5a0e18a584dc638ea2cb48a2695bd2073af0fc80e321d90687"
EXPECTED_CANONICAL_BYTE_COUNT = 43_079_337
EXPECTED_CANONICAL_SHA256 = "e64ed08f2f8aad04e5fa3145570add5a016b01aee55b20be89c89b9de05eb282"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_ID = "0" * 64
V177_CAMPAIGN_ID = "cf9e0bf64ba285d3b1873e5d48636a4de0e68006d7c3e43d761ebbf4a9d5f985"
V177_VERIFICATION_ID = "1f062589b9db53758691431dec327c0d303f20d06bd6b44c647eca02a11c76dd"


class ConstructionK7IndexedLazyInvalidationCampaignV178R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IndexedLazyInvalidationCampaignV178R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class IndexedLazyInvalidationCampaignV178R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_indexed_lazy_invalidation_campaign_v178r1(
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
) -> IndexedLazyInvalidationCampaignV178R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V178r1 attempt is terminal and will not be rerun")
    registration = pre.freeze_indexed_lazy_invalidation_preregistration_v178r1()
    document = build_indexed_lazy_invalidation_campaign_v178r1(
        pre.campaign_config_v178r1(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_raw,
        v177_campaign_id=V177_CAMPAIGN_ID,
        v177_verification_id=V177_VERIFICATION_ID,
    )
    if document.get("registered_gate", {}).get("passed") is not True:
        _fail("V178r1 preregistered scientific gate failed")
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V178r1 frozen campaign changed")
    _CACHE = IndexedLazyInvalidationCampaignV178R1(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_indexed_lazy_invalidation_campaign_v178r1",
)
