"""Producer for the preregistered V60 query-local raw-evidence campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_query_local_preregistration_v60 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.query_local_raw_evidence_campaign_core_v60 import build_query_local_raw_evidence_campaign_document_v60


CAMPAIGN_ID = "abb8c1dab6a8dd1599617dfd9927f741259e93102b06bdb650c849103aa5ff8c"
EXPECTED_CANONICAL_BYTE_COUNT = 4_843_044
EXPECTED_CANONICAL_SHA256 = "820476b0d7a98ea5ea24383996a7b56d3202afdda265ff9f03779201c99ea69c"
REGISTERED_FAILURE_ID = ""


class ConstructionK7QueryLocalCampaignV60Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryLocalCampaignV60Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class QueryLocalCampaignV60:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if self._issuer is not _ISSUER or type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes or document.get("campaign_id") != self.campaign_id or pre.domains.extension_content_id_v60(pre.V60_DOMAINS["campaign"], payload) != self.campaign_id:
            _fail("V60 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: QueryLocalCampaignV60 | None = None


def run_query_local_campaign_v60() -> QueryLocalCampaignV60:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V60 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_query_local_preregistration_v60(pre.freeze_query_local_preregistration_v60())
    if pre._source_facts() != preregistration.to_document()["source_closure"]["source_facts"]:
        _fail("V60 preregistered source closure changed before execution")
    document = build_query_local_raw_evidence_campaign_document_v60(
        pre.campaign_config_v60(), preregistration.preregistration_id, pre.previous.previous.previous.FACTOR_LIBRARY
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (identity != CAMPAIGN_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("frozen V60 campaign changed")
    _CACHE = QueryLocalCampaignV60(_ISSUER, raw, identity)
    return _CACHE


def verify_query_local_campaign_v60(value: Any) -> QueryLocalCampaignV60:
    if type(value) is not QueryLocalCampaignV60:
        _fail("V60 campaign rejects foreign values")
    value.__post_init__()
    expected = run_query_local_campaign_v60()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V60 campaign does not match frozen output")
    return value


__all__ = ("CAMPAIGN_ID", "EXPECTED_CANONICAL_BYTE_COUNT", "EXPECTED_CANONICAL_SHA256", "run_query_local_campaign_v60", "verify_query_local_campaign_v60")
