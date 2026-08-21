from acfqp import construction_k7_coordinate_aligned_target_preregistration_v87r1 as previous
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp.construction_k7_action_applicability_model_v87 import load_action_applicability_model_v87
from acfqp.construction_k7_projected_model_artifact_v86 import load_projected_model_artifact_v86
from acfqp.generic_coordinate_alignment_independent_replay_v61 import rederive_coordinate_alignment_v61
from acfqp.replayable_coordinate_target_campaign_core_v88 import build_replayable_coordinate_target_campaign_document_v88


def test_v88_fixture_embeds_every_input_needed_to_rederive_alignment():
    config = previous.campaign_config_v87r1()
    config.update(
        target_seeds=(888_883,),
        target_worker_count=1,
        required_target_occurrence_count=1,
        minimum_replayable_completed_target_count=1,
        v87r1_campaign_id="33e9d49933e8b2d94169911170732b178095ce55fe52258c6ccfb9d425990739",
        v87r1_verification_id="9a5fdb135fcebe2e4a31077e7a542d9af2338ecb1c2d76eda1e3f4f72eedd29d",
    )
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    factor_library = v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    result = build_replayable_coordinate_target_campaign_document_v88(
        config,
        "fixture-preregistration",
        projected["model_artifact_id"],
        applicability["model_artifact_id"],
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        factor_library,
    )
    occurrence = result["target_occurrences"][0]
    replayed = rederive_coordinate_alignment_v61(
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        occurrence["target_common_partial_acquisition"]["candidate"],
        occurrence["target_common_partial_raw_transition_rows"],
        occurrence["target_common_partial_action_catalogue"],
    )
    assert replayed == occurrence["coordinate_alignment"]
    assert result["registered_gate"]["passed"] is True
    assert result["registered_gate"][
        "raw_alignment_inputs_embedded_on_every_completed_target"
    ] is True
    assert result["sample_tax_reduction_verified"] is False
