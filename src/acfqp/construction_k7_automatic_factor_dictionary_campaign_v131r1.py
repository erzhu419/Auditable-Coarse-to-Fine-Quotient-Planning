"""Producer for the preregistered V131R1 automatic factor-dictionary campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_automatic_factor_dictionary_preregistration_v131r1 as pre
from acfqp.automatic_minimal_factor_dictionary_v131 import (
    derive_automatic_minimal_factor_dictionary_v131,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.automatic_factor_dictionary_campaign_core_v131r1 import (
    build_automatic_dictionary_factor_prior_campaign_document_v131r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7AutomaticFactorDictionaryCampaignV131R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AutomaticFactorDictionaryCampaignV131R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AutomaticFactorDictionaryCampaignV131R1:
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
            or pre.domains.extension_content_id_v131r1(
                pre.domains.CONSTRUCTION_K7_AUTOMATIC_DICTIONARY_FACTOR_CAMPAIGN_V131R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V131R1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: AutomaticFactorDictionaryCampaignV131R1 | None = None


def run_automatic_factor_dictionary_campaign_v131r1(
    source_campaign_bytes: Mapping[str, bytes],
    v130_campaign_raw: bytes,
    v130_verification_raw: bytes,
    v131_preregistration_raw: bytes,
) -> AutomaticFactorDictionaryCampaignV131R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V131R1 campaign exists; same identity will not be rerun")
    source = dict(source_campaign_bytes)
    registration = pre.freeze_automatic_factor_dictionary_preregistration_v131r1(
        source,
        v130_campaign_raw,
        v130_verification_raw,
        v131_preregistration_raw,
    )
    source_library = derive_artifact_factor_projection_v120(source)
    dictionary = derive_automatic_minimal_factor_dictionary_v131(
        source_library, source
    )
    preregistration = registration.to_document()
    if (
        source_library != preregistration["source_artifact_factor_library"]
        or dictionary != preregistration["automatic_factor_dictionary"]
    ):
        _fail("V131R1 preregistered automatic dictionary changed")
    document = build_automatic_dictionary_factor_prior_campaign_document_v131r1(
        pre.campaign_config_v131r1(),
        preregistration_id=registration.preregistration_id,
        v130_campaign_id=pre.V130_CAMPAIGN_ID,
        v130_verification_id=pre.V130_VERIFICATION_ID,
        artifact_factor_library=dictionary,
        source_campaign_bytes=source,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V131R1 campaign changed")
    _CACHE = AutomaticFactorDictionaryCampaignV131R1(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_automatic_factor_dictionary_campaign_v131r1")
