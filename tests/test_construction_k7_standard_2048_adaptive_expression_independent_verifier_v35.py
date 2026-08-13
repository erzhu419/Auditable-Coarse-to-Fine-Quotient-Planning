from __future__ import annotations

import ast
import copy
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_adaptive_expression_independent_verifier_v35 as verifier
from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as preregistration
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


FULL = os.environ.get("ACFQP_RUN_ADAPTIVE_2048_V35") == "1"
DEFAULT_CAMPAIGN = Path(
    "/tmp/acfqp-v35-adaptive-expression-campaign.canonical.json"
)


@pytest.fixture(scope="module")
def result():
    if not FULL:
        pytest.skip("requires retained preregistered adaptive-expression bytes")
    campaign_path = Path(
        os.environ.get("ACFQP_V35_CAMPAIGN_PATH", str(DEFAULT_CAMPAIGN))
    )
    campaign_bytes = campaign_path.read_bytes()
    preregistration_bytes = (
        preregistration.freeze_standard_2048_adaptive_expression_preregistration_v35().canonical_bytes
    )
    verified = verifier.verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35(
        campaign_bytes, preregistration_bytes
    )
    return campaign_bytes, preregistration_bytes, verified


def test_independent_verifier_import_surface_excludes_v35_producers() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        "acfqp.construction_k7_standard_2048_adaptive_expression_campaign_v35",
        "acfqp.construction_k7_standard_2048_adaptive_expression_preregistration_v35",
        "acfqp.construction_k7_standard_2048_adaptive_expression_runtime_v35",
        "acfqp.construction_k7_standard_2048_adaptive_expression_target_v35",
        "acfqp.construction_k7_standard_2048_expression_planner_v1",
    }
    assert imported.isdisjoint(forbidden)


def test_frozen_preregistration_bytes_replay_without_target_source() -> None:
    frozen = (
        preregistration.freeze_standard_2048_adaptive_expression_preregistration_v35()
    )
    document = verifier._preregistration_document(frozen.canonical_bytes)  # noqa: SLF001
    assert document["adaptive_expression_preregistration_id"] == (
        verifier.PREREGISTRATION_ID
    )
    assert document["target_revealed"] is False
    assert document["outcome_fields_present"] is False


def test_campaign_replays_failure_repair_and_all_h3_certificates(result) -> None:
    campaign_bytes, _, verified = result
    assert len(campaign_bytes) == verifier.EXPECTED_CAMPAIGN_BYTE_COUNT
    assert verified.campaign_id == verifier.EXPECTED_CAMPAIGN_ID
    document = verified.to_document()
    assert document["campaign_replay_result"] == "PASS"
    assert document[
        "failure_frontier_acquisition_and_candidate_elimination_replayed"
    ] is True
    assert document["selected_expression_exact_proof_replayed"] is True
    assert document["every_h3_plan_certificate_replayed"] is True
    assert document["every_seeded_execution_transition_replayed"] is True
    assert document["cold_ground_checkpoints_replayed"] is True
    assert document["ground_distinction_query_count"] < document[
        "first_frontier_no_prior_label_count"
    ]


def test_accounting_and_scientific_claim_boundaries_remain_locked(result) -> None:
    _, _, verified = result
    document = verified.to_document()
    assert document["counter_records_issued"] is False
    assert document["formal_native_accounting_successor_required"] is True
    assert document["automatic_reusable_world_model_goal_completed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def _resign_campaign(document: dict[str, object]) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "adaptive_expression_campaign_id"
    }
    document["adaptive_expression_campaign_id"] = content_id(
        verifier.CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CAMPAIGN_V35_DOMAIN,
        payload,
    )
    return canonical_json_bytes(document)


def test_resigned_acquisition_context_tamper_is_rejected(result) -> None:
    campaign_bytes, preregistration_bytes, _ = result
    document = loads_canonical_json(campaign_bytes)
    assert type(document) is dict
    forged = copy.deepcopy(document)
    forged["expression_acquisitions"][0]["raw_context"][
        "post_swipe_board_ranks"
    ][0] += 1
    with pytest.raises(
        verifier.ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error
    ):
        verifier.verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35(
            _resign_campaign(forged), preregistration_bytes
        )


def test_resigned_sample_efficiency_claim_flip_is_rejected(result) -> None:
    campaign_bytes, preregistration_bytes, _ = result
    document = loads_canonical_json(campaign_bytes)
    assert type(document) is dict
    forged = copy.deepcopy(document)
    forged["broad_iid_or_cross_domain_sample_efficiency_claimed"] = True
    with pytest.raises(
        verifier.ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error
    ):
        verifier.verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35(
            _resign_campaign(forged), preregistration_bytes
        )


def test_preregistration_byte_tamper_is_rejected(result) -> None:
    campaign_bytes, preregistration_bytes, _ = result
    damaged = bytearray(preregistration_bytes)
    damaged[-2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error
    ):
        verifier.verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35(
            campaign_bytes, bytes(damaged)
        )
