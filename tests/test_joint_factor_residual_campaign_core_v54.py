from __future__ import annotations

import pytest

from acfqp.joint_factor_residual_campaign_core_v54 import (
    build_joint_factor_residual_campaign_document_v54,
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
    content_id,
)


_LIBRARY = {
    "factor_library_id": "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162",
    "cross_schema_subprograms": [
        {
            "signature_sha256": "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e",
            "source_schema_pairs": [[4, 3], [7, 5]],
        },
        {
            "signature_sha256": "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072",
            "source_schema_pairs": [[4, 3], [7, 5]],
        },
        {
            "signature_sha256": "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5",
            "source_schema_pairs": [[4, 3], [7, 5]],
        },
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
        "source_seeds": (549_101, 549_102, 549_103),
        "maximum_source_labels_per_occurrence": 128,
        "target_stage_count": 7,
        "target_unit_base": 4,
        "target_seeds": (549_201,),
        "maximum_target_layout_labels": 64,
        "layout_confirmation_count": 2,
        "maximum_relation_output_candidate": 64,
        "minimum_reusable_factor_count": 3,
        "v51_factor_library_id": _LIBRARY["factor_library_id"],
        "factor_library_labels": 370,
    }


@pytest.fixture(scope="module")
def campaign():
    return build_joint_factor_residual_campaign_document_v54(
        _config(), "0" * 64, _LIBRARY
    )


def test_joint_campaign_reconstructs_full_program_and_uses_no_target_scaffold(campaign):
    model = campaign["joint_world_model"]
    assert model["complete_target_program_synthesized_from_raw_observations"] is True
    assert model["factorable_reusable_count"] >= 3
    assert model["residual_schema_bound_count"] >= 1
    assert campaign["v51_target_program_consumed"] is False
    assert campaign["v51_reused_factor_slot_inventory_consumed"] is False
    assert model["shared_residual_scaffold_consumed"] is False
    assert model["predeclared_reusable_factor_slots_consumed"] is False


def test_joint_campaign_plans_fresh_target_and_recovers_only_after_failure(campaign):
    assert campaign["structural_episodes"][0]["success"] is True
    assert campaign["strict_episodes"][0]["success"] is True
    assert campaign["structural_episodes"][0]["action_keys"] == campaign[
        "strict_episodes"
    ][0]["action_keys"]
    assert campaign["failed_certificates"]
    assert len(campaign["failed_certificates"]) == len(campaign["local_distinctions"])
    assert all(
        row["query_after_failed_certificate"] is True
        for row in campaign["local_distinctions"]
    )


def test_joint_campaign_strictly_rejects_ood_and_keeps_gates_locked(campaign):
    assert campaign["ood_rejection"]["outcome"] == "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER"
    assert campaign["ood_rejection"]["prior_transfer_attempted"] is False
    assert campaign["official_execution_allowed"] is False
    assert campaign["official_scalar_cost"] is None
    assert campaign["official_N_break_even"] is None
    assert campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    assert campaign["campaign_id"] == content_id(
        CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN, payload
    )
