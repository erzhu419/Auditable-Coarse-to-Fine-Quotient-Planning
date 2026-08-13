from __future__ import annotations

import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_expression_accounted_campaign_v24 as campaign
from acfqp import construction_k7_standard_2048_expression_accounted_independent_verifier_v24 as verifier


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    root = tmp_path_factory.mktemp("v24-accounted-full") / "run"
    produced = campaign.run_standard_2048_expression_accounted_campaign_v24(root)
    verified = verifier.verify_standard_2048_expression_accounting_bytes_independently_v24(
        produced.canonical_bytes, root
    )
    return produced, verified, root


def test_full_accounting_bundle_replays_independently(result) -> None:
    produced, verified, _ = result
    assert produced.campaign_id == verifier.EXPECTED_CAMPAIGN_ID
    assert verified.campaign_id == produced.campaign_id
    document = verified.to_document()
    assert document["accounting_bundle_replay_result"] == "PASS"
    assert document["operational_work_vector_count"] == 135
    assert document["evaluation_work_vector_count"] == 13
    assert document["counter_record_count"] == 39_812
    assert document["every_operational_comparison_recomputed"] is True


def test_evaluation_and_official_claim_boundaries_remain_locked(result) -> None:
    _, verified, _ = result
    document = verified.to_document()
    assert document["evaluation_excluded_from_operational_comparison"] is True
    assert document["semantic_planning_replay_in_this_verifier"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_retained_counter_bundle_tamper_is_rejected(result, tmp_path) -> None:
    produced, _, root = result
    copied = tmp_path / "copied"
    copied.mkdir()
    for source in root.rglob("*.json"):
        target = copied / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    victim = next(copied.rglob("operational.json"))
    raw = bytearray(victim.read_bytes())
    raw[-2] ^= 1
    victim.write_bytes(bytes(raw))
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error
    ):
        verifier.verify_standard_2048_expression_accounting_bytes_independently_v24(
            produced.canonical_bytes, copied
        )


def test_missing_bundle_is_rejected(result, tmp_path) -> None:
    produced, _, root = result
    copied = tmp_path / "missing"
    copied.mkdir()
    sources = list(root.rglob("*.json"))
    for source in sources[1:]:
        target = copied / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error
    ):
        verifier.verify_standard_2048_expression_accounting_bytes_independently_v24(
            produced.canonical_bytes, copied
        )
