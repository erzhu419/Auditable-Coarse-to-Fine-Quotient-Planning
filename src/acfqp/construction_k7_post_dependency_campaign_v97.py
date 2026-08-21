"""Producer for the preregistered V97 post-dependency campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_post_dependency_preregistration_v97 as pre
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.post_dependency_campaign_core_v97 import (
    build_post_dependency_campaign_document_v97,
)


CAMPAIGN_ID = "b132245b0827898cb497232ed82b911fc17bebc4a30e981a7b080895abc8bf3e"
EXPECTED_CANONICAL_BYTE_COUNT = 2_361_088
EXPECTED_CANONICAL_SHA256 = "dc5bd10f193e98038ef2ced4d0ab7558deb35200104195de8299ded1add32afc"


class ConstructionK7PostDependencyCampaignV97Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PostDependencyCampaignV97Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PostDependencyCampaignV97:
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
            or pre.domains.extension_content_id_v97(
                pre.domains.CONSTRUCTION_K7_POST_DEPENDENCY_CAMPAIGN_V97_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V97 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: PostDependencyCampaignV97 | None = None


def run_post_dependency_campaign_v97(
    v96_campaign_raw: bytes,
    v96_verification_raw: bytes,
) -> PostDependencyCampaignV97:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V97 campaign exists; same identity will not be rerun")
    preregistration = pre.verify_post_dependency_preregistration_v97(
        pre.freeze_post_dependency_preregistration_v97()
    )
    source = freeze_post_dependency_source_library_v97(
        v96_campaign_raw, v96_verification_raw
    )
    if source.source_library_artifact_id != pre.SOURCE_LIBRARY_ARTIFACT_ID:
        _fail("V97 source dependency library changed")
    residual = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V97 residual library changed")
    document = build_post_dependency_campaign_document_v97(
        pre.campaign_config_v97(),
        preregistration_id=preregistration.preregistration_id,
        v96_campaign_id=pre.V96_CAMPAIGN_ID,
        v96_verification_id=pre.V96_VERIFICATION_ID,
        source_library_artifact_id=source.source_library_artifact_id,
        factor_library=pre.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_library=residual.to_document()["compiled_library"],
        structural_prior_library=source.to_document()[
            "compiled_structure_library"
        ],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V97 campaign changed")
    _CACHE = PostDependencyCampaignV97(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_post_dependency_campaign_v97")
