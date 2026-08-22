"""Producer for the preregistered V151 relation-keyed campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_relation_keyed_bank_preregistration_v151 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_keyed_relational_bank_campaign_core_v151 import (
    build_relation_keyed_relational_bank_campaign_document_v151,
)


CAMPAIGN_ID = "da305e55c00ff69b3aa240f2536a511eec6d6c3ee07f1418f80281f9ffa64cb0"
EXPECTED_CANONICAL_BYTE_COUNT = 25_536_677
EXPECTED_CANONICAL_SHA256 = "df3c508a7aa9fb8b0fecebb07530b21288818ebf993cf2e1f8b4407e79568a68"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7RelationKeyedBankCampaignV151Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationKeyedBankCampaignV151Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationKeyedBankCampaignV151:
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
            or pre.domains.extension_content_id_v151(
                pre.domains.CONSTRUCTION_K7_CAMPAIGN_V151_DOMAIN, payload
            )
            != self.campaign_id
        ):
            _fail("V151 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: RelationKeyedBankCampaignV151 | None = None


def run_relation_keyed_bank_campaign_v151(
    v150_campaign_raw: bytes,
    v150_verification_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
) -> RelationKeyedBankCampaignV151:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V151 attempt is terminal; its identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V151 campaign exists; its identity will not be rerun")
    registration = pre.freeze_relation_keyed_bank_preregistration_v151(
        v150_campaign_raw, v150_verification_raw
    )
    document = build_relation_keyed_relational_bank_campaign_document_v151(
        pre.campaign_config_v151(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    _CACHE = RelationKeyedBankCampaignV151(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_relation_keyed_bank_campaign_v151",
)
