"""Producer for the preregistered V159 third-dynamics campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_third_dynamics_preregistration_v159 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.third_dynamics_joint_factor_query_campaign_core_v159 import (
    build_third_dynamics_joint_factor_query_campaign_v159,
)


CAMPAIGN_ID = "76561d796084acf486f92e55feeca59a2b671cfacd03ddd2eb17230a8503bc55"
EXPECTED_CANONICAL_BYTE_COUNT = 22_440_110
EXPECTED_CANONICAL_SHA256 = "10befc870c0ef542b32dc401e8f6d81bc99314c5ec6cc972ad56d161dad23748"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7ThirdDynamicsCampaignV159Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThirdDynamicsCampaignV159Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ThirdDynamicsCampaignV159:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_third_dynamics_campaign_v159(
    classifier_receipt_raw: bytes, bank_raw: bytes, bank_verification_raw: bytes
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V159 target attempt is terminal and will not be rerun")
    registration = pre.freeze_third_dynamics_preregistration_v159(
        classifier_receipt_raw
    )
    document = build_third_dynamics_joint_factor_query_campaign_v159(
        pre.campaign_config_v159(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = ThirdDynamicsCampaignV159(_ISSUER, raw, document["campaign_id"])
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_third_dynamics_campaign_v159",
)
