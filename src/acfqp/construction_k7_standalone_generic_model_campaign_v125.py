"""Producer for the preregistered standalone V125 model campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp import construction_k7_standalone_generic_model_preregistration_v125 as pre
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.standalone_generic_model_campaign_core_v125 import build_standalone_generic_model_campaign_document_v125


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7StandaloneGenericModelCampaignV125Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StandaloneGenericModelCampaignV125Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StandaloneGenericModelCampaignV125:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if self._issuer is not _ISSUER or canonical_json_bytes(document) != self.canonical_bytes or document.get("campaign_id") != self.campaign_id or pre.domains.extension_content_id_v125(pre.domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_CAMPAIGN_V125_DOMAIN, payload) != self.campaign_id:
            _fail("V125 campaign bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_standalone_generic_model_campaign_v125(source_campaign_bytes: Mapping[str, bytes], v124_campaign_raw: bytes, v124_verification_raw: bytes):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V125 campaign exists; same identity will not be rerun")
    source = dict(source_campaign_bytes)
    registration = pre.freeze_standalone_generic_model_preregistration_v125(source, v124_campaign_raw, v124_verification_raw)
    library = derive_artifact_factor_projection_v120(source)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V125 preregistered artifact library changed")
    document = build_standalone_generic_model_campaign_document_v125(
        pre.campaign_config_v125(),
        preregistration_id=registration.preregistration_id,
        v124_campaign_id=pre.V124_CAMPAIGN_ID,
        v124_verification_id=pre.V124_VERIFICATION_ID,
        artifact_factor_library=library,
        source_campaign_bytes=source,
        strict_complete_factor_library=v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
    )
    raw, identity = canonical_json_bytes(document), document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (identity != CAMPAIGN_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("frozen V125 campaign changed")
    _CACHE = StandaloneGenericModelCampaignV125(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_standalone_generic_model_campaign_v125")
