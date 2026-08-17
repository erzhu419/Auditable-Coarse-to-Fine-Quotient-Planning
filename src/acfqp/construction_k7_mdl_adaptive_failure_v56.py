"""Frozen failed V56 registered predecessor; it must never be rerun."""

from __future__ import annotations

import hashlib

from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp.phase3e_ids import canonical_json_bytes


FAILURE_ID = "7d0e88ba7d78d96c6ff635515313707cda915fde39f5902e0a7d202bcf05348c"
EXPECTED_CANONICAL_BYTE_COUNT = 1_652
EXPECTED_CANONICAL_SHA256 = "6321ded952d728cbf81dfc6246b1de91cc91f0e7011413da90fa2df559aac19b"


def freeze_mdl_adaptive_failure_v56() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "acfqp.mdl_adaptive_registered_failure.v56",
        "preregistration_id": (
            "e78cb6b1698f88d27e2368798f331b3d289f2ff381d98b7a6207a2710706bd6e"
        ),
        "implementation_commit": "8d6a606",
        "preregistration_commit": "09440fe",
        "registered_execution_started": True,
        "campaign_artifact_returned": False,
        "failure_stage": "STRICT_NO_PRIOR_MDL_ACQUISITION_STOP",
        "failed_family": "COUPLED_EXCHANGE",
        "failed_seed": 562_101,
        "pending_arms": ["STRICT_NO_PRIOR"],
        "witness_blind_reachable_frontier_exhausted": True,
        "registered_label_cap_crossed": False,
        "exception_type": "AdaptiveMDLCrossDomainCampaignCoreV56Error",
        "exception_message": (
            "V56 witness-blind frontier exhausted before both arms stopped for "
            "COUPLED_EXCHANGE seed 562101; pending arms=['STRICT_NO_PRIOR']"
        ),
        "trace_frames": [
            {
                "relative_path": (
                    "src/acfqp/construction_k7_mdl_adaptive_campaign_v56.py"
                ),
                "line": 98,
                "function": "run_mdl_adaptive_campaign_v56",
            },
            {
                "relative_path": (
                    "src/acfqp/adaptive_mdl_cross_domain_campaign_core_v56.py"
                ),
                "line": 1099,
                "function": (
                    "build_adaptive_mdl_cross_domain_campaign_document_v56"
                ),
            },
            {
                "relative_path": (
                    "src/acfqp/adaptive_mdl_cross_domain_campaign_core_v56.py"
                ),
                "line": 1015,
                "function": "_run_occurrence",
            },
            {
                "relative_path": (
                    "src/acfqp/adaptive_mdl_cross_domain_campaign_core_v56.py"
                ),
                "line": 409,
                "function": "_acquire_matched",
            },
        ],
        "partial_scientific_artifacts_persisted": False,
        "failed_worker_partial_state_reused": False,
        "same_identity_rerun_forbidden": True,
        "fresh_successor_identity_required": True,
        "successor_may_add_exact_frontier_closure_stop": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    raw = canonical_json_bytes(payload)
    identity = domains_v56.extension_content_id_v56(
        domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_CAMPAIGN_V56_DOMAIN,
        payload,
    )
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("frozen V56 registered failure changed")
    return {**payload, "failure_id": identity}


__all__ = ("FAILURE_ID", "freeze_mdl_adaptive_failure_v56")
