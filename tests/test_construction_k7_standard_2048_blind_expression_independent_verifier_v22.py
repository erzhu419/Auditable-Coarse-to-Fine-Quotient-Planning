from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_blind_expression_campaign_v22 as producer
from acfqp import construction_k7_standard_2048_blind_expression_independent_verifier_v22 as verifier


@pytest.fixture(scope="module")
def result() -> verifier.Standard2048BlindExpressionIndependentVerificationV22:
    campaign = producer.run_standard_2048_blind_expression_campaign_v22()
    return verifier.verify_standard_2048_blind_expression_bytes_independently_v22(
        campaign.canonical_bytes
    )


def test_frozen_independent_verification_identity(result) -> None:
    assert result.verification_id == verifier.EXPECTED_VERIFICATION_ID
    assert result.campaign_id == verifier.EXPECTED_CAMPAIGN_ID


def test_commit_reveal_synthesis_proof_and_plans_are_independently_replayed(result) -> None:
    document = result.to_document()
    assert document["commitment_and_reveal_semantics_independently_recomputed"] is True
    assert document["twenty_eight_primitive_expressions_independently_generated"] is True
    assert document["eighty_program_candidates_independently_generated"] is True
    assert document["four_minimax_queries_independently_replayed"] is True
    assert document["unique_count_eq_post_one_expression_independently_selected"] is True
    assert document["all_17_formula_rows_independently_proved"] is True
    assert document["all_12_h3_root_values_actions_and_transitions_independently_replayed"] is True
    assert document["four_query_difference_against_strict_no_prior_verified"] is True


def test_independent_claim_boundary_remains_narrow(result) -> None:
    document = result.to_document()
    assert document["experimenter_cognitive_blinding_verified"] is False
    assert document["runtime_target_source_access_isolation_verified"] is False
    assert document["open_ended_expression_invention_verified"] is False
    assert document["broad_sample_efficiency_or_total_work_saving_verified"] is False
    assert document["full_game_or_broad_world_model_verified"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_verifier_does_not_import_v22_producers_or_generic_planner() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = (
        "blind_expression_campaign_v22",
        "blind_expression_preregistration_v22",
        "commit_reveal_target_kernel_v22",
        "expression_planner_v1",
    )
    assert not any(any(fragment in name for fragment in forbidden) for name in imports)


def test_noncanonical_bytes_and_verification_forgery_are_rejected(result) -> None:
    with pytest.raises(
        verifier.ConstructionK7Standard2048BlindExpressionIndependentVerifierV22Error
    ):
        verifier.verify_standard_2048_blind_expression_bytes_independently_v22(b"{} ")
    tampered = copy.copy(result)
    object.__setattr__(tampered, "verification_id", "f" * 64)
    with pytest.raises(
        verifier.ConstructionK7Standard2048BlindExpressionIndependentVerifierV22Error
    ):
        tampered.__post_init__()
    with pytest.raises(
        verifier.ConstructionK7Standard2048BlindExpressionIndependentVerifierV22Error
    ):
        verifier.Standard2048BlindExpressionIndependentVerificationV22(
            object(), result.canonical_bytes, result.verification_id, result.campaign_id
        )
