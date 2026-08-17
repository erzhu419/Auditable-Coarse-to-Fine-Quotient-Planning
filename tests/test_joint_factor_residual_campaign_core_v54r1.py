from __future__ import annotations

import pytest

from acfqp.joint_factor_residual_campaign_core_v54r1 import (
    build_joint_factor_residual_campaign_document_v54r1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_EPISODE_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_FAILED_CERTIFICATE_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LOCAL_DISTINCTION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_OOD_REJECTION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_RAW_OBSERVATION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
)


_LIBRARY = {
    "factor_library_id": "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162",
    "cross_schema_subprograms": [
        {"signature_sha256": "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e", "source_schema_pairs": [[4, 3], [7, 5]]},
        {"signature_sha256": "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072", "source_schema_pairs": [[4, 3], [7, 5]]},
        {"signature_sha256": "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5", "source_schema_pairs": [[4, 3], [7, 5]]},
    ],
}


def _config():
    return {
        "domains": {
            "observation": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_RAW_OBSERVATION_V54_DOMAIN,
            "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
            "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
            "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
            "joint_model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
            "failed_certificate": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_FAILED_CERTIFICATE_V54_DOMAIN,
            "distinction": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LOCAL_DISTINCTION_V54_DOMAIN,
            "episode": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_EPISODE_V54_DOMAIN,
            "ood": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_OOD_REJECTION_V54_DOMAIN,
            "campaign": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN,
        },
        "terminal_tokens": {"A": 9_001, "F": 9_007, "S": 9_011},
        "source_stage_count": 6,
        "source_unit_base": 3,
        "source_seeds": (559_101, 559_102, 559_103),
        "maximum_source_labels_per_occurrence": 128,
        "target_stage_count": 7,
        "target_unit_base": 4,
        "target_seeds": (559_301, 559_302),
        "maximum_target_layout_labels": 128,
        "maximum_relation_output_candidate": 64,
        "minimum_reusable_factor_count": 3,
        "v51_factor_library_id": _LIBRARY["factor_library_id"],
        "factor_library_labels": 370,
        "v54_failure_id": "f5dbecac001b91c3a460fe4f7d4559a45bef631640f881c29e6e484f95c8b785",
    }


@pytest.fixture(scope="module")
def campaign():
    return build_joint_factor_residual_campaign_document_v54r1(
        _config(), "1" * 64, _LIBRARY
    )


def test_v54r1_jointly_discovers_factorable_and_residual_assignments(campaign):
    model = campaign["joint_world_model"]
    assert model["factorable_reusable_count"] >= 3
    assert model["factorable_novel_count"] >= 1
    assert model["residual_schema_bound_count"] >= 1
    assert model["shared_residual_scaffold_consumed"] is False
    assert model["predeclared_reusable_factor_slots_consumed"] is False
    assert campaign["frozen_failed_v54_predecessor_id"] == _config()["v54_failure_id"]


def test_v54r1_layout_planning_recovery_and_ood_boundaries(campaign):
    assert all(row["success"] for row in campaign["structural_episodes"])
    assert [row["action_keys"] for row in campaign["structural_episodes"]] == [
        row["action_keys"] for row in campaign["strict_episodes"]
    ]
    assert len(campaign["failed_certificates"]) == len(campaign["local_distinctions"])
    assert campaign["failed_certificates"]
    assert all(row["query_after_failed_certificate"] for row in campaign["local_distinctions"])
    assert all(row["relation_outputs_consumed_for_target_binding"] is False for row in campaign["target_layout_calibrations"])
    assert campaign["ood_rejection"]["outcome"] == "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER"
    assert campaign["official_execution_allowed"] is False
    assert campaign["official_scalar_cost"] is None
    assert campaign["official_N_break_even"] is None
