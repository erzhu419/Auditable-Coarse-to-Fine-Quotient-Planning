import hashlib

from acfqp import construction_k7_true_bit_partial_preregistration_v58r1 as subject


def test_v58r1_preregistration_is_outcome_free_and_fresh():
    value = subject.freeze_true_bit_partial_preregistration_v58r1()
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["claim_boundary"]["registered_outcome_observed"] is False
    assert document["matched_acquisition_contract"][
        "reachable_frontier_exhaustion_stop_available"
    ] is False
    assert document["matched_acquisition_contract"][
        "heuristic_mdl_information_units_available"
    ] is False
    assert len(value.canonical_bytes) > 10_000
    assert len(hashlib.sha256(value.canonical_bytes).hexdigest()) == 64


def test_v58r1_config_has_36_fresh_occurrences_and_separate_axes():
    config = subject.campaign_config_v58r1()
    assert sum(len(spec["target_seeds"]) for spec in config["families"].values()) == 36
    assert config["planning_seed_count_per_family"] == 1
    assert config["worker_count"] == 4
    assert "predictive_evidence_credit_units_per_bit" not in config
