from pathlib import Path

from acfqp import construction_k7_open_world_composite_macro_execution_preregistration_v185 as preregistration


def test_v185_target_preregistration_is_fresh_and_fail_closed() -> None:
    document = preregistration.freeze_open_world_composite_macro_execution_preregistration_v185().to_document()
    assert document["execution_preregistration_id"] == preregistration.EXPECTED_PREREGISTRATION_ID
    assert document["fresh_target_outcomes_accessed"] is False
    assert document["offline_source_training_is_not_held_out_target_evidence"] is True
    assert document["source_checkpoint_label_counts"] == [24, 28]
    assert document["output_root_absent_at_preregistration"] is True
    assert document["same_identity_rerun_after_any_progress_forbidden"] is True
    assert document["producer_free_reconstruction_required"] is True
    assert document["only_macro_library_prior_toggled_between_arms"] is True
    assert document["new_low_level_primitive_opcode_invention_claimed"] is False
    assert document["official_execution_allowed"] is False
    root = Path(__file__).resolve().parents[1]
    assert not (root / document["output_root_relative_path"]).exists()
