"""Exact identity lock for the outcome-free V180r1 finalizer fixture graph."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from acfqp import (
    construction_k7_all_path_terminal_finalizer_independent_verifier_v180r1
    as verifier,
)
from acfqp.phase3e_ids import loads_canonical_json


EXPECTED_CAMPAIGN_ID = (
    "c8eb72ea0d6c4b84343ea499ecf308e972b2abfc32e99696afa6b307122e8e13"
)
EXPECTED_CAMPAIGN_BYTE_COUNT = 2_669_998
EXPECTED_CAMPAIGN_SHA256 = (
    "f53168b1c23c6571731d1db8b46648cad8f3789b2f3a1e33ed4647cdb08360db"
)
EXPECTED_VERIFICATION_ID = (
    "bb7b3a78af5c892b569085069d75b4dcf695e17687a346e15ce8b330526bed2c"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 1_680
EXPECTED_VERIFICATION_SHA256 = (
    "fb0dd0a32e967cc2c107bc56b22589ab84eabeb2c0fac4b41b0332371489b9a9"
)


@dataclass(frozen=True, slots=True)
class FrozenFixtureGraphV180r1:
    campaign_bytes: bytes
    verification_bytes: bytes
    campaign_id: str
    verification_id: str


def load_frozen_fixture_graph_v180r1() -> FrozenFixtureGraphV180r1:
    root = Path(__file__).resolve().parents[2] / ".tmp" / "exact-freeze"
    campaign = (root / "v180r1_all_path_fixture_campaign.json").read_bytes()
    verification = (
        root / "v180r1_all_path_fixture_campaign_verification.json"
    ).read_bytes()
    campaign_document = loads_canonical_json(campaign)
    verification_document = loads_canonical_json(verification)
    if not (
        len(campaign) == EXPECTED_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign).hexdigest() == EXPECTED_CAMPAIGN_SHA256
        and campaign_document["fixture_campaign_bundle_id"] == EXPECTED_CAMPAIGN_ID
        and len(verification) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(verification).hexdigest() == EXPECTED_VERIFICATION_SHA256
        and verification_document["terminal_finalizer_verification_id"]
        == EXPECTED_VERIFICATION_ID
        and verifier.verify_fixture_campaign_independently_v180r1(campaign)
        == verification
    ):
        raise ValueError("V180r1 exact fixture graph changed")
    return FrozenFixtureGraphV180r1(
        campaign,
        verification,
        EXPECTED_CAMPAIGN_ID,
        EXPECTED_VERIFICATION_ID,
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "load_frozen_fixture_graph_v180r1",
)
