"""Producer for the preregistered V94 total-label campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_total_label_meta_prior_preregistration_v94 as pre
from acfqp.construction_k7_prior_only_occurrence_source_campaign_v91r2 import (
    CAMPAIGN_ID as V91R2_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V91R2_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V91R2_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_source_model_acceptance_v91r3 import (
    ACCEPTANCE_ID as V91R3_ACCEPTANCE_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V91R3_ACCEPTANCE_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V91R3_ACCEPTANCE_SHA256,
)
from acfqp.construction_k7_terminal_overlay_target_campaign_v93 import (
    CAMPAIGN_ID as V93_FAILED_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V93_FAILED_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V93_FAILED_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_terminal_overlay_target_independent_verifier_v93 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V93_FAILED_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V93_FAILED_VERIFICATION_SHA256,
    VERIFICATION_ID as V93_FAILED_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.total_label_meta_prior_campaign_core_v94 import (
    build_total_label_meta_prior_campaign_document_v94,
)


CAMPAIGN_ID = (
    "8fcb91339c02f818ef9ff829e99ab1ac000fbc6940888d700c31c461fafabde8"
)
EXPECTED_CANONICAL_BYTE_COUNT = 278_767
EXPECTED_CANONICAL_SHA256 = (
    "b1419448d18011bec11dfe604573856b6f7e4a56c642a078c0804a1cb410465f"
)


class ConstructionK7TotalLabelMetaPriorCampaignV94Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TotalLabelMetaPriorCampaignV94Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TotalLabelMetaPriorCampaignV94:
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
            or pre.domains.extension_content_id_v94(
                pre.domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_CAMPAIGN_V94_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V94 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: TotalLabelMetaPriorCampaignV94 | None = None


def run_total_label_meta_prior_campaign_v94(
    source_campaign_raw: bytes,
    source_acceptance_raw: bytes,
    v93_failed_campaign_raw: bytes,
    v93_failed_verification_raw: bytes,
) -> TotalLabelMetaPriorCampaignV94:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V94 campaign exists; same identity will not be rerun")
    inputs = (
        (source_campaign_raw, V91R2_CAMPAIGN_BYTE_COUNT, V91R2_CAMPAIGN_SHA256),
        (
            source_acceptance_raw,
            V91R3_ACCEPTANCE_BYTE_COUNT,
            V91R3_ACCEPTANCE_SHA256,
        ),
        (
            v93_failed_campaign_raw,
            V93_FAILED_CAMPAIGN_BYTE_COUNT,
            V93_FAILED_CAMPAIGN_SHA256,
        ),
        (
            v93_failed_verification_raw,
            V93_FAILED_VERIFICATION_BYTE_COUNT,
            V93_FAILED_VERIFICATION_SHA256,
        ),
    )
    if any(
        type(raw) is not bytes
        or len(raw) != count
        or hashlib.sha256(raw).hexdigest() != digest
        for raw, count, digest in inputs
    ):
        _fail("V94 frozen predecessor bytes changed")
    source = loads_canonical_json(source_campaign_raw)
    acceptance = loads_canonical_json(source_acceptance_raw)
    failed = loads_canonical_json(v93_failed_campaign_raw)
    failed_verification = loads_canonical_json(v93_failed_verification_raw)
    if (
        source.get("campaign_id") != V91R2_CAMPAIGN_ID
        or acceptance.get("acceptance_id") != V91R3_ACCEPTANCE_ID
        or acceptance.get("v91r2_campaign_id") != source["campaign_id"]
        or failed.get("campaign_id") != V93_FAILED_CAMPAIGN_ID
        or failed_verification.get("verification_id")
        != V93_FAILED_VERIFICATION_ID
        or failed_verification.get("campaign_id") != failed["campaign_id"]
    ):
        _fail("V94 predecessor identity join changed")
    preregistration = pre.verify_total_label_meta_prior_preregistration_v94(
        pre.freeze_total_label_meta_prior_preregistration_v94()
    )
    document = build_total_label_meta_prior_campaign_document_v94(
        pre.campaign_config_v94(),
        preregistration_id=preregistration.preregistration_id,
        source_acceptance_id=acceptance["acceptance_id"],
        source_acceptance_verification_id=pre.V91R3_VERIFICATION_ID,
        source_campaign_id=source["campaign_id"],
        source_campaign_verification_id=pre.V91R2_VERIFICATION_ID,
        v93_failed_campaign_id=failed["campaign_id"],
        v93_failed_verification_id=failed_verification["verification_id"],
        source_accounting=source["accounting"],
        model=acceptance["accepted_joint_successor_version_space_model"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V94 campaign changed")
    _CACHE = TotalLabelMetaPriorCampaignV94(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_total_label_meta_prior_campaign_v94")
