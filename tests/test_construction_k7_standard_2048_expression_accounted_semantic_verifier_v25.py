from __future__ import annotations

from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_expression_accounted_campaign_v24 as campaign
from acfqp import construction_k7_standard_2048_expression_accounted_semantic_verifier_v25 as verifier


def test_independent_model_synthesis_reconstructs_registered_counter_totals() -> None:
    trace, acquisition, proof = verifier._model_expected()
    assert trace["world_model"]["blind_expression_world_model_id"] == campaign.EXPECTED_WORLD_MODEL_ID
    assert acquisition["model.target_probability_labels_acquired"] == 4
    assert acquisition["model.active_query_partition_evaluations"] == 399
    assert proof["model.exact_program_proof_rows_evaluated"] == 17


def test_independent_cold_replay_matches_exact_native_counter_semantics() -> None:
    from acfqp.construction_k7_standard_2048_expression_long_preregistration_v23 import INITIAL_BOARDS
    from acfqp.domains.standard_2048 import state_from_board_v1

    document, counters = verifier._independent_cold(state_from_board_v1(INITIAL_BOARDS[0]))
    assert document["route_or_certificate_authority"] is False
    assert counters["evaluation.exact_ground_steps"] > 0
    assert counters["evaluation.exact_ground_steps"] == counters["evaluation.exact_bellman_backups"]


def test_unexplained_nonzero_counter_is_rejected() -> None:
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionAccountedSemanticVerifierV25Error
    ):
        verifier._assert_sparse_values(
            {"model.world_model_freezes": 1, "process.launches": 1},
            {"model.world_model_freezes": 1},
            "attack",
        )


def test_full_v24_semantics_replay_independently(tmp_path: Path) -> None:
    root = tmp_path / "accounted"
    produced = campaign.run_standard_2048_expression_accounted_campaign_v24(root)
    result = verifier.verify_standard_2048_expression_accounting_semantics_v25(
        produced.canonical_bytes, root
    )
    document = result.to_document()
    assert document["independent_h3_certificate_replay_count"] == 128
    assert document["independent_cold_checkpoint_replay_count"] == 12
    assert document["registered_profile_counter_completeness_candidate_verified"] is True
    assert document["global_counter_completeness_gate_passed"] is False
    assert document["official_execution_allowed"] is False


def test_missing_output_root_is_rejected() -> None:
    with pytest.raises(Exception):
        verifier.verify_standard_2048_expression_accounting_semantics_v25(
            b"{}", Path("/definitely/not/a/v24/output/root")
        )
