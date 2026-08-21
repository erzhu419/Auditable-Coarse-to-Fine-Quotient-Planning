"""Producer for the preregistered V91 reference-aligned source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_reference_aligned_source_preregistration_v91 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.reference_aligned_source_campaign_core_v91 import (
    build_reference_aligned_source_campaign_document_v91,
)


CAMPAIGN_ID = "e9d6fd70a8cdf0d023dfaa5a3dfa60423a777632baef7b610b28da11024d7373"
EXPECTED_CANONICAL_BYTE_COUNT = 561_886
EXPECTED_CANONICAL_SHA256 = "ba35b013bca09e49a8d533dd86df0ef4d4e7b2c82862598942bb40a8a87f3bb9"


class ConstructionK7ReferenceAlignedSourceCampaignV91Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReferenceAlignedSourceCampaignV91Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReferenceAlignedSourceCampaignV91:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v91(
                pre.domains.CONSTRUCTION_K7_REFERENCE_ALIGNED_CAMPAIGN_V91_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V91 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ReferenceAlignedSourceCampaignV91 | None = None


def run_reference_aligned_source_campaign_v91() -> ReferenceAlignedSourceCampaignV91:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V91 outcome exists; same identity will not be rerun")
    preregistration = pre.verify_reference_aligned_source_preregistration_v91(
        pre.freeze_reference_aligned_source_preregistration_v91()
    )
    residual = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    ).to_document()
    template = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    ).to_document()
    factor_library = (
        v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_reference_aligned_source_campaign_document_v91(
        pre.campaign_config_v91(),
        preregistration.preregistration_id,
        pre.V90_VERIFICATION_ID,
        factor_library,
        residual["compiled_library"],
        template["compiled_template_library"],
        template["offline_template_source_ground_support_labels"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91 campaign changed")
    _CACHE = ReferenceAlignedSourceCampaignV91(_ISSUER, raw, identity)
    return _CACHE


def verify_reference_aligned_source_campaign_v91(
    value: Any,
) -> ReferenceAlignedSourceCampaignV91:
    if type(value) is not ReferenceAlignedSourceCampaignV91:
        _fail("V91 campaign rejects foreign values")
    value.__post_init__()
    expected = run_reference_aligned_source_campaign_v91()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V91 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_reference_aligned_source_campaign_v91",
    "verify_reference_aligned_source_campaign_v91",
)
