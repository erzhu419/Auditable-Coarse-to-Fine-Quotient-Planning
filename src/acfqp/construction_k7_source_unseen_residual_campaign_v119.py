"""Producer for the preregistered source-unseen residual campaign V119."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_source_unseen_residual_preregistration_v119 as pre
from acfqp.construction_k7_fourth_family_inventory_campaign_v118 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V118_CAMPAIGN_BYTE_COUNT,
)
from acfqp.construction_k7_fourth_family_inventory_independent_verifier_v118 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V118_VERIFICATION_BYTE_COUNT,
    freeze_fourth_family_inventory_verification_v118,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.source_unseen_residual_campaign_core_v119 import (
    build_source_unseen_residual_campaign_document_v119,
)


CAMPAIGN_ID = "611c995b93af4016bb85e070f5c1f263d6028ec424cc860e2b67da2bb9aeb3d4"
EXPECTED_CANONICAL_BYTE_COUNT = 4_479_714
EXPECTED_CANONICAL_SHA256 = "22565e57114973fbf1c2fc16d11785eb67c9aebcb5df2c61dc39cc0ba64e301e"


class ConstructionK7SourceUnseenResidualCampaignV119Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceUnseenResidualCampaignV119Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SourceUnseenResidualCampaignV119:
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
            or pre.domains.extension_content_id_v119(
                pre.domains.CONSTRUCTION_K7_SOURCE_UNSEEN_RESIDUAL_CAMPAIGN_V119_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V119 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: SourceUnseenResidualCampaignV119 | None = None


def run_source_unseen_residual_campaign_v119(
    v118_campaign_raw: bytes,
    v118_verification_raw: bytes,
) -> SourceUnseenResidualCampaignV119:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V119 campaign exists; same identity will not be rerun")
    registration = pre.verify_source_unseen_residual_preregistration_v119(
        pre.freeze_source_unseen_residual_preregistration_v119()
    )
    try:
        campaign_v118 = loads_canonical_json(v118_campaign_raw)
        verification_v118 = loads_canonical_json(v118_verification_raw)
    except Exception as exc:
        _fail(f"V119 frozen V118 predecessor is unreadable: {exc}")
    if (
        len(v118_campaign_raw) != V118_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v118_campaign_raw).hexdigest()
        != pre.V118_CAMPAIGN_SHA256
        or campaign_v118.get("campaign_id") != pre.V118_CAMPAIGN_ID
        or canonical_json_bytes(verification_v118) != v118_verification_raw
        or len(v118_verification_raw) != V118_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v118_verification_raw).hexdigest()
        != pre.V118_VERIFICATION_SHA256
        or verification_v118.get("verification_id") != pre.V118_VERIFICATION_ID
        or verification_v118.get("registered_gate_independently_verified")
        is not True
        or freeze_fourth_family_inventory_verification_v118(v118_campaign_raw)
        != v118_verification_raw
    ):
        _fail("V119 frozen successful V118 evidence changed")
    document = build_source_unseen_residual_campaign_document_v119(
        pre.campaign_config_v119(),
        preregistration_id=registration.preregistration_id,
        v118_campaign_id=pre.V118_CAMPAIGN_ID,
        v118_verification_id=pre.V118_VERIFICATION_ID,
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
        _fail("frozen V119 campaign changed")
    _CACHE = SourceUnseenResidualCampaignV119(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_source_unseen_residual_campaign_v119")
