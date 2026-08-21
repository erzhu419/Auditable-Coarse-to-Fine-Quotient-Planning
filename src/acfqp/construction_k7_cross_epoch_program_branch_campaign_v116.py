"""Producer for preregistered cross-epoch program reuse V116."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_cross_epoch_program_branch_preregistration_v116 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_projected_program_memo_campaign_v115 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V115_CAMPAIGN_BYTE_COUNT,
)
from acfqp.construction_k7_projected_program_memo_independent_verifier_v115 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V115_VERIFICATION_BYTE_COUNT,
    freeze_projected_program_memo_verification_v115,
)
from acfqp.cross_epoch_program_branch_campaign_core_v116 import (
    build_cross_epoch_program_branch_campaign_document_v116,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "2ffeebf8f989a944afce3144aeed8aeba4eda529bce3f3bfe7be19cea4a8e406"
EXPECTED_CANONICAL_BYTE_COUNT = 6_768_106
EXPECTED_CANONICAL_SHA256 = (
    "755a92500fcf5f4e88bf6f1b0990ced8b4660a35cfd92ad92e535112363b0be2"
)


class ConstructionK7CrossEpochProgramBranchCampaignV116Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossEpochProgramBranchCampaignV116Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossEpochProgramBranchCampaignV116:
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
            or pre.domains.extension_content_id_v116(
                pre.domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_CAMPAIGN_V116_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V116 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CrossEpochProgramBranchCampaignV116 | None = None


def run_cross_epoch_program_branch_campaign_v116(
    v115_campaign_raw: bytes,
    v115_verification_raw: bytes,
) -> CrossEpochProgramBranchCampaignV116:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V116 campaign exists; same identity will not be rerun")
    registration = pre.verify_cross_epoch_program_branch_preregistration_v116(
        pre.freeze_cross_epoch_program_branch_preregistration_v116()
    )
    try:
        campaign_v115 = loads_canonical_json(v115_campaign_raw)
        verification_v115 = loads_canonical_json(v115_verification_raw)
    except Exception as exc:
        _fail(f"V116 frozen V115 predecessor is unreadable: {exc}")
    if (
        len(v115_campaign_raw) != V115_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v115_campaign_raw).hexdigest()
        != pre.V115_CAMPAIGN_SHA256
        or campaign_v115.get("campaign_id") != pre.V115_CAMPAIGN_ID
        or canonical_json_bytes(verification_v115) != v115_verification_raw
        or len(v115_verification_raw) != V115_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v115_verification_raw).hexdigest()
        != pre.V115_VERIFICATION_SHA256
        or verification_v115.get("verification_id") != pre.V115_VERIFICATION_ID
        or verification_v115.get("registered_gate_independently_verified")
        is not True
        or freeze_projected_program_memo_verification_v115(v115_campaign_raw)
        != v115_verification_raw
    ):
        _fail("V116 frozen successful V115 evidence changed")
    document = build_cross_epoch_program_branch_campaign_document_v116(
        pre.campaign_config_v116(),
        preregistration_id=registration.preregistration_id,
        v115_campaign_id=pre.V115_CAMPAIGN_ID,
        v115_verification_id=pre.V115_VERIFICATION_ID,
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
        _fail("frozen V116 campaign changed")
    _CACHE = CrossEpochProgramBranchCampaignV116(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_cross_epoch_program_branch_campaign_v116",
)
