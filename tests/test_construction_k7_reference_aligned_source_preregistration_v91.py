from acfqp import construction_k7_reference_aligned_source_preregistration_v91 as pre


def test_v91_preregistration_identity_is_frozen():
    assert pre.PREREGISTRATION_ID == (
        "9a4d8dc9a8d40024708df19e6689d59b94aed082fa9c6468f4867c34604578de"
    )


def test_v91_preregistration_is_outcome_free_and_source_only():
    registration = pre.freeze_reference_aligned_source_preregistration_v91()
    document = registration.to_document()
    assert pre._source_facts() == pre._frozen_source_facts()  # noqa: SLF001
    assert document["fresh_registered_v91_execution_performed"] is False
    assert document["identity_contract"]["source_pool_seeds"] == [921101, 921102]
    assert document["resource_schedule"]["source_worker_count"] == 2
    assert document["registered_gate"][
        "multiple_residual_proposals_jointly_compiled_required"
    ] is True
    assert document["claim_boundary"]["fresh_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
