from __future__ import annotations

import pytest

from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp import construction_k7_domain_registry_extension_v57 as domains_v57
from acfqp.calibrated_mdl_three_domain_campaign_core_v57 import (
    build_calibrated_mdl_three_domain_campaign_document_v57,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
)


_LIBRARY = {
    "factor_library_id": (
        "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
    ),
    "cross_schema_subprograms": [
        {
            "signature_sha256": signature,
            "source_schema_pairs": [[7, 5], [9, 6]],
        }
        for signature in (
            "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e",
            "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072",
            "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5",
        )
    ],
}


def _config():
    return {
        "domains": {
            "candidate": (
                domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_CANDIDATE_V56_DOMAIN
            ),
            "failed_certificate": (
                domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_FAILED_CERTIFICATE_V56_DOMAIN
            ),
            "distinction": (
                domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_LOCAL_DISTINCTION_V56_DOMAIN
            ),
            "episode": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_EPISODE_V56_DOMAIN,
            "validation": (
                domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_ISOLATED_VALIDATION_V56_DOMAIN
            ),
            "ood": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_OOD_REJECTION_V56_DOMAIN,
        },
        "successor_domains": {
            "acquisition": (
                domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_ACQUISITION_V57_DOMAIN
            ),
            "sample_tax": (
                domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_SAMPLE_TAX_V57_DOMAIN
            ),
            "campaign": (
                domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_CAMPAIGN_V57_DOMAIN
            ),
        },
        "generic_domains": {
            "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
            "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
            "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
            "model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
        },
        "terminal_tokens": {"A": 9_001, "F": 9_007, "S": 9_011},
        "families": {
            "BALANCED_BATCH_REFINEMENT": {
                "stage_count": 9,
                "unit_base": 5,
                "target_seeds": (579_910, 579_911),
                "planning_seed_count": 1,
                "maximum_acquisition_labels": 128,
            },
            "COUPLED_EXCHANGE": {
                "stage_count": 7,
                "primary_base": 5,
                "target_seeds": (579_920, 579_921),
                "planning_seed_count": 1,
                "maximum_acquisition_labels": 160,
            },
            "MAINTENANCE_CASCADE": {
                "zone_count": 7,
                "repair_base": 2,
                "target_seeds": (579_930, 579_931),
                "planning_seed_count": 1,
                "maximum_acquisition_labels": 200,
            },
        },
        "worker_count": 3,
        "factor_signature_credit_units": 16,
        "invalidated_candidate_penalty_units": 16,
        "minimum_reusable_factor_count": 3,
        "maximum_relation_output_candidate": 64,
        "maximum_local_resyntheses": 8,
        "global_alpha_denominator": 20,
        "epoch_alpha_spending_base": 2,
        "success_evalue_multiplier_numerator": 3,
        "success_evalue_multiplier_denominator": 2,
        "predictive_evidence_credit_units_per_bit": 2,
        "factor_library_id": _LIBRARY["factor_library_id"],
        "factor_library_labels": 20,
        "v56r1_campaign_id": (
            "0f5032377cd52b021133fe03a4ab4a34613a230bd3ae25efa43e02ca911521a8"
        ),
        "v56r1_verification_id": (
            "8aa9de632593f60ae8ac59cac3f0affa25568caf011211271913d8732e66733f"
        ),
    }


@pytest.fixture(scope="module")
def campaign():
    return build_calibrated_mdl_three_domain_campaign_document_v57(
        _config(), "d" * 64, _LIBRARY
    )


def test_v57_has_no_fixed_floor_block_reserve_or_frontier_stop(campaign):
    assert campaign["minimum_candidate_label_floor_consumed"] is False
    assert campaign["confirmation_block_consumed"] is False
    assert campaign["fixed_confidence_reserve_consumed"] is False
    assert campaign["reachable_frontier_exhaustion_stop_consumed"] is False
    for rows in campaign["acquisitions"].values():
        assert all(
            row["terminal_stop_update"][
                "calibrated_evalue_threshold_met"
            ]
            and row["terminal_stop_update"][
                "anytime_valid_for_registered_predictive_null"
            ]
            and not row["reachable_frontier_exhaustion_input_consumed"]
            for row in rows
        )


def test_v57_same_synthesizer_reduces_tax_in_three_families(campaign):
    sample = campaign["sample_tax"]
    assert sample["factor_prior_on_acquisition_labels"] == 482
    assert sample["strict_no_prior_acquisition_labels"] == 585
    assert sample["incremental_acquisition_label_reduction"] == 103
    assert sample["online_label_reduction_including_local_recovery"] == 103
    assert sample["lifetime_label_reduction_after_factor_library_tax"] == 83
    assert sample["diagnostic_break_even_occurrence_count"] == 3
    assert {
        key: row["incremental_label_reduction"]
        for key, row in sample["family_projections"].items()
    } == {
        "BALANCED_BATCH_REFINEMENT": 10,
        "COUPLED_EXCHANGE": 60,
        "MAINTENANCE_CASCADE": 33,
    }


def test_v57_abstract_prior_switch_is_matched_and_ground_successful(campaign):
    prior = campaign["episodes"]["ANONYMOUS_FACTOR_PRIOR_ON"]
    no_prior = campaign["episodes"]["STRICT_NO_PRIOR"]
    assert [(row["family"], row["action_keys"]) for row in prior] == [
        (row["family"], row["action_keys"]) for row in no_prior
    ]
    assert all(
        row["success"] for rows in campaign["episodes"].values() for row in rows
    )
    assert campaign["matched_direct_baseline_same_ground_kernel_and_objective"]
    assert campaign["identical_action_sequence_across_distinct_planners_required"] is False
    assert len(campaign["failed_certificates"]) == 10
    assert len(campaign["local_distinctions"]) == 10


def test_v57_isolated_validation_ood_and_claim_locks(campaign):
    assert {row["family"] for row in campaign["isolated_full_frontier_validations"]} == {
        "BALANCED_BATCH_REFINEMENT",
        "COUPLED_EXCHANGE",
        "MAINTENANCE_CASCADE",
    }
    assert all(
        row["validation_rows_consumed_for_acquisition"] is False
        and row["validation_rows_consumed_for_binding"] is False
        and row["validation_rows_consumed_for_planning"] is False
        for row in campaign["isolated_full_frontier_validations"]
    )
    assert campaign["ood_rejection"]["prior_transfer_attempted"] is False
    assert campaign["distribution_free_global_dynamics_confidence_claimed"] is False
    assert campaign["official_execution_allowed"] is False
    assert campaign["official_scalar_cost"] is None
    assert campaign["official_N_break_even"] is None
    assert campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
