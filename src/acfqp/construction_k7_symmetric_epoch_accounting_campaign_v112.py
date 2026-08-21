"""Producer for preregistered symmetric epoch accounting campaign V112."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_symmetric_epoch_accounting_preregistration_v112 as pre
from acfqp.construction_k7_identity_short_circuited_epoch_independent_verifier_v111 import (
    CAMPAIGN_BYTE_COUNT as V111_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V111_VERIFICATION_BYTE_COUNT,
    freeze_identity_short_circuited_epoch_verification_v111,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.symmetric_epoch_accounting_campaign_core_v112 import (
    build_symmetric_epoch_accounting_campaign_document_v112,
)


CAMPAIGN_ID = "9c77611e946310fb08ba1d22afe11326b975f0087c3b2712d39fc2899e09b2a4"
EXPECTED_CANONICAL_BYTE_COUNT = 18_417_315
EXPECTED_CANONICAL_SHA256 = "9c299ce8ed67ba6a8201d2b780b7a76a5cfef888733c5560c160a0d272e1c899"


class ConstructionK7SymmetricEpochAccountingCampaignV112Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SymmetricEpochAccountingCampaignV112Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SymmetricEpochAccountingCampaignV112:
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
            or pre.domains.extension_content_id_v112(
                pre.domains.CONSTRUCTION_K7_SYMMETRIC_EPOCH_ACCOUNTING_CAMPAIGN_V112_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V112 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: SymmetricEpochAccountingCampaignV112 | None = None


def run_symmetric_epoch_accounting_campaign_v112(
    v111_campaign_raw: bytes,
    v111_verification_raw: bytes,
) -> SymmetricEpochAccountingCampaignV112:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V112 campaign exists; same identity will not be rerun")
    registration = pre.verify_symmetric_epoch_accounting_preregistration_v112(
        pre.freeze_symmetric_epoch_accounting_preregistration_v112()
    )
    try:
        campaign_v111 = loads_canonical_json(v111_campaign_raw)
        verification_v111 = loads_canonical_json(v111_verification_raw)
    except Exception as exc:
        _fail(f"V112 frozen failed V111 predecessor is unreadable: {exc}")
    if (
        len(v111_campaign_raw) != V111_CAMPAIGN_BYTE_COUNT
        or campaign_v111.get("campaign_id") != pre.V111_CAMPAIGN_ID
        or canonical_json_bytes(verification_v111) != v111_verification_raw
        or len(v111_verification_raw) != V111_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v111_verification_raw).hexdigest()
        != pre.V111_VERIFICATION_SHA256
        or verification_v111.get("verification_id") != pre.V111_VERIFICATION_ID
        or verification_v111.get("campaign_id") != pre.V111_CAMPAIGN_ID
        or verification_v111.get("registered_gate_independently_verified") is not False
        or verification_v111.get("fresh_successor_required") is not True
        or freeze_identity_short_circuited_epoch_verification_v111(
            v111_campaign_raw
        )
        != v111_verification_raw
    ):
        _fail("V112 frozen failed V111 evidence changed")
    document = build_symmetric_epoch_accounting_campaign_document_v112(
        pre.campaign_config_v112(),
        preregistration_id=registration.preregistration_id,
        v111_campaign_id=pre.V111_CAMPAIGN_ID,
        v111_verification_id=pre.V111_VERIFICATION_ID,
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
        _fail("frozen V112 campaign changed")
    _CACHE = SymmetricEpochAccountingCampaignV112(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_symmetric_epoch_accounting_campaign_v112",
)
