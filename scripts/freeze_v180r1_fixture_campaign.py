#!/usr/bin/env python3
"""Materialize the outcome-free V180r1 fixture graph exactly once."""

from __future__ import annotations

import hashlib
from pathlib import Path

from acfqp import construction_k7_all_path_terminal_finalizer_v180r1 as producer
from acfqp import (
    construction_k7_all_path_terminal_finalizer_independent_verifier_v180r1
    as verifier,
)
from acfqp.phase3e_ids import loads_canonical_json
from acfqp.routing_v1 import TerminalCode


def _write_fresh(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        if stream.write(raw) != len(raw):
            raise RuntimeError("V180r1 exact-freeze short write")


def main() -> None:
    root = Path(__file__).resolve().parents[1] / ".tmp" / "exact-freeze"
    bundles: dict[str, bytes] = {}
    for code in TerminalCode:
        fixture = producer.fixture_counter_values_v180r1(code)
        observation = producer.build_terminal_observation_v180r1(
            subject_id=f"fixture_{code.value.lower()}",
            terminal_code=code,
            counter_values=fixture.values,
            evidence_id=hashlib.sha256(code.value.encode()).hexdigest(),
        )
        bundles[code.value] = (
            producer.materialize_terminal_accounting_bundle_v180r1(observation)
        )
    campaign = producer.materialize_fixture_campaign_bundle_v180r1(bundles)
    verification = verifier.verify_fixture_campaign_independently_v180r1(campaign)
    campaign_path = root / "v180r1_all_path_fixture_campaign.json"
    verification_path = root / "v180r1_all_path_fixture_campaign_verification.json"
    _write_fresh(campaign_path, campaign)
    _write_fresh(verification_path, verification)
    campaign_document = loads_canonical_json(campaign)
    verification_document = loads_canonical_json(verification)
    print(
        "campaign",
        campaign_document["fixture_campaign_bundle_id"],
        len(campaign),
        hashlib.sha256(campaign).hexdigest(),
    )
    print(
        "verification",
        verification_document["terminal_finalizer_verification_id"],
        len(verification),
        hashlib.sha256(verification).hexdigest(),
    )


if __name__ == "__main__":
    main()
