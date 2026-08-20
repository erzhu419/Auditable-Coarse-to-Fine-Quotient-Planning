from acfqp.construction_k7_role_free_prequential_preregistration_v71 import (
    freeze_role_free_prequential_preregistration_v71,
    verify_role_free_prequential_preregistration_v71,
)


def test_v71_preregistration_is_outcome_free_and_factorial():
    value = verify_role_free_prequential_preregistration_v71(
        freeze_role_free_prequential_preregistration_v71()
    )
    document = value.to_document()
    assert document["fresh_registered_target_execution_performed"] is False
    assert document["source_closure"][
        "frozen_before_any_registered_v71_target_outcome"
    ] is True
    assert len(document["factorial_acquisition_contract"]["arms"]) == 4
    assert document["registered_gate"]["sample_reduction_required"] is False
    assert document["claim_boundary"]["online_actual_sample_reduction_claimed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    failure = document["preserved_development_failure"]
    assert failure["prior_status"].endswith("FAILED_NONCERTIFICATE")
    seeds = [
        seed
        for family in ("BALANCED_BATCH_REFINEMENT", "COUPLED_EXCHANGE", "MAINTENANCE_CASCADE")
        for seed in document["target_families"][family]["target_seeds"]
    ]
    assert len(seeds) == len(set(seeds)) == 6
