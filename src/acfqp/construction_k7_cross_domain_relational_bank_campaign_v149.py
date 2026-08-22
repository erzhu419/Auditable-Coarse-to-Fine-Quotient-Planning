"""Producer for the preregistered V149 cross-domain bank campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_cross_domain_relational_bank_preregistration_v149 as pre
from acfqp.cross_domain_relational_factor_bank_campaign_core_v149 import (
    build_cross_domain_relational_factor_bank_campaign_document_v149,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "FROZEN_PREREGISTERED_PLANNER_ACTION_PATH_FAILURE"
FAILURE_RECORD_SHA256: str | None = (
    "0ad197ecd213fa53467ff7252b61e5d750dbc27d675fdf0d5fd8c242ab22458d"
)


class ConstructionK7CrossDomainRelationalBankCampaignV149Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossDomainRelationalBankCampaignV149Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossDomainRelationalBankCampaignV149:
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
            or pre.domains.extension_content_id_v149(
                pre.domains.CONSTRUCTION_K7_CROSS_DOMAIN_RELATIONAL_BANK_CAMPAIGN_V149_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V149 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CrossDomainRelationalBankCampaignV149 | None = None


def run_cross_domain_relational_bank_campaign_v149(
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v148_campaign_raw: bytes,
    v148_verification_raw: bytes,
) -> CrossDomainRelationalBankCampaignV149:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V149 attempt is terminal; its identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V149 campaign exists; its identity will not be rerun")
    registration = pre.freeze_cross_domain_relational_bank_preregistration_v149(
        bank_raw,
        bank_verification_raw,
        v148_campaign_raw,
        v148_verification_raw,
    )
    document = build_cross_domain_relational_factor_bank_campaign_document_v149(
        pre.campaign_config_v149(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    _CACHE = CrossDomainRelationalBankCampaignV149(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_cross_domain_relational_bank_campaign_v149",
)
