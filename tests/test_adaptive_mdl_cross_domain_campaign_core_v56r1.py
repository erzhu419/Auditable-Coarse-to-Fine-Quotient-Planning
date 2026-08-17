from __future__ import annotations

import pytest

from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp import construction_k7_domain_registry_extension_v56r1 as domains_v56r1
from acfqp.adaptive_mdl_cross_domain_campaign_core_v56r1 import (
    build_adaptive_mdl_cross_domain_campaign_document_v56r1,
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
            "episode": (
                domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_EPISODE_V56_DOMAIN
            ),
            "validation": (
                domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_ISOLATED_VALIDATION_V56_DOMAIN
            ),
            "ood": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_OOD_REJECTION_V56_DOMAIN,
        },
        "successor_domains": {
            "acquisition": (
                domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_ACQUISITION_V56R1_DOMAIN
            ),
            "sample_tax": (
                domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_SAMPLE_TAX_V56R1_DOMAIN
            ),
            "campaign": (
                domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_CAMPAIGN_V56R1_DOMAIN
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
                "target_seeds": (569_930, 569_931),
                "planning_seed_count": 1,
                "maximum_acquisition_labels": 128,
            },
            "COUPLED_EXCHANGE": {
                "stage_count": 7,
                "primary_base": 5,
                "target_seeds": (569_940, 569_941),
                "planning_seed_count": 1,
                "maximum_acquisition_labels": 160,
            },
        },
        "worker_count": 2,
        "factor_signature_credit_units": 16,
        "confidence_reserve_units": 48,
        "invalidated_candidate_penalty_units": 16,
        "minimum_reusable_factor_count": 3,
        "maximum_relation_output_candidate": 64,
        "maximum_local_resyntheses": 8,
        "factor_library_id": _LIBRARY["factor_library_id"],
        "factor_library_labels": 20,
        "v55_campaign_id": (
            "ea85860f499ac631a7f3e6b306974be2a2d7c9de88cde3cf492380ebd59ec589"
        ),
        "v55_verification_id": (
            "ec6fe8ee01a663030ffdd146613d1f4231000f27bae0773f47c15b6d398fd1f6"
        ),
        "v56_failure_id": (
            "7d0e88ba7d78d96c6ff635515313707cda915fde39f5902e0a7d202bcf05348c"
        ),
    }


@pytest.fixture(scope="module")
def campaign():
    return build_adaptive_mdl_cross_domain_campaign_document_v56r1(
        _config(), "d" * 64, _LIBRARY
    )


def test_v56r1_exact_frontier_rule_closes_failed_v56_case(campaign):
    strict = campaign["acquisitions"]["STRICT_NO_PRIOR"]
    coupled = [row for row in strict if row["family"] == "COUPLED_EXCHANGE"]
    assert len(coupled) == 2
    assert all(row["stopped_by_exact_reachable_frontier_closure"] for row in coupled)
    assert all(
        row["terminal_stop_update"]["current_candidate_replay_disagreement_count"]
        == 0
        and row["terminal_stop_update"]["unresolved_frontier_disagreement_units"]
        == 0
        for row in coupled
    )


def test_v56r1_has_no_floor_block_or_calibration(campaign):
    assert campaign["minimum_candidate_label_floor_consumed"] is False
    assert campaign["confirmation_block_consumed"] is False
    assert campaign["full_frontier_target_layout_calibration_consumed"] is False
    assert campaign["exact_frontier_closure_is_a_stop_not_a_calibration_input"]
    assert all(
        row["candidate_synthesis_attempted_after_every_support_query"]
        and not row["minimum_candidate_label_floor_consumed"]
        and not row["confirmation_block_consumed"]
        for rows in campaign["acquisitions"].values()
        for row in rows
    )


def test_v56r1_matched_single_switch_reduces_both_domain_sample_tax(campaign):
    sample = campaign["sample_tax"]
    assert sample["factor_prior_on_acquisition_labels"] == 409
    assert sample["strict_no_prior_acquisition_labels"] == 460
    assert sample["incremental_acquisition_label_reduction"] == 51
    assert sample["online_label_reduction_including_local_recovery"] == 50
    assert sample["lifetime_label_reduction_after_factor_library_tax"] == 30
    assert sample["diagnostic_break_even_occurrence_count"] == 2
    assert sample["family_projections"]["BALANCED_BATCH_REFINEMENT"][
        "incremental_label_reduction"
    ] == 28
    assert sample["family_projections"]["COUPLED_EXCHANGE"][
        "incremental_label_reduction"
    ] == 23
    assert sample["only_registered_factor_code_credit_switched"] is True


def test_v56r1_planning_recovery_ood_and_claim_locks(campaign):
    plans = [
        [(row["family"], row["seed"], row["action_keys"]) for row in campaign[
            "episodes"
        ][arm]]
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    ]
    assert plans[0] == plans[1] == plans[2]
    assert len(campaign["failed_certificates"]) == 7
    assert len(campaign["local_distinctions"]) == 7
    assert all(
        row["query_after_failed_certificate"]
        for row in campaign["local_distinctions"]
    )
    assert campaign["ood_rejection"]["prior_transfer_attempted"] is False
    assert campaign["official_execution_allowed"] is False
    assert campaign["official_scalar_cost"] is None
    assert campaign["official_N_break_even"] is None
    assert campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
