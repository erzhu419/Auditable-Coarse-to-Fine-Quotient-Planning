"""Producer for the preregistered V152 changed-cardinality campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_ternary_relational_transfer_preregistration_v152 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.ternary_relational_transfer_campaign_core_v152 import build_ternary_relational_transfer_campaign_document_v152


CAMPAIGN_ID = "043437af4d99d554275eaf1f13a5691b1f46a332081b5a1cbe3b75f0e0586783"
EXPECTED_CANONICAL_BYTE_COUNT = 30_756_918
EXPECTED_CANONICAL_SHA256 = "d77f1be15500ac909f81a0b782443a659970b625f534e3c3f0acd460c936091a"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7TernaryRelationalTransferCampaignV152Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TernaryRelationalTransferCampaignV152Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TernaryRelationalTransferCampaignV152:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if self._issuer is not _ISSUER or canonical_json_bytes(document) != self.canonical_bytes or document.get("campaign_id") != self.campaign_id or pre.domains.extension_content_id_v152(pre.domains.CONSTRUCTION_K7_CAMPAIGN_V152_DOMAIN, payload) != self.campaign_id:
            _fail("V152 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_ternary_relational_transfer_campaign_v152(v151_campaign_raw: bytes, v151_verification_raw: bytes, bank_raw: bytes, bank_verification_raw: bytes):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V152 attempt is terminal; its identity will not be rerun")
    registration = pre.freeze_ternary_relational_transfer_preregistration_v152(v151_campaign_raw, v151_verification_raw)
    document = build_ternary_relational_transfer_campaign_document_v152(
        pre.campaign_config_v152(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = TernaryRelationalTransferCampaignV152(_ISSUER, raw, document["campaign_id"])
    return _CACHE


__all__ = ("ATTEMPT_TERMINAL_STATE", "CAMPAIGN_ID", "FAILURE_RECORD_SHA256", "run_ternary_relational_transfer_campaign_v152")
