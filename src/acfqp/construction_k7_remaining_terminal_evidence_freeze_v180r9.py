"""Exact retained identity for the successful V180r9 six-terminal campaign."""

from __future__ import annotations

import hashlib
from typing import Any

from acfqp import construction_k7_remaining_terminal_execution_authorization_v180r9 as authorization
from acfqp import construction_k7_remaining_terminal_independent_verifier_v180r9 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_EXECUTION_AUTHORIZATION_ID = (
    "d855e8cd646537687fcde2485a3f7ee83e50ac1831ab01e0f1d0b923aca5703f"
)
EXPECTED_PRODUCTION_CAMPAIGN_BUNDLE_ID = (
    "dae4c77ee78da32ccb1fee25481fd6d201ba66282a00259ff4ca68ac51a9b622"
)
EXPECTED_TERMINAL_BYTE_COUNT = 1_548_968
EXPECTED_TERMINAL_SHA256 = (
    "605f5448db54da8e193e062fe694e5c40badcd1ccbb277d8822cb17dcaf9bb42"
)
EXPECTED_VERIFICATION_ID = (
    "d17c2fdd948479a9bcd9aecd4de9b6f834f390da3f889ee8d83c15aae02ae735"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 1_170
EXPECTED_VERIFICATION_SHA256 = (
    "b0eb929d5da9630b2446a94668ca93e5d328116a19b4b176af247731866543cb"
)


def verify_frozen_remaining_terminal_evidence_v180r9(
    terminal_bytes: bytes,
    verification_bytes: bytes,
) -> dict[str, Any]:
    if not (
        type(terminal_bytes) is bytes
        and len(terminal_bytes) == EXPECTED_TERMINAL_BYTE_COUNT
        and hashlib.sha256(terminal_bytes).hexdigest() == EXPECTED_TERMINAL_SHA256
        and type(verification_bytes) is bytes
        and len(verification_bytes) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(verification_bytes).hexdigest()
        == EXPECTED_VERIFICATION_SHA256
    ):
        raise ValueError("V180r9 retained bytes changed")
    terminal_document = loads_canonical_json(terminal_bytes)
    if (
        type(terminal_document) is not dict
        or terminal_document.get("production_campaign_bundle_id")
        != EXPECTED_PRODUCTION_CAMPAIGN_BUNDLE_ID
        or authorization.EXPECTED_AUTHORIZATION_ID
        != EXPECTED_EXECUTION_AUTHORIZATION_ID
    ):
        raise ValueError("V180r9 retained campaign identity changed")
    result = verifier.verify_remaining_terminal_campaign_independently_v180r9(
        terminal_bytes,
        execution_authorization_id=EXPECTED_EXECUTION_AUTHORIZATION_ID,
        event_manifests=authorization.event_manifests_v180r9(),
    )
    if not (
        canonical_json_bytes(result) == verification_bytes
        and result.get("verification_id") == EXPECTED_VERIFICATION_ID
        and result.get("production_campaign_bundle_id")
        == EXPECTED_PRODUCTION_CAMPAIGN_BUNDLE_ID
        and result.get("verified_terminal_count") == 6
        and result.get("all_counter_records_replayed") is True
        and result.get("all_nine_path_receipt_sets_replayed") is True
        and result.get("all_ten_paths_verified") is False
        and result.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and result.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and result.get("official_execution_allowed") is False
    ):
        raise ValueError("V180r9 independent verification changed")
    return result


__all__ = (
    "EXPECTED_EXECUTION_AUTHORIZATION_ID",
    "EXPECTED_PRODUCTION_CAMPAIGN_BUNDLE_ID",
    "EXPECTED_TERMINAL_BYTE_COUNT",
    "EXPECTED_TERMINAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "EXPECTED_VERIFICATION_BYTE_COUNT",
    "EXPECTED_VERIFICATION_SHA256",
    "verify_frozen_remaining_terminal_evidence_v180r9",
)
