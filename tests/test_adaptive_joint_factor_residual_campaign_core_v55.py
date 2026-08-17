from __future__ import annotations

import pytest

from acfqp import construction_k7_domain_registry_extension_v55 as domains
from acfqp.adaptive_joint_factor_residual_campaign_core_v55 import (
    build_adaptive_joint_factor_residual_campaign_document_v55,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
)


_LIBRARY = {
    "factor_library_id": "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162",
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
            "candidate": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_CANDIDATE_V55_DOMAIN,
            "acquisition": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_ACQUISITION_V55_DOMAIN,
            "failed_certificate": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_FAILED_CERTIFICATE_V55_DOMAIN,
            "distinction": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_LOCAL_DISTINCTION_V55_DOMAIN,
            "episode": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_EPISODE_V55_DOMAIN,
            "validation": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_ISOLATED_VALIDATION_V55_DOMAIN,
            "ood": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_OOD_REJECTION_V55_DOMAIN,
            "sample_tax": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_SAMPLE_TAX_V55_DOMAIN,
            "campaign": domains.CONSTRUCTION_K7_ADAPTIVE_JOINT_CAMPAIGN_V55_DOMAIN,
        },
        "generic_domains": {
            "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
            "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
            "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
            "model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
        },
        "terminal_tokens": {"A": 9_001, "F": 9_007, "S": 9_011},
        "target_stage_count": 9,
        "target_unit_base": 5,
        "target_seeds": tuple(range(559_930, 559_938)),
        "planning_validation_seed_count": 2,
        "worker_count": 2,
        "minimum_candidate_labels": 80,
        "maximum_acquisition_labels": 128,
        "confirmation_block_size": 4,
        "factor_prior_weight": 64,
        "exact_likelihood_block_weight": 64,
        "stopping_weight": 64,
        "minimum_reusable_factor_count": 3,
        "maximum_relation_output_candidate": 64,
        "maximum_local_resyntheses": 8,
        "factor_library_id": _LIBRARY["factor_library_id"],
        "factor_library_labels": 20,
        "v54r1_campaign_id": "48f49e489e1cc5dfc98ec14c23565f66edfa93d51e15ca23f66f4668cc377223",
        "v54r1_verification_id": "a4d71d1f6517c032e8f7f14b4fd8b2e6ab9560ca96bd4741e2d5874ad06b5acc",
    }


@pytest.fixture(scope="module")
def campaign():
    return build_adaptive_joint_factor_residual_campaign_document_v55(
        _config(), "d" * 64, _LIBRARY
    )


def test_v55_adaptive_joint_acquisition_removes_full_frontier_calibration(campaign):
    assert campaign["full_frontier_target_layout_calibration_consumed"] is False
    assert campaign["shared_residual_scaffold_consumed"] is False
    assert campaign["predeclared_reusable_factor_slots_consumed"] is False
    for arm in campaign["acquisitions"].values():
        assert len(arm) == 8
        assert all(row["full_frontier_calibration_consumed"] is False for row in arm)
        assert all(row["candidate"]["factorable_reusable_count"] == 3 for row in arm)
        assert all(row["candidate"]["factorable_novel_count"] == 1 for row in arm)
        assert all(row["candidate"]["residual_schema_bound_count"] == 2 for row in arm)


def test_v55_single_prior_switch_reduces_incremental_and_lifetime_labels(campaign):
    sample = campaign["sample_tax"]
    assert sample["factor_prior_on_acquisition_labels"] == 640
    assert sample["strict_no_prior_acquisition_labels"] == 672
    assert sample["incremental_acquisition_label_reduction"] == 32
    assert sample["online_label_reduction_including_local_recovery"] == 32
    assert sample["lifetime_label_reduction_after_factor_library_tax"] == 12
    assert sample["same_synthesizer_and_stopping_formula"] is True
    assert sample["only_factor_prior_initial_weight_switched"] is True


def test_v55_receding_plans_match_direct_and_ground_only_after_failure(campaign):
    action_rows = [
        [row["action_keys"] for row in campaign["episodes"][arm]]
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    ]
    assert action_rows[0] == action_rows[1] == action_rows[2]
    assert all(
        row["success"]
        for values in campaign["episodes"].values()
        for row in values
    )
    assert len(campaign["failed_certificates"]) == len(
        campaign["local_distinctions"]
    )
    assert all(
        row["query_after_failed_certificate"]
        for row in campaign["local_distinctions"]
    )


def test_v55_validation_is_isolated_and_ood_transfer_is_rejected(campaign):
    assert len(campaign["isolated_full_frontier_validations"]) == 2
    assert all(
        row["validation_rows_consumed_for_acquisition"] is False
        and row["validation_rows_consumed_for_binding"] is False
        and row["validation_rows_consumed_for_planning"] is False
        for row in campaign["isolated_full_frontier_validations"]
    )
    assert campaign["ood_rejection"]["factorable_reusable_count"] == 2
    assert campaign["ood_rejection"]["outcome"] == (
        "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER"
    )
    assert campaign["official_execution_allowed"] is False
    assert campaign["official_scalar_cost"] is None
    assert campaign["official_N_break_even"] is None
