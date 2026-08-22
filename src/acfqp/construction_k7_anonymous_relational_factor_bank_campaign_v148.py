"""Producer for the preregistered V148 relational-prior ablation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_anonymous_relational_factor_bank_preregistration_v148 as pre
from acfqp.anonymous_relational_factor_bank_planning_campaign_core_v148 import (
    build_anonymous_relational_factor_bank_campaign_document_v148,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7AnonymousRelationalFactorBankCampaignV148Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AnonymousRelationalFactorBankCampaignV148Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AnonymousRelationalFactorBankCampaignV148:
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
            or pre.domains.extension_content_id_v148(
                pre.domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_CAMPAIGN_V148_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V148 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: AnonymousRelationalFactorBankCampaignV148 | None = None


def run_anonymous_relational_factor_bank_campaign_v148(
    v145_campaign_raw: bytes,
    v145_verification_raw: bytes,
    v146_bank_raw: bytes,
    v146_verification_raw: bytes,
) -> AnonymousRelationalFactorBankCampaignV148:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V148 attempt is terminal; its identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V148 campaign exists; its identity will not be rerun")
    registration = pre.freeze_anonymous_relational_factor_bank_preregistration_v148(
        v145_campaign_raw,
        v145_verification_raw,
        v146_bank_raw,
        v146_verification_raw,
    )
    document = build_anonymous_relational_factor_bank_campaign_document_v148(
        pre.campaign_config_v148(),
        preregistration_id=registration.preregistration_id,
        bank_raw=v146_bank_raw,
        verification_raw=v146_verification_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V148 campaign changed")
    _CACHE = AnonymousRelationalFactorBankCampaignV148(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_anonymous_relational_factor_bank_campaign_v148",
)
