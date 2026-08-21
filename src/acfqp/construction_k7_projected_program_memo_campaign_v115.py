"""Producer for preregistered projected program memoization V115."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_projected_program_memo_preregistration_v115 as pre
from acfqp.construction_k7_three_family_incremental_successor_campaign_v114 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V114_CAMPAIGN_BYTE_COUNT,
)
from acfqp.construction_k7_three_family_incremental_successor_independent_verifier_v114 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V114_VERIFICATION_BYTE_COUNT,
    freeze_three_family_incremental_successor_verification_v114,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.projected_program_memo_campaign_core_v115 import (
    build_projected_program_memo_campaign_document_v115,
)


CAMPAIGN_ID = "d2d061867f8bfc3d2c1abe439537ad0a1432738bf2db4242ef4d35f2c41dfcfe"
EXPECTED_CANONICAL_BYTE_COUNT = 6_519_817
EXPECTED_CANONICAL_SHA256 = (
    "94add1705c5780f4893a7dde82771e4dd3c8d27219ceb1c6b8a3631d393476dd"
)


class ConstructionK7ProjectedProgramMemoCampaignV115Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedProgramMemoCampaignV115Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProjectedProgramMemoCampaignV115:
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
            or pre.domains.extension_content_id_v115(
                pre.domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_CAMPAIGN_V115_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V115 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: ProjectedProgramMemoCampaignV115 | None = None


def run_projected_program_memo_campaign_v115(
    v114_campaign_raw: bytes,
    v114_verification_raw: bytes,
) -> ProjectedProgramMemoCampaignV115:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V115 campaign exists; same identity will not be rerun")
    registration = pre.verify_projected_program_memo_preregistration_v115(
        pre.freeze_projected_program_memo_preregistration_v115()
    )
    try:
        campaign_v114 = loads_canonical_json(v114_campaign_raw)
        verification_v114 = loads_canonical_json(v114_verification_raw)
    except Exception as exc:
        _fail(f"V115 frozen V114 predecessor is unreadable: {exc}")
    if (
        len(v114_campaign_raw) != V114_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v114_campaign_raw).hexdigest()
        != pre.V114_CAMPAIGN_SHA256
        or campaign_v114.get("campaign_id") != pre.V114_CAMPAIGN_ID
        or canonical_json_bytes(verification_v114) != v114_verification_raw
        or len(v114_verification_raw) != V114_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v114_verification_raw).hexdigest()
        != pre.V114_VERIFICATION_SHA256
        or verification_v114.get("verification_id") != pre.V114_VERIFICATION_ID
        or verification_v114.get("registered_gate_independently_verified")
        is not True
        or freeze_three_family_incremental_successor_verification_v114(
            v114_campaign_raw
        )
        != v114_verification_raw
    ):
        _fail("V115 frozen successful V114 evidence changed")
    document = build_projected_program_memo_campaign_document_v115(
        pre.campaign_config_v115(),
        preregistration_id=registration.preregistration_id,
        v114_campaign_id=pre.V114_CAMPAIGN_ID,
        v114_verification_id=pre.V114_VERIFICATION_ID,
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
        _fail("frozen V115 campaign changed")
    _CACHE = ProjectedProgramMemoCampaignV115(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_projected_program_memo_campaign_v115",
)
