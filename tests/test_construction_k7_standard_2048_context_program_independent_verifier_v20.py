from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_context_program_campaign_v20 as producer
from acfqp import construction_k7_standard_2048_context_program_independent_verifier_v20 as verifier


@pytest.fixture(scope="module")
def verification() -> verifier.Standard2048ContextProgramIndependentVerificationV20:
    campaign = producer.run_standard_2048_context_program_campaign_v20()
    return verifier.verify_standard_2048_context_program_bytes_independently_v20(
        campaign.canonical_bytes
    )


def test_independent_verification_identity_and_complete_replay(verification) -> None:
    assert verification.verification_id == verifier.EXPECTED_VERIFICATION_ID
    assert verification.campaign_id == verifier.EXPECTED_CAMPAIGN_ID
    document = verification.to_document()
    assert document["four_raw_context_observations_independently_replayed"] is True
    assert document["twelve_postobservation_candidates_independently_generated"] is True
    assert document["unique_feature_threshold_program_independently_selected"] is True
    assert document["all_16_formula_rows_independently_proved"] is True
    assert document["all_12_h3_plans_independently_replanned"] is True
    assert document["all_12_target_transitions_independently_replayed"] is True
    assert document["all_root_values_and_actions_match_independent_target_ground"] is True


def test_verifier_has_no_v20_producer_or_target_kernel_import() -> None:
    path = Path(verifier.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("context_program_campaign_v20" in name for name in imports)
    assert not any("local_dynamics_kernel_v18" in name for name in imports)


def test_independent_claim_boundary_remains_narrow(verification) -> None:
    document = verification.to_document()
    assert document["retained_six_query_difference_against_v19_no_prior_verified"] is True
    assert document["open_ended_coordinate_invention_verified"] is False
    assert document["broad_sample_efficiency_or_total_work_saving_verified"] is False
    assert document["full_game_or_broad_world_model_verified"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_noncanonical_or_tampered_campaign_bytes_are_rejected() -> None:
    with pytest.raises(
        verifier.ConstructionK7Standard2048ContextProgramIndependentVerifierV20Error
    ):
        verifier.verify_standard_2048_context_program_bytes_independently_v20(b"{} ")


def test_verification_tamper_and_caller_mint_are_rejected(verification) -> None:
    tampered = copy.copy(verification)
    object.__setattr__(tampered, "verification_id", "f" * 64)
    with pytest.raises(
        verifier.ConstructionK7Standard2048ContextProgramIndependentVerifierV20Error
    ):
        tampered.__post_init__()
    with pytest.raises(
        verifier.ConstructionK7Standard2048ContextProgramIndependentVerifierV20Error
    ):
        verifier.Standard2048ContextProgramIndependentVerificationV20(
            object(),
            verification.canonical_bytes,
            verification.verification_id,
            verification.campaign_id,
        )
