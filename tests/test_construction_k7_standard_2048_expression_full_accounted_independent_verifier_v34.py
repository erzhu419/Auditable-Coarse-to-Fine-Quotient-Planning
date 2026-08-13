from __future__ import annotations

import copy
import os
from pathlib import Path
import shutil

import pytest

from acfqp import construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


_DEFAULT_CAMPAIGN = Path(
    "/tmp/acfqp-v34-full-accounted-campaign.canonical.json"
)
_DEFAULT_ROOT = Path("/tmp/acfqp-v34-full-accounting")


@pytest.fixture(scope="module")
def result():
    if os.environ.get("ACFQP_RUN_FULL_2048_ACCOUNTING") != "1":
        pytest.skip("requires retained preregistered full-accounting bytes")
    campaign_path = Path(
        os.environ.get("ACFQP_V34_CAMPAIGN_PATH", str(_DEFAULT_CAMPAIGN))
    )
    root = Path(os.environ.get("ACFQP_V34_OUTPUT_ROOT", str(_DEFAULT_ROOT)))
    raw = campaign_path.read_bytes()
    verified = (
        verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
            raw, root
        )
    )
    return raw, verified, root


def test_independent_verifier_does_not_import_producer() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    assert "full_accounted_campaign_v34" not in source
    assert "full_accounting_artifacts_v34" not in source
    assert "full_accounting_runtime_v34" not in source


def test_full_accounting_bundle_replays_independently(result) -> None:
    raw, verified, _ = result
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert verified.campaign_id == verifier.EXPECTED_CAMPAIGN_ID
    document = verified.to_document()
    assert document["accounting_bundle_replay_result"] == "PASS"
    assert document["operational_work_vector_count"] == 45
    assert document["evaluation_work_vector_count"] == 34
    assert document["counter_record_count"] == 21_251
    assert document["complete_decision_count"] == 3_187
    assert document["won_occurrence_count"] == 2
    assert document["lost_occurrence_count"] == 2
    assert document["every_operational_comparison_recomputed"] is True


def test_evaluation_and_official_claim_boundaries_remain_locked(result) -> None:
    _, verified, _ = result
    document = verified.to_document()
    assert document["evaluation_excluded_from_operational_comparison"] is True
    assert document["semantic_planning_replay_in_this_verifier"] is False
    assert document["registered_label_axis_sample_tax_reduction_replayed"] is True
    assert document["broad_iid_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_retained_counter_bundle_tamper_is_rejected(result, tmp_path) -> None:
    raw, _, root = result
    copied = tmp_path / "copied"
    shutil.copytree(root, copied)
    victim = next(copied.rglob("episode-0000-operational.json"))
    damaged = bytearray(victim.read_bytes())
    damaged[-2] ^= 1
    victim.write_bytes(bytes(damaged))
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error
    ):
        verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
            raw, copied
        )


def test_missing_bundle_is_rejected(result, tmp_path) -> None:
    raw, _, root = result
    copied = tmp_path / "missing"
    shutil.copytree(root, copied)
    next(copied.rglob("episode-0000-evaluation.json")).unlink()
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error
    ):
        verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
            raw, copied
        )


def test_resigned_campaign_claim_flip_is_rejected(result) -> None:
    raw, _, root = result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    forged = copy.deepcopy(document)
    forged["broad_iid_sample_efficiency_claimed"] = True
    payload = {
        key: value
        for key, value in forged.items()
        if key != "expression_full_accounted_campaign_id"
    }
    forged["expression_full_accounted_campaign_id"] = content_id(
        verifier.pre.FUTURE_DOMAINS["campaign"], payload
    )
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error
    ):
        verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
            canonical_json_bytes(forged), root
        )


def test_resigned_terminal_route_work_injection_is_rejected(result) -> None:
    raw, _, root = result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    forged = copy.deepcopy(document)
    terminal = forged["segments"][-1]["terminal_carry_forward"][0]
    terminal["route_work_vector_id"] = "f" * 64
    terminal["zero_decision_work"] = False
    payload = {
        key: value
        for key, value in forged.items()
        if key != "expression_full_accounted_campaign_id"
    }
    forged["expression_full_accounted_campaign_id"] = content_id(
        verifier.pre.FUTURE_DOMAINS["campaign"], payload
    )
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error
    ):
        verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
            canonical_json_bytes(forged), root
        )
