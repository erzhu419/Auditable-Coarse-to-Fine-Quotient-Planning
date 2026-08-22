from pathlib import Path

from acfqp.construction_k7_relation_keyed_bank_preregistration_v151 import (
    TARGET_EPISODE_INDICES,
    TARGET_OCCURRENCES,
    freeze_relation_keyed_bank_preregistration_v151,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v151_preregistration_is_outcome_free_and_fresh():
    registration = freeze_relation_keyed_bank_preregistration_v151(
        (ROOT / "v150_certified_planner_abstention_campaign.json").read_bytes(),
        (ROOT / "v150_certified_planner_abstention_verification.json").read_bytes(),
    )
    document = registration.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["registered_v151_target_outcome_observed"] is False
    assert len(TARGET_OCCURRENCES) == 6
    assert len({seed for _family, seed in TARGET_OCCURRENCES}) == 6
    assert TARGET_EPISODE_INDICES == (601, 602, 603, 604)
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
