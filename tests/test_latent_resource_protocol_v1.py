from __future__ import annotations

import pytest

from acfqp.science.latent_resource_protocol_v1 import (
    ARM_ZERO_MASK_COORDINATE_INDICES_V1,
    LatentResourceProtocolV1Error,
    build_confirmatory_template_v1,
    build_pilot_protocol_v1,
    build_ratified_confirmatory_protocol_v1,
    validate_ratified_confirmatory_protocol_v1,
)


def test_pilot_is_nonconfirmatory_and_matched() -> None:
    protocol = build_pilot_protocol_v1()

    assert protocol["campaign_kind"] == "PILOT_NONCONFIRMATORY"
    assert protocol["arms"] == ["RAW_BOARD", "RESOURCE_STATE_ONLY"]
    assert protocol["network_contract"]["same_parameter_count_for_all_arms"] is True
    assert protocol["representation_contract"]["input_dimension_for_every_arm"] == 16
    assert protocol["statistics_gate"] == "NOT_RUN_PILOT"
    assert protocol["sample_efficiency_gate"] == "NOT_RUN_PILOT"
    assert protocol["claim_boundary"]["scientific_success_claimed"] is False
    assert protocol["claim_boundary"]["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert len(protocol["protocol_id"]) == 64
    assert (
        protocol["protocol_id"]
        == "f24521d272d8fb7b25ad8db1b0a1549a50b0f4aa91cdf6de78f9b5834d746620"
    )
    assert build_pilot_protocol_v1() == protocol


def test_confirmatory_template_uses_ten_seeds_joint_gate_and_ablations() -> None:
    protocol = build_confirmatory_template_v1()

    assert protocol["campaign_kind"] == "CONFIRMATORY_TEMPLATE_NOT_YET_AUTHORIZED"
    assert len(protocol["training_seeds"]) == 10
    assert protocol["statistics_gate"]["primary_test"] == "TWO_SIDED_WELCH_T_TEST"
    assert protocol["joint_success_gate"][
        "candidate_earliest_threshold_interactions_strictly_less"
    ] is True
    assert protocol["joint_success_gate"][
        "candidate_final_mean_primary_outcome_strictly_greater"
    ] is True
    assert "RESOURCE_STATE_ONLY_DROP_ANCHOR" in protocol["arms"]
    assert "RESOURCE_STATE_ONLY_DROP_LIQUIDITY" in protocol["arms"]
    assert protocol["representation_contract"][
        "state_only_resource_calls_no_transition_or_successor_kernel"
    ] is True
    assert protocol["authorization"].startswith("NOT_AUTHORIZED")
    assert protocol["confirmatory_execution_authorized"] is False
    assert protocol["claim_boundary"]["official_execution_allowed"] is False
    assert protocol["claim_boundary"]["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert protocol["confirmatory_ablation_contract"][
        "zero_mask_coordinate_indices_by_arm"
    ] == {arm: list(indices) for arm, indices in ARM_ZERO_MASK_COORDINATE_INDICES_V1}


def test_ratification_changes_only_science_execution_authority_and_source() -> None:
    protocol = build_ratified_confirmatory_protocol_v1("1" * 40)

    assert validate_ratified_confirmatory_protocol_v1(protocol) == protocol
    assert protocol["campaign_kind"] == "CONFIRMATORY_RATIFIED"
    assert protocol["authorization"] == "RATIFIED_FOR_EXECUTION"
    assert protocol["confirmatory_protocol_ratified"] is True
    assert protocol["confirmatory_execution_authorized"] is True
    assert protocol["claim_boundary"]["official_execution_allowed"] is False
    assert protocol["claim_boundary"]["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"

    protocol["training_seeds"][0] += 1
    with pytest.raises(LatentResourceProtocolV1Error):
        validate_ratified_confirmatory_protocol_v1(protocol)
