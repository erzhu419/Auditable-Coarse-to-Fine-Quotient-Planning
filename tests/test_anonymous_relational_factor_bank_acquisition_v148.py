from pathlib import Path

from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    build_maintenance_cascade_adapter_v144,
    maintenance_cascade_config_v144,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v148_same_pool_relational_prior_closes_on_frozen_source_occurrence():
    campaign = loads_canonical_json(
        (ROOT / "v145_certificate_local_recovery_union_campaign.json").read_bytes()
    )
    occurrence = campaign["target_occurrences"][0]
    config = maintenance_cascade_config_v144()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_024
    adapter = build_maintenance_cascade_adapter_v144(occurrence["seed"], config)
    arms = acquire_matched_anonymous_relational_factor_bank_arms_v148(
        adapter,
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        config,
    )
    prior = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    strict = arms["STRICT_NO_PRIOR"]["document"]
    assert prior["only_arm_switch_is_anonymous_relational_prior"] is True
    assert strict["only_arm_switch_is_anonymous_relational_prior"] is True
    assert prior["same_generic_atomic_hypothesis_pool"] is True
    assert strict["same_generic_atomic_hypothesis_pool"] is True
    assert prior["anonymous_relational_instantiation"][
        "exact_relational_instantiation_count"
    ] > 0
    assert prior["artifact_expression_selected_count"] > 0
    assert prior["relational_artifact_expression_selected_count"] > 0
    assert prior["ground_support_labels"] <= strict["ground_support_labels"]
    assert prior["complete_world_model_claimed"] is False
