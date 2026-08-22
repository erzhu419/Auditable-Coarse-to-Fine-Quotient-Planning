"""Producer for the preregistered V162 certified-switch campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_certified_paid_path_switch_preregistration_v162 as pre
from acfqp.certified_paid_path_switch_campaign_core_v162 import (
    build_certified_paid_path_switch_campaign_v162,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = (
    "84250a94f22de611e57987c88bedbf5d44cc2bfa8f92cdec942ef625daa6b69a"
)
EXPECTED_CANONICAL_BYTE_COUNT = 20_607_166
EXPECTED_CANONICAL_SHA256 = (
    "371b2733c20b9834306be7a9afe191be6149751091a6dbd8496669828bc19073"
)
ATTEMPT_TERMINAL_STATE = "FROZEN_FAILED_REGISTERED_GATE"
FAILURE_RECORD_BYTE_COUNT = 2_561
FAILURE_RECORD_SHA256 = (
    "3f69c16b089ce2bb95a458b1e046dd19c3d262b953397bd79d8579e1f9f96c7a"
)


class ConstructionK7CertifiedPaidPathSwitchCampaignV162Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertifiedPaidPathSwitchCampaignV162Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertifiedPaidPathSwitchCampaignV162:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_certified_paid_path_switch_campaign_v162(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V162 target attempt is terminal and will not be rerun")
    registration = pre.freeze_certified_paid_path_switch_preregistration_v162(
        classifier_receipt_raw
    )
    document = build_certified_paid_path_switch_campaign_v162(
        pre.campaign_config_v162(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = CertifiedPaidPathSwitchCampaignV162(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_certified_paid_path_switch_campaign_v162",
)
