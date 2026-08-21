"""Producer for the preregistered hierarchical utilization V104 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_hierarchical_utilization_preregistration_v104 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_receipted_utilization_independent_verifier_v103 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V103_VERIFICATION_BYTE_COUNT,
    verify_receipted_utilization_campaign_bytes_v103,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.hierarchical_abstract_utilization_campaign_core_v104 import (
    build_hierarchical_utilization_campaign_document_v104,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7HierarchicalUtilizationCampaignV104Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HierarchicalUtilizationCampaignV104Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class HierarchicalUtilizationCampaignV104:
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
            or pre.domains.extension_content_id_v104(
                pre.domains.CONSTRUCTION_K7_HIERARCHICAL_UTILIZATION_CAMPAIGN_V104_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V104 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: HierarchicalUtilizationCampaignV104 | None = None


def run_hierarchical_utilization_campaign_v104(
    v96_campaign_raw: bytes,
    v96_verification_raw: bytes,
    v103_campaign_raw: bytes,
    v103_verification_raw: bytes,
) -> HierarchicalUtilizationCampaignV104:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V104 campaign exists; same identity will not be rerun")
    registration = pre.verify_hierarchical_utilization_preregistration_v104(
        pre.freeze_hierarchical_utilization_preregistration_v104()
    )
    try:
        verified_v103 = verify_receipted_utilization_campaign_bytes_v103(
            v103_campaign_raw
        )
        verification_v103 = loads_canonical_json(v103_verification_raw)
    except Exception as exc:
        _fail(f"V104 frozen V103 failure predecessor is unreadable: {exc}")
    if (
        verified_v103.get("campaign_id") != pre.V103_CAMPAIGN_ID
        or verified_v103.get("registered_gate_independently_verified") is not False
        or not verified_v103.get("verification_status", "").endswith("GATE_FAILED")
        or canonical_json_bytes(verification_v103) != v103_verification_raw
        or verification_v103.get("verification_id") != pre.V103_VERIFICATION_ID
        or verification_v103.get("registered_gate_independently_verified") is not False
        or len(v103_verification_raw) != V103_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v103_verification_raw).hexdigest()
        != pre.V103_VERIFICATION_SHA256
    ):
        _fail("V104 frozen V103 failure evidence changed")
    source = freeze_post_dependency_source_library_v97(
        v96_campaign_raw, v96_verification_raw
    )
    residual = verify_residual_factor_library_v62(freeze_residual_factor_library_v62())
    if (
        source.source_library_artifact_id
        != pre.previous.previous.previous.previous.SOURCE_LIBRARY_ARTIFACT_ID
        or residual.library_artifact_id
        != pre.previous.previous.previous.previous.V62_LIBRARY_ID
    ):
        _fail("V104 source library changed")
    document = build_hierarchical_utilization_campaign_document_v104(
        pre.campaign_config_v104(),
        preregistration_id=registration.preregistration_id,
        v103_campaign_id=pre.V103_CAMPAIGN_ID,
        v103_verification_id=pre.V103_VERIFICATION_ID,
        source_library_artifact_id=source.source_library_artifact_id,
        factor_library=v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_library=residual.to_document()["compiled_library"],
        structural_prior_library=source.to_document()["compiled_structure_library"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V104 campaign changed")
    _CACHE = HierarchicalUtilizationCampaignV104(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_hierarchical_utilization_campaign_v104")
