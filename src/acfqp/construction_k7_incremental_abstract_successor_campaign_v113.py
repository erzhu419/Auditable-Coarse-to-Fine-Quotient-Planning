"""Producer for the preregistered incremental-successor campaign V113."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_incremental_abstract_successor_preregistration_v113 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_symmetric_epoch_accounting_independent_verifier_v112 import (
    CAMPAIGN_BYTE_COUNT as V112_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_BYTE_COUNT as V112_VERIFICATION_BYTE_COUNT,
    freeze_symmetric_epoch_accounting_verification_v112,
)
from acfqp.incremental_abstract_successor_campaign_core_v113 import (
    build_incremental_abstract_successor_campaign_document_v113,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "eb59e83d53b6ebcf104ece21a60a99371ac15516f3e5629a604290142411b13a"
EXPECTED_CANONICAL_BYTE_COUNT = 23_620_415
EXPECTED_CANONICAL_SHA256 = "835e0a9687196b77a8af76ed5c025c7757d3656fc7317af3a9a43a519e268054"


class ConstructionK7IncrementalAbstractSuccessorCampaignV113Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IncrementalAbstractSuccessorCampaignV113Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class IncrementalAbstractSuccessorCampaignV113:
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
            or pre.domains.extension_content_id_v113(
                pre.domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_CAMPAIGN_V113_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V113 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: IncrementalAbstractSuccessorCampaignV113 | None = None


def run_incremental_abstract_successor_campaign_v113(
    v112_campaign_raw: bytes,
    v112_verification_raw: bytes,
) -> IncrementalAbstractSuccessorCampaignV113:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V113 campaign exists; same identity will not be rerun")
    registration = pre.verify_incremental_abstract_successor_preregistration_v113(
        pre.freeze_incremental_abstract_successor_preregistration_v113()
    )
    try:
        campaign_v112 = loads_canonical_json(v112_campaign_raw)
        verification_v112 = loads_canonical_json(v112_verification_raw)
    except Exception as exc:
        _fail(f"V113 frozen V112 predecessor is unreadable: {exc}")
    if (
        len(v112_campaign_raw) != V112_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v112_campaign_raw).hexdigest()
        != pre.V112_CAMPAIGN_SHA256
        or campaign_v112.get("campaign_id") != pre.V112_CAMPAIGN_ID
        or canonical_json_bytes(verification_v112) != v112_verification_raw
        or len(v112_verification_raw) != V112_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v112_verification_raw).hexdigest()
        != pre.V112_VERIFICATION_SHA256
        or verification_v112.get("verification_id") != pre.V112_VERIFICATION_ID
        or verification_v112.get("campaign_id") != pre.V112_CAMPAIGN_ID
        or verification_v112.get("registered_gate_independently_verified") is not True
        or freeze_symmetric_epoch_accounting_verification_v112(v112_campaign_raw)
        != v112_verification_raw
    ):
        _fail("V113 frozen successful V112 evidence changed")
    document = build_incremental_abstract_successor_campaign_document_v113(
        pre.campaign_config_v113(),
        preregistration_id=registration.preregistration_id,
        v112_campaign_id=pre.V112_CAMPAIGN_ID,
        v112_verification_id=pre.V112_VERIFICATION_ID,
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
        _fail("frozen V113 campaign changed")
    _CACHE = IncrementalAbstractSuccessorCampaignV113(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_incremental_abstract_successor_campaign_v113",
)
