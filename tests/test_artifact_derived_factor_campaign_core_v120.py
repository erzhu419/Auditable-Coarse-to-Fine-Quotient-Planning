from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.artifact_derived_factor_campaign_core_v120 import (
    build_artifact_derived_factor_occurrence_v120,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import dual_budget_config_v119


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v120_development_occurrence_uses_only_artifact_derived_projection():
    sources = _sources()
    library = derive_artifact_factor_projection_v120(sources)
    row = build_artifact_derived_factor_occurrence_v120(
        dual_budget_config_v119(),
        seed=1_032_001,
        episode_indices=(266, 267, 268),
        artifact_factor_library=library,
        source_campaign_bytes=sources,
        strict_complete_factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["registered_gate"]["hand_written_factor_template_count_zero"] is True
    assert row["artifact_factor_library"]["hand_written_factor_template_count"] == 0
    assert row["partial_prior_acquisition"]["artifact_factor_library_id"] == row[
        "artifact_factor_library_id"
    ]
    assert row["registered_gate"][
        "partial_candidate_retains_unknown_higher_order_residual"
    ] is True
    assert row["accounting"]["same_epoch_genesis_authorized_cache_hits"] > 0
    assert row["strict_no_prior_complete_model_control"]["attempt_count"] == 1
    assert row["complete_ground_world_model_synthesized"] is False
    assert row["official_scalar_cost"] is None
