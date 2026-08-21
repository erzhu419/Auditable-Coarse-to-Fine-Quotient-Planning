"""Producer for preregistered dependency-derived branch retention V117."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_dependency_derived_program_branch_preregistration_v117 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_cross_epoch_program_branch_campaign_v116 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V116_CAMPAIGN_BYTE_COUNT,
)
from acfqp.construction_k7_cross_epoch_program_branch_independent_verifier_v116 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V116_VERIFICATION_BYTE_COUNT,
    freeze_cross_epoch_program_branch_verification_v116,
)
from acfqp.dependency_derived_program_branch_campaign_core_v117 import (
    build_dependency_derived_program_branch_campaign_document_v117,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "5817b88896699206fcb08ed64111fc993691515fd0461e518c956a04de283b9d"
EXPECTED_CANONICAL_BYTE_COUNT = 7_794_238
EXPECTED_CANONICAL_SHA256 = "061a653cf1048fe01420a3159d4389b9b81eb573f97c5acfbd66fcf618d60039"


class ConstructionK7DependencyDerivedProgramBranchCampaignV117Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DependencyDerivedProgramBranchCampaignV117Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class DependencyDerivedProgramBranchCampaignV117:
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
            or pre.domains.extension_content_id_v117(
                pre.domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_CAMPAIGN_V117_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V117 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: DependencyDerivedProgramBranchCampaignV117 | None = None


def run_dependency_derived_program_branch_campaign_v117(
    v116_campaign_raw: bytes,
    v116_verification_raw: bytes,
) -> DependencyDerivedProgramBranchCampaignV117:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V117 campaign exists; same identity will not be rerun")
    registration = pre.verify_dependency_derived_program_branch_preregistration_v117(
        pre.freeze_dependency_derived_program_branch_preregistration_v117()
    )
    try:
        campaign_v116 = loads_canonical_json(v116_campaign_raw)
        verification_v116 = loads_canonical_json(v116_verification_raw)
    except Exception as exc:
        _fail(f"V117 frozen V116 predecessor is unreadable: {exc}")
    if (
        len(v116_campaign_raw) != V116_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v116_campaign_raw).hexdigest()
        != pre.V116_CAMPAIGN_SHA256
        or campaign_v116.get("campaign_id") != pre.V116_CAMPAIGN_ID
        or canonical_json_bytes(verification_v116) != v116_verification_raw
        or len(v116_verification_raw) != V116_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v116_verification_raw).hexdigest()
        != pre.V116_VERIFICATION_SHA256
        or verification_v116.get("verification_id") != pre.V116_VERIFICATION_ID
        or verification_v116.get("registered_gate_independently_verified")
        is not True
        or freeze_cross_epoch_program_branch_verification_v116(v116_campaign_raw)
        != v116_verification_raw
    ):
        _fail("V117 frozen successful V116 evidence changed")
    document = build_dependency_derived_program_branch_campaign_document_v117(
        pre.campaign_config_v117(),
        preregistration_id=registration.preregistration_id,
        v116_campaign_id=pre.V116_CAMPAIGN_ID,
        v116_verification_id=pre.V116_VERIFICATION_ID,
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V117 campaign changed")
    _CACHE = DependencyDerivedProgramBranchCampaignV117(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_dependency_derived_program_branch_campaign_v117",
)
