"""Frozen failed V54 registered predecessor; it must never be rerun."""

from __future__ import annotations

import hashlib

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN,
    canonical_json_bytes,
    content_id,
)


FAILURE_ID = "f5dbecac001b91c3a460fe4f7d4559a45bef631640f881c29e6e484f95c8b785"
EXPECTED_CANONICAL_BYTE_COUNT = 1_199
EXPECTED_CANONICAL_SHA256 = "c56e00d865f743d0cd4a15e11dee02847bf58bf1c5bbe61493ba38c52db5d30c"


def freeze_joint_factor_residual_failure_v54() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "acfqp.joint_factor_residual_registered_failure.v54",
        "preregistration_id": "e729ba8af747af549abc8454b6cd5b5466551ec25b76bbab854e17cf50815c01",
        "registered_execution_started": True,
        "campaign_artifact_returned": False,
        "failure_stage": "HELD_OUT_ANONYMOUS_LAYOUT_CALIBRATION",
        "exception_type": "JointFactorResidualCampaignCoreV54Error",
        "exception_message": "V54 held-out calibration did not recover a stable anonymous layout",
        "trace_frames": [
            {
                "relative_path": "src/acfqp/construction_k7_joint_factor_residual_campaign_v54.py",
                "line": 108,
                "function": "run_joint_factor_residual_campaign_v54",
            },
            {
                "relative_path": "src/acfqp/joint_factor_residual_campaign_core_v54.py",
                "line": 470,
                "function": "build_joint_factor_residual_campaign_document_v54",
            },
            {
                "relative_path": "src/acfqp/joint_factor_residual_campaign_core_v54.py",
                "line": 222,
                "function": "_calibrate",
            },
        ],
        "failed_target_seed_not_persisted_by_v54_instrumentation": True,
        "partial_scientific_artifacts_persisted": False,
        "same_identity_rerun_forbidden": True,
        "fresh_successor_identity_required": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    raw = canonical_json_bytes(payload)
    identity = content_id(
        CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN, payload
    )
    if (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("frozen V54 registered failure changed")
    return {**payload, "failure_id": identity}


__all__ = ("FAILURE_ID", "freeze_joint_factor_residual_failure_v54")
