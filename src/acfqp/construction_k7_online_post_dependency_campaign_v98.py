"""Producer for the preregistered online post-dependency V98 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_online_post_dependency_preregistration_v98 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_post_dependency_independent_verifier_v97 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V97_VERIFICATION_BYTE_COUNT,
    verify_post_dependency_campaign_bytes_v97,
)
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.online_post_dependency_campaign_core_v98 import (
    build_online_post_dependency_campaign_document_v98,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0c81232368a76e987b9921e3312fa70653eb5cdbf18e077c8c482aa7bd827f6b"
EXPECTED_CANONICAL_BYTE_COUNT = 2_818_317
EXPECTED_CANONICAL_SHA256 = "102a3cbd116d09b793ecce9e3cb7172ea1044ca1d9cd5ba29186cd78b683a8c3"


class ConstructionK7OnlinePostDependencyCampaignV98Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlinePostDependencyCampaignV98Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OnlinePostDependencyCampaignV98:
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
            or pre.domains.extension_content_id_v98(
                pre.domains.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_CAMPAIGN_V98_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V98 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: OnlinePostDependencyCampaignV98 | None = None


def run_online_post_dependency_campaign_v98(
    v96_campaign_raw: bytes,
    v96_verification_raw: bytes,
    v97_campaign_raw: bytes,
    v97_verification_raw: bytes,
) -> OnlinePostDependencyCampaignV98:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V98 campaign exists; same identity will not be rerun")
    preregistration = pre.verify_online_post_dependency_preregistration_v98(
        pre.freeze_online_post_dependency_preregistration_v98()
    )
    verified_v97 = verify_post_dependency_campaign_bytes_v97(v97_campaign_raw)
    verification = loads_canonical_json(v97_verification_raw)
    if (
        verified_v97.get("campaign_id") != pre.V97_CAMPAIGN_ID
        or type(verification) is not dict
        or canonical_json_bytes(verification) != v97_verification_raw
        or verification.get("verification_id") != pre.V97_VERIFICATION_ID
        or len(v97_verification_raw) != V97_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v97_verification_raw).hexdigest()
        != pre.V97_VERIFICATION_SHA256
    ):
        _fail("V98 frozen V97 predecessor evidence changed")
    source = freeze_post_dependency_source_library_v97(
        v96_campaign_raw, v96_verification_raw
    )
    if source.source_library_artifact_id != pre.SOURCE_LIBRARY_ARTIFACT_ID:
        _fail("V98 structural source library changed")
    residual = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V98 residual library changed")
    document = build_online_post_dependency_campaign_document_v98(
        pre.campaign_config_v98(),
        preregistration_id=preregistration.preregistration_id,
        v97_campaign_id=pre.V97_CAMPAIGN_ID,
        v97_verification_id=pre.V97_VERIFICATION_ID,
        source_library_artifact_id=source.source_library_artifact_id,
        factor_library=v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
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
        _fail("frozen V98 campaign changed")
    _CACHE = OnlinePostDependencyCampaignV98(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_online_post_dependency_campaign_v98")
