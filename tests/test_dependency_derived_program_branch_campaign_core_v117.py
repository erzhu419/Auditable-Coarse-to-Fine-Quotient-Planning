from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_projected_program_memo_preregistration_v115 as v115_pre
from acfqp.dependency_derived_program_branch_campaign_core_v117 import (
    build_dependency_derived_program_branch_campaign_document_v117,
)


def test_v117_historical_three_family_development_gate():
    config = v115_pre.campaign_config_v115()
    config.update(
        target_occurrences=[
            {"family": "BALANCED_BATCH_REFINEMENT", "seed": 1_028_101},
            {"family": "COUPLED_EXCHANGE", "seed": 1_028_201},
            {"family": "MAINTENANCE_CASCADE", "seed": 1_028_301},
        ],
        target_episode_indices=(251, 252, 253),
        required_target_occurrence_count=3,
        target_worker_count=2,
    )
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_dependency_derived_program_branch_campaign_document_v117(
        config,
        preregistration_id="development-only",
        v116_campaign_id="development-v116",
        v116_verification_id="development-v116-verification",
        factor_library=factor_library,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"][
        "dependency_derived_planning_compute_events"
    ] == document["accounting"]["matched_v116_planning_compute_events"]
    assert document["registered_gate"][
        "every_occurrence_rederives_exact_dependency_and_rejects_changed_dependency"
    ] is True
    assert document["compiled_model_cache_or_receipt_used_as_safety_authority"] is False
