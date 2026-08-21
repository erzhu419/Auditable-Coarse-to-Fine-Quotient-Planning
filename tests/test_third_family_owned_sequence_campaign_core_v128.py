from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_modular_routing_adapter_v128 import FAMILY, modular_routing_config_v128
from acfqp.third_family_owned_sequence_campaign_core_v128 import build_third_family_owned_sequence_occurrence_v128


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _source():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v128_development_identity_reuses_owned_sequence_on_modular_routing():
    source = _source()
    document = build_third_family_owned_sequence_occurrence_v128(
        modular_routing_config_v128(),
        seed=1_030_006,
        episode_indices=(314, 315, 316),
        artifact_factor_library=derive_artifact_factor_projection_v120(source),
        source_campaign_bytes=source,
        strict_complete_factor_library=v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
    )
    assert document["target_family"] == FAMILY
    assert document["registered_gate"]["passed"] is True
    assert document["same_v126_owned_sequence_reused_without_family_dispatch"] is True
    assert document["accounting"] == {
        "partial_prior_acquisition_labels": 20,
        "strict_control_matched_prefix_labels": 20,
        "strict_complete_model_attempt_count": 1,
        "certificate_local_labels": 27,
        "lifetime_target_labels": 47,
        "execution_steps": 18,
        "abstract_planning_compute_events": 5220,
        "matched_uncached_planning_compute_events": 11800,
        "planning_compute_events_avoided_against_uncached": 6580,
        "dependency_derivation_compute_events": 57,
        "standalone_model_epoch_reconstructions": 6,
        "generic_model_program_support_checks": 2040,
        "direct_generic_factor_program_plans": 17,
        "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    assert document["retained_v113_sequence_orchestration_present"] is False
    assert document["retained_v119_sequence_orchestration_present"] is False
    assert document["official_scalar_cost"] is None
