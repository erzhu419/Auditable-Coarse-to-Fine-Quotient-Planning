from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_three_family_incremental_successor_preregistration_v114 as v114_pre
from acfqp.projected_program_memo_campaign_core_v115 import (
    build_projected_program_memo_campaign_document_v115,
)


def test_v115_historical_three_family_development_gate():
    config = v114_pre.campaign_config_v114()
    config.update(
        target_occurrences=[
            {"family": "BALANCED_BATCH_REFINEMENT", "seed": 1_026_101},
            {"family": "COUPLED_EXCHANGE", "seed": 1_026_201},
            {"family": "MAINTENANCE_CASCADE", "seed": 1_026_301},
        ],
        required_target_occurrence_count=3,
        target_worker_count=2,
    )
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_projected_program_memo_campaign_document_v115(
        config,
        preregistration_id="development-only",
        v114_campaign_id=v114_pre.V113_CAMPAIGN_ID,
        v114_verification_id=v114_pre.V113_VERIFICATION_ID,
        factor_library=factor_library,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["projected_program_branch_cache_hits"] > 0
    assert document["accounting"][
        "projected_program_memo_planning_compute_events"
    ] < document["accounting"]["matched_v113_planning_compute_events"]
    assert document["compiled_model_or_memo_used_as_safety_authority"] is False
