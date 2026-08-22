from pathlib import Path

import pytest

from acfqp.cross_domain_relational_factor_bank_campaign_core_v150 import (
    TARGET_FAMILIES,
    build_cross_domain_relational_factor_bank_campaign_document_v150,
    build_cross_domain_relational_factor_bank_occurrence_v150,
)
from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@pytest.mark.parametrize("family", TARGET_FAMILIES)
def test_v150_historical_cross_domain_planner_abstention_closes(family):
    config = packet_batching_config_v134()
    config["families"][family]["maximum_acquisition_labels"] = 1_536
    row = build_cross_domain_relational_factor_bank_occurrence_v150(
        config,
        family=family,
        seed=1_047_231,
        episode_indices=(561, 562),
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            ROOT / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["paired_label_reduction"] > 0
    assert row["incomplete_abstract_path_never_used_as_execution_authority"] is True
    for key in (
        "anonymous_relational_factor_prior_owned_sequence",
        "strict_no_prior_owned_sequence",
    ):
        assert row[key]["certified_legal_search_remains_fallback_authority"] is True
        assert all(
            episode["every_execution_action_has_content_addressed_receipt"]
            for episode in row[key]["episodes"]
        )


def test_v150_historical_four_family_campaign_exercises_abstention():
    config = packet_batching_config_v134()
    for family in TARGET_FAMILIES:
        config["families"][family]["maximum_acquisition_labels"] = 1_536
    config.update(
        target_occurrences=[
            {"family": family, "seed": 1_047_231} for family in TARGET_FAMILIES
        ],
        target_episode_indices=(561, 562),
        target_worker_count=2,
        required_target_occurrence_count=4,
    )
    document = build_cross_domain_relational_factor_bank_campaign_document_v150(
        config,
        preregistration_id="1" * 64,
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            ROOT / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
    )
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "v149_preserved_failure_exercised_action_path_boundary"
    ] is True
    assert document["incomplete_abstract_plan_abstention_count"] == 0
    assert document["v149_identity_rerun"] is False
