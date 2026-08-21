"""Producer for preregistered three-family incremental transfer V114."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_three_family_incremental_successor_preregistration_v114 as pre
from acfqp.construction_k7_incremental_abstract_successor_independent_verifier_v113 import (
    CAMPAIGN_BYTE_COUNT as V113_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V113_VERIFICATION_BYTE_COUNT,
    freeze_incremental_abstract_successor_verification_v113,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.three_family_incremental_successor_campaign_core_v114 import (
    build_three_family_incremental_successor_campaign_document_v114,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7ThreeFamilyIncrementalSuccessorCampaignV114Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThreeFamilyIncrementalSuccessorCampaignV114Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ThreeFamilyIncrementalSuccessorCampaignV114:
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
            or pre.domains.extension_content_id_v114(
                pre.domains.CONSTRUCTION_K7_THREE_FAMILY_INCREMENTAL_SUCCESSOR_CAMPAIGN_V114_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V114 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: ThreeFamilyIncrementalSuccessorCampaignV114 | None = None


def run_three_family_incremental_successor_campaign_v114(
    v113_campaign_raw: bytes,
    v113_verification_raw: bytes,
) -> ThreeFamilyIncrementalSuccessorCampaignV114:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V114 campaign exists; same identity will not be rerun")
    registration = pre.verify_three_family_incremental_successor_preregistration_v114(
        pre.freeze_three_family_incremental_successor_preregistration_v114()
    )
    try:
        campaign_v113 = loads_canonical_json(v113_campaign_raw)
        verification_v113 = loads_canonical_json(v113_verification_raw)
    except Exception as exc:
        _fail(f"V114 frozen V113 predecessor is unreadable: {exc}")
    if (
        len(v113_campaign_raw) != V113_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v113_campaign_raw).hexdigest()
        != pre.V113_CAMPAIGN_SHA256
        or campaign_v113.get("campaign_id") != pre.V113_CAMPAIGN_ID
        or canonical_json_bytes(verification_v113) != v113_verification_raw
        or len(v113_verification_raw) != V113_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v113_verification_raw).hexdigest()
        != pre.V113_VERIFICATION_SHA256
        or verification_v113.get("verification_id") != pre.V113_VERIFICATION_ID
        or verification_v113.get("registered_gate_independently_verified") is not True
        or freeze_incremental_abstract_successor_verification_v113(
            v113_campaign_raw
        )
        != v113_verification_raw
    ):
        _fail("V114 frozen successful V113 evidence changed")
    document = build_three_family_incremental_successor_campaign_document_v114(
        pre.campaign_config_v114(),
        preregistration_id=registration.preregistration_id,
        v113_campaign_id=pre.V113_CAMPAIGN_ID,
        v113_verification_id=pre.V113_VERIFICATION_ID,
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
        _fail("frozen V114 campaign changed")
    _CACHE = ThreeFamilyIncrementalSuccessorCampaignV114(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_three_family_incremental_successor_campaign_v114",
)
