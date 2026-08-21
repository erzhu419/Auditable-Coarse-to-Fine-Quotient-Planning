"""Producer for the preregistered actual quotient-utilization V105 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_quotient_utilization_preregistration_v105 as pre
from acfqp.actual_quotient_utilization_campaign_core_v105 import (
    build_actual_quotient_utilization_campaign_document_v105,
)
from acfqp.construction_k7_hierarchical_utilization_independent_verifier_v104 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V104_VERIFICATION_BYTE_COUNT,
    verify_hierarchical_utilization_campaign_bytes_v104,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7QuotientUtilizationCampaignV105Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QuotientUtilizationCampaignV105Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class QuotientUtilizationCampaignV105:
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
            or pre.domains.extension_content_id_v105(
                pre.domains.CONSTRUCTION_K7_QUOTIENT_UTILIZATION_CAMPAIGN_V105_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V105 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: QuotientUtilizationCampaignV105 | None = None


def run_quotient_utilization_campaign_v105(
    v104_campaign_raw: bytes,
    v104_verification_raw: bytes,
) -> QuotientUtilizationCampaignV105:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V105 campaign exists; same identity will not be rerun")
    registration = pre.verify_quotient_utilization_preregistration_v105(
        pre.freeze_quotient_utilization_preregistration_v105()
    )
    try:
        verified_v104 = verify_hierarchical_utilization_campaign_bytes_v104(
            v104_campaign_raw
        )
        verification_v104 = loads_canonical_json(v104_verification_raw)
    except Exception as exc:
        _fail(f"V105 frozen V104 predecessor is unreadable: {exc}")
    if (
        verified_v104.get("campaign_id") != pre.V104_CAMPAIGN_ID
        or verified_v104.get("registered_gate_independently_verified") is not True
        or verified_v104.get("partial_world_model_primary_ordering_verified")
        is not True
        or canonical_json_bytes(verification_v104) != v104_verification_raw
        or verification_v104.get("verification_id") != pre.V104_VERIFICATION_ID
        or verification_v104.get("registered_gate_independently_verified")
        is not True
        or len(v104_verification_raw) != V104_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v104_verification_raw).hexdigest()
        != pre.V104_VERIFICATION_SHA256
    ):
        _fail("V105 frozen V104 evidence changed")
    document = build_actual_quotient_utilization_campaign_document_v105(
        pre.campaign_config_v105(),
        preregistration_id=registration.preregistration_id,
        v104_campaign_id=pre.V104_CAMPAIGN_ID,
        v104_verification_id=pre.V104_VERIFICATION_ID,
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
        _fail("frozen V105 campaign changed")
    _CACHE = QuotientUtilizationCampaignV105(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_quotient_utilization_campaign_v105")
