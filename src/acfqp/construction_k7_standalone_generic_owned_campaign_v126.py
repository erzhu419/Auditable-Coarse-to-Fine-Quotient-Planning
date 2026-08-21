"""Producer for the preregistered V126 owned-sequence campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Mapping, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp import construction_k7_standalone_generic_owned_preregistration_v126 as pre
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.standalone_generic_owned_campaign_core_v126 import build_standalone_generic_owned_campaign_document_v126


CAMPAIGN_ID = "c10d9d46c448c2fc12661b24a47886c9b8b4c53f6849609e76f0620f8d21877f"
EXPECTED_CANONICAL_BYTE_COUNT = 2_287_042
EXPECTED_CANONICAL_SHA256 = "4f4277bc8b35297ddc5ff272fbaaa0e37734f1ee0d419b52d825285f8ec36085"


class ConstructionK7StandaloneGenericOwnedCampaignV126Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StandaloneGenericOwnedCampaignV126Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StandaloneGenericOwnedCampaignV126:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v126(
                pre.domains.CONSTRUCTION_K7_STANDALONE_GENERIC_OWNED_CAMPAIGN_V126_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V126 campaign bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_standalone_generic_owned_campaign_v126(
    source_campaign_bytes: Mapping[str, bytes],
    v125_campaign_raw: bytes,
    v125_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V126 campaign exists; same identity will not be rerun")
    source = dict(source_campaign_bytes)
    registration = pre.freeze_standalone_generic_owned_preregistration_v126(
        source, v125_campaign_raw, v125_verification_raw
    )
    library = derive_artifact_factor_projection_v120(source)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V126 preregistered artifact library changed")
    document = build_standalone_generic_owned_campaign_document_v126(
        pre.campaign_config_v126(),
        preregistration_id=registration.preregistration_id,
        v125_campaign_id=pre.V125_CAMPAIGN_ID,
        v125_verification_id=pre.V125_VERIFICATION_ID,
        artifact_factor_library=library,
        source_campaign_bytes=source,
        strict_complete_factor_library=v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V126 campaign changed")
    _CACHE = StandaloneGenericOwnedCampaignV126(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_standalone_generic_owned_campaign_v126")
