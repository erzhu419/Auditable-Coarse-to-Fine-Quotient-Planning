"""Producer for the preregistered V164 sample-tax replication."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_sample_tax_replication_preregistration_v164 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.sample_tax_replication_campaign_core_v164 import (
    build_sample_tax_replication_campaign_v164,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"


class ConstructionK7SampleTaxReplicationCampaignV164Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SampleTaxReplicationCampaignV164Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SampleTaxReplicationCampaignV164:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_sample_tax_replication_campaign_v164(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V164 target attempt is terminal and will not be rerun")
    registration = pre.freeze_sample_tax_replication_preregistration_v164()
    document = build_sample_tax_replication_campaign_v164(
        pre.campaign_config_v164(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = SampleTaxReplicationCampaignV164(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "run_sample_tax_replication_campaign_v164",
)
