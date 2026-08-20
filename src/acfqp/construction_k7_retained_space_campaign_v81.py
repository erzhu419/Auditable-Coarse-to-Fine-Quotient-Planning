"""Producer for the preregistered V81 retained-version-space source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_retained_space_preregistration_v81 as pre
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
from acfqp.retained_version_space_source_campaign_core_v81 import (
    build_retained_version_space_source_campaign_document_v81,
)


CAMPAIGN_ID = "66a4d06b58156e24dedb4ccd56741d99444ac29b2b3b9cb8c806dc338b5571b0"
EXPECTED_CANONICAL_BYTE_COUNT = 1_181_184
EXPECTED_CANONICAL_SHA256 = "a438f9b77e47eb40496addd58cfde7c2cd96b824c66e668d87d7129b7cfcb5be"


class ConstructionK7RetainedSpaceCampaignV81Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RetainedSpaceCampaignV81Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RetainedSpaceCampaignV81:
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
            or pre.domains.extension_content_id_v81(
                pre.domains.CONSTRUCTION_K7_RETAINED_SPACE_CAMPAIGN_V81_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V81 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: RetainedSpaceCampaignV81 | None = None


def run_retained_space_campaign_v81() -> RetainedSpaceCampaignV81:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_retained_space_preregistration_v81(
        pre.freeze_retained_space_preregistration_v81()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V81 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V81 frozen template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_retained_version_space_source_campaign_document_v81(
        pre.campaign_config_v81(),
        preregistration.preregistration_id,
        pre.V80_FAILED_CAMPAIGN_ID,
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
        _fail("frozen V81 campaign changed")
    _CACHE = RetainedSpaceCampaignV81(_ISSUER, raw, identity)
    return _CACHE


def verify_retained_space_campaign_v81(
    value: Any,
) -> RetainedSpaceCampaignV81:
    if type(value) is not RetainedSpaceCampaignV81:
        _fail("V81 campaign rejects foreign values")
    value.__post_init__()
    expected = run_retained_space_campaign_v81()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V81 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_retained_space_campaign_v81",
    "verify_retained_space_campaign_v81",
)
