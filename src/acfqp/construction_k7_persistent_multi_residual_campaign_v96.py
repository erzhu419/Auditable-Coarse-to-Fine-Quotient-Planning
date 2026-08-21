"""Producer for the preregistered V96 persistent multi-residual campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.persistent_multi_residual_campaign_core_v96 import (
    build_persistent_multi_residual_campaign_document_v96,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "93d3ae84f1a1f2e1a6cb7dac3f72d5e5ef24646b2e9f864657fee3a242443551"
EXPECTED_CANONICAL_BYTE_COUNT = 1_115_065
EXPECTED_CANONICAL_SHA256 = "7d34c7d96689536937a3e157a74aad597da7a707054326322cf6a19bcbbca4c5"


class ConstructionK7PersistentMultiResidualCampaignV96Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentMultiResidualCampaignV96Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PersistentMultiResidualCampaignV96:
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
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v96(
                pre.domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_CAMPAIGN_V96_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V96 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PersistentMultiResidualCampaignV96 | None = None


def run_persistent_multi_residual_campaign_v96(
) -> PersistentMultiResidualCampaignV96:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V96 campaign exists; same identity will not be rerun")
    preregistration = pre.verify_persistent_multi_residual_preregistration_v96(
        pre.freeze_persistent_multi_residual_preregistration_v96()
    )
    prereg_document = preregistration.to_document()
    predecessors = prereg_document["frozen_predecessors"]
    if (
        predecessors["v62_residual_library_id"] != pre.V62_LIBRARY_ID
        or predecessors["v62_residual_library_sha256"] != pre.V62_LIBRARY_SHA256
        or predecessors["v67_campaign_id"] != pre.V67_CAMPAIGN_ID
        or predecessors["v67_campaign_sha256"] != pre.V67_CAMPAIGN_SHA256
        or predecessors["v67_verification_id"] != pre.V67_VERIFICATION_ID
        or predecessors["v67_verification_sha256"]
        != pre.V67_VERIFICATION_SHA256
        or predecessors["v95_campaign_id"] != pre.V95_CAMPAIGN_ID
        or predecessors["v95_campaign_sha256"] != pre.V95_CAMPAIGN_SHA256
        or predecessors["v95_verification_id"] != pre.V95_VERIFICATION_ID
        or predecessors["v95_verification_sha256"]
        != pre.V95_VERIFICATION_SHA256
    ):
        _fail("V96 frozen predecessor identity changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual_artifact.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V96 residual library predecessor changed")
    factor_library = pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    document = build_persistent_multi_residual_campaign_document_v96(
        pre.campaign_config_v96(),
        preregistration_id=preregistration.preregistration_id,
        v67_campaign_id=pre.V67_CAMPAIGN_ID,
        v67_verification_id=pre.V67_VERIFICATION_ID,
        v95_campaign_id=pre.V95_CAMPAIGN_ID,
        v95_verification_id=pre.V95_VERIFICATION_ID,
        factor_library=factor_library,
        residual_library=residual_artifact.to_document()["compiled_library"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V96 campaign changed")
    _CACHE = PersistentMultiResidualCampaignV96(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_persistent_multi_residual_campaign_v96",
)
