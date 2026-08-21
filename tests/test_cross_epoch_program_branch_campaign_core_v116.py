from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_projected_program_memo_preregistration_v115 as v115_pre
from acfqp.cross_epoch_program_branch_campaign_core_v116 import (
    build_cross_epoch_program_branch_campaign_document_v116,
)


def test_v116_historical_three_family_development_gate():
    config = v115_pre.campaign_config_v115()
    config.update(
        target_occurrences=[
            {"family": "BALANCED_BATCH_REFINEMENT", "seed": 1_027_101},
            {"family": "COUPLED_EXCHANGE", "seed": 1_027_201},
            {"family": "MAINTENANCE_CASCADE", "seed": 1_027_301},
        ],
        required_target_occurrence_count=3,
        target_worker_count=2,
    )
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_cross_epoch_program_branch_campaign_document_v116(
        config,
        preregistration_id="development-only",
        v115_campaign_id=v115_pre.V114_CAMPAIGN_ID,
        v115_verification_id=v115_pre.V114_VERIFICATION_ID,
        factor_library=factor_library,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"][
        "additional_cross_epoch_program_branch_cache_hits"
    ] > 0
    assert document["accounting"]["cross_epoch_planning_compute_events"] < document[
        "accounting"
    ]["matched_v115_planning_compute_events"]
    assert document["compiled_model_or_cache_used_as_safety_authority"] is False
