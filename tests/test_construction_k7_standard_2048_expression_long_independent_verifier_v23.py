from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_expression_long_campaign_v23 as producer
from acfqp import construction_k7_standard_2048_expression_long_independent_verifier_v23 as verifier


@pytest.fixture(scope="module")
def result() -> verifier.Standard2048ExpressionLongIndependentVerificationV23:
    campaign = producer.run_standard_2048_expression_long_campaign_v23()
    return verifier.verify_standard_2048_expression_long_bytes_independently_v23(
        campaign.canonical_bytes
    )


def test_frozen_long_independent_verification_identity(result) -> None:
    assert result.verification_id == verifier.EXPECTED_VERIFICATION_ID
    assert result.campaign_id == verifier.CAMPAIGN_ID


def test_all_long_certificates_cache_checkpoints_and_transitions_replay(result) -> None:
    document = result.to_document()
    assert document["all_128_h3_certificates_independently_replayed"] is True
    assert document["all_128_seeded_target_transitions_independently_replayed"] is True
    assert document["all_12_cold_target_checkpoints_independently_replayed"] is True
    assert document["persistent_cross_decision_subproof_cache_independently_replayed"] is True
    assert document["exact_rational_precision_preserved"] is True
    assert document["zero_additional_model_labels_independently_verified"] is True
    assert document["four_inherited_labels_amortized_over_128_certificates_verified"] is True


def test_independent_claim_boundary_remains_narrow(result) -> None:
    document = result.to_document()
    assert document["evaluation_counter_aggregates_independently_verified"] is True
    assert document["broad_sample_efficiency_or_total_work_saving_verified"] is False
    assert document["full_game_or_tile_2048_verified"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_verifier_does_not_import_v23_producer_or_planner() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("expression_long_campaign_v23" in name for name in imports)
    assert not any("expression_planner_v1" in name for name in imports)
    assert not any("commit_reveal_target_kernel_v22" in name for name in imports)


def test_noncanonical_bytes_and_verification_forgery_are_rejected(result) -> None:
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionLongIndependentVerifierV23Error
    ):
        verifier.verify_standard_2048_expression_long_bytes_independently_v23(b"{} ")
    tampered = copy.copy(result)
    object.__setattr__(tampered, "verification_id", "f" * 64)
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionLongIndependentVerifierV23Error
    ):
        tampered.__post_init__()
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionLongIndependentVerifierV23Error
    ):
        verifier.Standard2048ExpressionLongIndependentVerificationV23(
            object(), result.canonical_bytes, result.verification_id, result.campaign_id
        )
