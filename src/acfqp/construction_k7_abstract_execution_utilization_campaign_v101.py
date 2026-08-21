"""Producer for the preregistered abstract execution-utilization campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_abstract_execution_utilization_preregistration_v101 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.abstract_execution_utilization_campaign_core_v101 import (
    build_abstract_execution_utilization_campaign_document_v101,
)
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_sequence_wide_agreement_shielded_independent_verifier_v100 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V100_VERIFICATION_BYTE_COUNT,
    verify_sequence_wide_agreement_shielded_campaign_bytes_v100,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7AbstractExecutionUtilizationCampaignV101Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractExecutionUtilizationCampaignV101Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AbstractExecutionUtilizationCampaignV101:
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
            or pre.domains.extension_content_id_v101(
                pre.domains.CONSTRUCTION_K7_ABSTRACT_EXECUTION_UTILIZATION_CAMPAIGN_V101_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V101 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: AbstractExecutionUtilizationCampaignV101 | None = None


def run_abstract_execution_utilization_campaign_v101(
    v96_campaign_raw: bytes,
    v96_verification_raw: bytes,
    v100_campaign_raw: bytes,
    v100_verification_raw: bytes,
) -> AbstractExecutionUtilizationCampaignV101:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V101 campaign exists; same identity will not be rerun")
    preregistration = pre.verify_abstract_execution_utilization_preregistration_v101(
        pre.freeze_abstract_execution_utilization_preregistration_v101()
    )
    try:
        verified_v100 = verify_sequence_wide_agreement_shielded_campaign_bytes_v100(
            v100_campaign_raw
        )
        verification = loads_canonical_json(v100_verification_raw)
    except Exception as exc:
        _fail(f"V101 frozen V100 predecessor is unreadable: {exc}")
    if (
        verified_v100.get("campaign_id") != pre.V100_CAMPAIGN_ID
        or verified_v100.get("registered_v100_gate_passed") is not True
        or type(verification) is not dict
        or canonical_json_bytes(verification) != v100_verification_raw
        or verification.get("verification_id") != pre.V100_VERIFICATION_ID
        or len(v100_verification_raw) != V100_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v100_verification_raw).hexdigest()
        != pre.V100_VERIFICATION_SHA256
    ):
        _fail("V101 frozen V100 predecessor evidence changed")
    source = freeze_post_dependency_source_library_v97(
        v96_campaign_raw, v96_verification_raw
    )
    if source.source_library_artifact_id != pre.previous.SOURCE_LIBRARY_ARTIFACT_ID:
        _fail("V101 structural source library changed")
    residual = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual.library_artifact_id != pre.previous.V62_LIBRARY_ID:
        _fail("V101 residual library changed")
    document = build_abstract_execution_utilization_campaign_document_v101(
        pre.campaign_config_v101(),
        preregistration_id=preregistration.preregistration_id,
        v100_campaign_id=pre.V100_CAMPAIGN_ID,
        v100_verification_id=pre.V100_VERIFICATION_ID,
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
        _fail("frozen V101 campaign changed")
    _CACHE = AbstractExecutionUtilizationCampaignV101(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_abstract_execution_utilization_campaign_v101")
