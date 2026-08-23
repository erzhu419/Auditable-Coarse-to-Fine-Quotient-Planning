"""One-shot producer for the preregistered V177 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_reverse_index_only_invalidation_preregistration_v177 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.reverse_index_only_invalidation_campaign_core_v177 import (
    build_reverse_index_only_invalidation_campaign_v177,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_ID = "0" * 64
V176_CAMPAIGN_ID = "8d6d1348e67084b449debf5671cb568eb6b048eb56358bf3bbe20c4161255953"
V176_VERIFICATION_ID = "ac6b3a604c49423cbac35154bf1a0dbea15b65e6723e9471bd9990822de1968f"


class ConstructionK7ReverseIndexOnlyInvalidationCampaignV177Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReverseIndexOnlyInvalidationCampaignV177Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReverseIndexOnlyInvalidationCampaignV177:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_reverse_index_only_invalidation_campaign_v177(
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
) -> ReverseIndexOnlyInvalidationCampaignV177:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V177 attempt is terminal and will not be rerun")
    registration = pre.freeze_reverse_index_only_invalidation_preregistration_v177()
    document = build_reverse_index_only_invalidation_campaign_v177(
        pre.campaign_config_v177(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_raw,
        v176_campaign_id=V176_CAMPAIGN_ID,
        v176_verification_id=V176_VERIFICATION_ID,
    )
    if document.get("registered_gate", {}).get("passed") is not True:
        _fail("V177 preregistered scientific gate failed")
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V177 frozen campaign changed")
    _CACHE = ReverseIndexOnlyInvalidationCampaignV177(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_reverse_index_only_invalidation_campaign_v177",
)
