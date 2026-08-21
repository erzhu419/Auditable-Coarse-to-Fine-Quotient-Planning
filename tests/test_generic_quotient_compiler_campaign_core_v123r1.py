from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_dual_budget_adapter_v119 import dual_budget_config_v119
from acfqp.generic_quotient_compiler_campaign_core_v123r1 import (
    build_generic_quotient_compiler_occurrence_v123r1,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v123r1_development_occurrence_retains_failure_and_succeeds():
    sources = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    config = dual_budget_config_v119()
    config["families"]["STOCHASTIC_DUAL_BUDGET_COMPOSITION"][
        "maximum_acquisition_labels"
    ] = 2_048
    row = build_generic_quotient_compiler_occurrence_v123r1(
        config,
        seed=1_033_002,
        episode_indices=(272, 273, 274),
        artifact_factor_library=derive_artifact_factor_projection_v120(sources),
        source_campaign_bytes=sources,
        strict_complete_factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["same_failed_v123_identity_rerun"] is False
    assert row["frozen_failed_v123_record_sha256"] == "84f32d6ed71ac0b4496d457662d5f750dacb9e77e37a51a17d6db6b6939b778e"
