"""Producer for preregistered fourth-family inventory transfer V118."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_fourth_family_inventory_preregistration_v118 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_dependency_derived_program_branch_campaign_v117 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V117_CAMPAIGN_BYTE_COUNT,
)
from acfqp.construction_k7_dependency_derived_program_branch_independent_verifier_v117 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V117_VERIFICATION_BYTE_COUNT,
    freeze_dependency_derived_program_branch_verification_v117,
)
from acfqp.fourth_family_inventory_campaign_core_v118 import (
    build_fourth_family_inventory_campaign_document_v118,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0ab03c02a8b5b795860c5c96943204f8553fc6836e7dab92ef753c1fe6d86df1"
EXPECTED_CANONICAL_BYTE_COUNT = 2_986_273
EXPECTED_CANONICAL_SHA256 = "9afbade52f4b553ad5696e769ba6f8f1faced07fbb11b07b0f8a59991961e19d"


class ConstructionK7FourthFamilyInventoryCampaignV118Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FourthFamilyInventoryCampaignV118Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FourthFamilyInventoryCampaignV118:
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
            or pre.domains.extension_content_id_v118(
                pre.domains.CONSTRUCTION_K7_FOURTH_FAMILY_INVENTORY_CAMPAIGN_V118_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V118 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: FourthFamilyInventoryCampaignV118 | None = None


def run_fourth_family_inventory_campaign_v118(
    v117_campaign_raw: bytes,
    v117_verification_raw: bytes,
) -> FourthFamilyInventoryCampaignV118:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V118 campaign exists; same identity will not be rerun")
    registration = pre.verify_fourth_family_inventory_preregistration_v118(
        pre.freeze_fourth_family_inventory_preregistration_v118()
    )
    try:
        campaign_v117 = loads_canonical_json(v117_campaign_raw)
        verification_v117 = loads_canonical_json(v117_verification_raw)
    except Exception as exc:
        _fail(f"V118 frozen V117 predecessor is unreadable: {exc}")
    if (
        len(v117_campaign_raw) != V117_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v117_campaign_raw).hexdigest()
        != pre.V117_CAMPAIGN_SHA256
        or campaign_v117.get("campaign_id") != pre.V117_CAMPAIGN_ID
        or canonical_json_bytes(verification_v117) != v117_verification_raw
        or len(v117_verification_raw) != V117_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v117_verification_raw).hexdigest()
        != pre.V117_VERIFICATION_SHA256
        or verification_v117.get("verification_id") != pre.V117_VERIFICATION_ID
        or verification_v117.get("registered_gate_independently_verified")
        is not True
        or freeze_dependency_derived_program_branch_verification_v117(
            v117_campaign_raw
        )
        != v117_verification_raw
    ):
        _fail("V118 frozen successful V117 evidence changed")
    document = build_fourth_family_inventory_campaign_document_v118(
        pre.campaign_config_v118(),
        preregistration_id=registration.preregistration_id,
        v117_campaign_id=pre.V117_CAMPAIGN_ID,
        v117_verification_id=pre.V117_VERIFICATION_ID,
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
        _fail("frozen V118 campaign changed")
    _CACHE = FourthFamilyInventoryCampaignV118(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_fourth_family_inventory_campaign_v118")
