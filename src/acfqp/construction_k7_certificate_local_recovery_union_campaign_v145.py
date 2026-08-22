"""Producer for the preregistered V145 certificate-local recovery union."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_certificate_local_recovery_union_preregistration_v145 as pre
from acfqp.certificate_local_recovery_union_campaign_core_v145 import (
    build_certificate_local_recovery_union_campaign_document_v145,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7CertificateLocalRecoveryUnionCampaignV145Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateLocalRecoveryUnionCampaignV145Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertificateLocalRecoveryUnionCampaignV145:
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
            or pre.domains.extension_content_id_v145(
                pre.domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_CAMPAIGN_V145_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V145 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CertificateLocalRecoveryUnionCampaignV145 | None = None


def run_certificate_local_recovery_union_campaign_v145(
    v144r2_preregistration_raw: bytes,
    v144r2_campaign_raw: bytes,
    v144r2_failure_raw: bytes,
) -> CertificateLocalRecoveryUnionCampaignV145:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V145 attempt is terminal; its identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V145 campaign exists; its identity will not be rerun")
    registration = pre.freeze_certificate_local_recovery_union_preregistration_v145(
        v144r2_preregistration_raw, v144r2_campaign_raw, v144r2_failure_raw
    )
    preregistration = registration.to_document()
    v144 = preregistration["frozen_v144r2_preregistration"][
        "frozen_v144r1_preregistration"
    ]["frozen_v144_preregistration"]
    document = build_certificate_local_recovery_union_campaign_document_v145(
        pre.campaign_config_v145(),
        preregistration_id=registration.preregistration_id,
        dictionary=v144["frozen_v141_factor_bank"],
        dictionary_verification=v144["frozen_v141_independent_verification"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V145 campaign changed")
    _CACHE = CertificateLocalRecoveryUnionCampaignV145(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_certificate_local_recovery_union_campaign_v145",
)
