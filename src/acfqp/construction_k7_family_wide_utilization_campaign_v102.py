"""Producer for the preregistered family-wide utilization campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_family_wide_utilization_preregistration_v102 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_abstract_execution_utilization_independent_verifier_v101 import EXPECTED_CANONICAL_BYTE_COUNT as V101_VERIFICATION_BYTE_COUNT, verify_abstract_execution_utilization_campaign_bytes_v101
from acfqp.construction_k7_post_dependency_source_library_v97 import freeze_post_dependency_source_library_v97
from acfqp.construction_k7_residual_factor_library_v62 import freeze_residual_factor_library_v62, verify_residual_factor_library_v62
from acfqp.family_wide_abstract_utilization_campaign_core_v102 import build_family_wide_utilization_campaign_document_v102
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7FamilyWideUtilizationCampaignV102Error(ValueError): pass
def _fail(message: str) -> NoReturn: raise ConstructionK7FamilyWideUtilizationCampaignV102Error(message)
_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FamilyWideUtilizationCampaignV102:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    def __post_init__(self) -> None:
        doc = loads_canonical_json(self.canonical_bytes); payload = {k: v for k, v in doc.items() if k != "campaign_id"}
        if self._issuer is not _ISSUER or canonical_json_bytes(doc) != self.canonical_bytes or doc.get("campaign_id") != self.campaign_id or pre.domains.extension_content_id_v102(pre.domains.CONSTRUCTION_K7_FAMILY_WIDE_UTILIZATION_CAMPAIGN_V102_DOMAIN, payload) != self.campaign_id: _fail("V102 campaign bytes or issuer changed")
    def to_document(self) -> dict[str, Any]: return loads_canonical_json(self.canonical_bytes)


_CACHE: FamilyWideUtilizationCampaignV102 | None = None


def run_family_wide_utilization_campaign_v102(v96_campaign_raw: bytes, v96_verification_raw: bytes, v101_campaign_raw: bytes, v101_verification_raw: bytes) -> FamilyWideUtilizationCampaignV102:
    global _CACHE
    if _CACHE is not None: return _CACHE
    if CAMPAIGN_ID != "0" * 64: _fail("frozen V102 campaign exists; same identity will not be rerun")
    registration = pre.verify_family_wide_utilization_preregistration_v102(pre.freeze_family_wide_utilization_preregistration_v102())
    try:
        verified = verify_abstract_execution_utilization_campaign_bytes_v101(v101_campaign_raw); verification = loads_canonical_json(v101_verification_raw)
    except Exception as exc: _fail(f"V102 frozen V101 predecessor is unreadable: {exc}")
    if verified.get("campaign_id") != pre.V101_CAMPAIGN_ID or verified.get("v101_registered_gate_passed") is not False or canonical_json_bytes(verification) != v101_verification_raw or verification.get("verification_id") != pre.V101_VERIFICATION_ID or len(v101_verification_raw) != V101_VERIFICATION_BYTE_COUNT or hashlib.sha256(v101_verification_raw).hexdigest() != pre.V101_VERIFICATION_SHA256: _fail("V102 frozen V101 failure evidence changed")
    source = freeze_post_dependency_source_library_v97(v96_campaign_raw, v96_verification_raw)
    residual = verify_residual_factor_library_v62(freeze_residual_factor_library_v62())
    if source.source_library_artifact_id != pre.previous.previous.SOURCE_LIBRARY_ARTIFACT_ID or residual.library_artifact_id != pre.previous.previous.V62_LIBRARY_ID: _fail("V102 source library changed")
    doc = build_family_wide_utilization_campaign_document_v102(pre.campaign_config_v102(), preregistration_id=registration.preregistration_id, v101_campaign_id=pre.V101_CAMPAIGN_ID, v101_verification_id=pre.V101_VERIFICATION_ID, source_library_artifact_id=source.source_library_artifact_id, factor_library=v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY, residual_library=residual.to_document()["compiled_library"], structural_prior_library=source.to_document()["compiled_structure_library"])
    raw = canonical_json_bytes(doc); identity = doc["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (identity != CAMPAIGN_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256): _fail("frozen V102 campaign changed")
    _CACHE = FamilyWideUtilizationCampaignV102(_ISSUER, raw, identity); return _CACHE


__all__ = ("CAMPAIGN_ID", "run_family_wide_utilization_campaign_v102")
