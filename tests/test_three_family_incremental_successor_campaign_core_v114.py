from acfqp import construction_k7_incremental_abstract_successor_preregistration_v113 as v113_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.three_family_incremental_successor_campaign_core_v114 import (
    build_three_family_incremental_successor_occurrence_v114,
)


def test_v114_historical_third_family_uses_unchanged_incremental_compiler():
    row = build_three_family_incremental_successor_occurrence_v114(
        v113_pre.campaign_config_v113(),
        family="COUPLED_EXCHANGE",
        seed=682_103,
        episode_indices=(221, 222, 223),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["registered_gate"][
        "incremental_model_exactly_matches_full_v105_rebuild"
    ] is True
    assert row["accounting"][
        "incremental_model_update_compilation_events"
    ] < row["accounting"]["matched_full_rebuild_update_compilation_events"]
    assert row["compiled_model_used_as_safety_authority"] is False
