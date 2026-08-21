import hashlib

from acfqp import construction_k7_abstract_execution_utilization_preregistration_v101 as pre


def test_v101_preregistration_freezes_execution_utilization_before_outcomes():
    value = pre.verify_abstract_execution_utilization_preregistration_v101(
        pre.freeze_abstract_execution_utilization_preregistration_v101()
    )
    document = value.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["source_closure"][
        "frozen_before_any_registered_v101_target_outcome"
    ] is True
    assert document["construction_contract"][
        "search_receipts_are_not_counted_as_executed_actions"
    ] is True
    assert document["claim_boundary"][
        "registered_multistep_execution_primarily_abstract_ordered_verified"
    ] is False
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )


def test_v101_preregistration_uses_fresh_occurrences_and_two_workers():
    config = pre.campaign_config_v101()
    assert config["target_occurrences"] == [
        {"family": family, "seed": seed}
        for family, seed in pre.TARGET_OCCURRENCES
    ]
    assert tuple(config["target_episode_indices"]) == (101, 102, 103)
    assert config["target_worker_count"] == 2
