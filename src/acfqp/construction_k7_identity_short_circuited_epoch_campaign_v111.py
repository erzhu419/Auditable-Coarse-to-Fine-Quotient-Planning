"""Producer for preregistered identity-short-circuited epoch campaign V111."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_identity_short_circuited_epoch_preregistration_v111 as pre
from acfqp.construction_k7_epoch_indexed_quotient_independent_verifier_v110 import (
    CAMPAIGN_BYTE_COUNT as V110_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V110_VERIFICATION_BYTE_COUNT,
    freeze_epoch_indexed_quotient_verification_v110,
    verify_epoch_indexed_quotient_campaign_bytes_v110,
)
from acfqp.identity_short_circuited_epoch_campaign_core_v111 import (
    build_identity_short_circuited_epoch_campaign_document_v111,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "378f333008191bdb338182c787547aeb80f4fa27b612f499043b20163a6327f5"
EXPECTED_CANONICAL_BYTE_COUNT = 19_377_728
EXPECTED_CANONICAL_SHA256 = "9aa43e94e150c085c155db2115ce01cc1447b7547f72b29c128392b972072efc"


class ConstructionK7IdentityShortCircuitedEpochCampaignV111Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IdentityShortCircuitedEpochCampaignV111Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class IdentityShortCircuitedEpochCampaignV111:
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
            or pre.domains.extension_content_id_v111(
                pre.domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_CAMPAIGN_V111_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V111 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: IdentityShortCircuitedEpochCampaignV111 | None = None


def run_identity_short_circuited_epoch_campaign_v111(
    v110_campaign_raw: bytes,
    v110_verification_raw: bytes,
) -> IdentityShortCircuitedEpochCampaignV111:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V111 campaign exists; same identity will not be rerun")
    registration = pre.verify_identity_short_circuited_epoch_preregistration_v111(
        pre.freeze_identity_short_circuited_epoch_preregistration_v111()
    )
    try:
        verified_v110 = verify_epoch_indexed_quotient_campaign_bytes_v110(
            v110_campaign_raw
        )
        verification_v110 = loads_canonical_json(v110_verification_raw)
    except Exception as exc:
        _fail(f"V111 frozen failed V110 predecessor is unreadable: {exc}")
    if (
        len(v110_campaign_raw) != V110_CAMPAIGN_BYTE_COUNT
        or verified_v110.get("campaign_id") != pre.V110_CAMPAIGN_ID
        or verified_v110.get("registered_gate_independently_verified") is not False
        or verified_v110.get("fresh_successor_required") is not True
        or canonical_json_bytes(verification_v110) != v110_verification_raw
        or len(v110_verification_raw) != V110_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v110_verification_raw).hexdigest()
        != pre.V110_VERIFICATION_SHA256
        or verification_v110.get("verification_id") != pre.V110_VERIFICATION_ID
        or freeze_epoch_indexed_quotient_verification_v110(v110_campaign_raw)
        != v110_verification_raw
    ):
        _fail("V111 frozen failed V110 evidence changed")
    document = build_identity_short_circuited_epoch_campaign_document_v111(
        pre.campaign_config_v111(),
        preregistration_id=registration.preregistration_id,
        v110_campaign_id=pre.V110_CAMPAIGN_ID,
        v110_verification_id=pre.V110_VERIFICATION_ID,
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
        _fail("frozen V111 campaign changed")
    _CACHE = IdentityShortCircuitedEpochCampaignV111(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_identity_short_circuited_epoch_campaign_v111",
)
