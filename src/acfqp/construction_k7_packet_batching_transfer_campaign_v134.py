"""Producer for the preregistered V134 packet-batching transfer campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_packet_batching_transfer_preregistration_v134 as pre
from acfqp.packet_batching_transfer_campaign_core_v134 import (
    build_packet_batching_transfer_campaign_document_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "bbf4781ed3c49f278eeeb2b266ac9e94e2bc250659f4578acecafb22ed9ca46d"
EXPECTED_CANONICAL_BYTE_COUNT = 23_072_947
EXPECTED_CANONICAL_SHA256 = "51c83073eb28e424ed34336203738bd693f3d662001a3b936bdbb5366424dc27"


class ConstructionK7PacketBatchingTransferCampaignV134Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PacketBatchingTransferCampaignV134Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PacketBatchingTransferCampaignV134:
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
            or pre.domains.extension_content_id_v134(
                pre.domains.CONSTRUCTION_K7_PACKET_BATCHING_TRANSFER_CAMPAIGN_V134_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V134 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: PacketBatchingTransferCampaignV134 | None = None


def run_packet_batching_transfer_campaign_v134(
    dictionary_raw: bytes,
    dictionary_verification_raw: bytes,
    v133_campaign_raw: bytes,
    v133_verification_raw: bytes,
) -> PacketBatchingTransferCampaignV134:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V134 campaign exists; same identity will not be rerun")
    registration = pre.freeze_packet_batching_transfer_preregistration_v134(
        dictionary_raw,
        dictionary_verification_raw,
        v133_campaign_raw,
        v133_verification_raw,
    )
    preregistration = registration.to_document()
    document = build_packet_batching_transfer_campaign_document_v134(
        pre.campaign_config_v134(),
        preregistration_id=registration.preregistration_id,
        dictionary=preregistration["frozen_v132_dictionary"],
        dictionary_verification=preregistration[
            "frozen_v132_independent_verification"
        ],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V134 campaign changed")
    _CACHE = PacketBatchingTransferCampaignV134(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_packet_batching_transfer_campaign_v134")
