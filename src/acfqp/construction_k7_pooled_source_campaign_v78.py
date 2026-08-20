"""Producer for the preregistered V78 pooled-source diagnostic."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_pooled_source_preregistration_v78 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.pooled_source_campaign_core_v78 import (
    build_pooled_source_campaign_document_v78,
)


CAMPAIGN_ID = "2d3fd7a1470914b5bf945f07b519f3930144a6393635e4ccf9c6d568fdbfcb19"
EXPECTED_CANONICAL_BYTE_COUNT = 1_355_876
EXPECTED_CANONICAL_SHA256 = "1a5feaaf3c3ac9a06d8abf2dcecb3e54f874af76351a693f00dba95c0c721986"


class ConstructionK7PooledSourceCampaignV78Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PooledSourceCampaignV78Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PooledSourceCampaignV78:
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
            or pre.domains.extension_content_id_v78(
                pre.domains.CONSTRUCTION_K7_POOLED_SOURCE_CAMPAIGN_V78_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V78 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PooledSourceCampaignV78 | None = None


def run_pooled_source_campaign_v78() -> PooledSourceCampaignV78:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_pooled_source_preregistration_v78(
        pre.freeze_pooled_source_preregistration_v78()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V78 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V78 frozen template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_pooled_source_campaign_document_v78(
        pre.campaign_config_v78(),
        preregistration.preregistration_id,
        pre.V77_FAILED_CAMPAIGN_ID,
        factor_library,
        residual_artifact.to_document()["compiled_library"],
        template_document["compiled_template_library"],
        template_document["offline_template_source_ground_support_labels"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V78 campaign changed")
    _CACHE = PooledSourceCampaignV78(_ISSUER, raw, identity)
    return _CACHE


def verify_pooled_source_campaign_v78(value: Any) -> PooledSourceCampaignV78:
    if type(value) is not PooledSourceCampaignV78:
        _fail("V78 campaign rejects foreign values")
    value.__post_init__()
    expected = run_pooled_source_campaign_v78()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V78 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_pooled_source_campaign_v78",
    "verify_pooled_source_campaign_v78",
)
