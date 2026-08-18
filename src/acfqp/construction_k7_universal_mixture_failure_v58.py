"""Frozen failed V58 registered predecessor; same-identity rerun is forbidden."""

from __future__ import annotations

import hashlib

from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp.phase3e_ids import canonical_json_bytes


FAILURE_ID = "f90df0f0035140179b33e0b3a9d438dd232faf458b4efbd0be6d9f6a785d6ac2"
EXPECTED_CANONICAL_BYTE_COUNT = 1_873
EXPECTED_CANONICAL_SHA256 = "acf35d76ffeda490486900453991a6b4864d78db866a37443aab89610607c04c"


def freeze_universal_mixture_failure_v58() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "acfqp.universal_mixture_registered_failure.v58",
        "preregistration_id": (
            "1eff338036ea7ef542c2447e87dee5588c85022cb53568f925484e3efb83fc68"
        ),
        "implementation_commit": "d72231f",
        "preregistration_commit": "e7aeca5",
        "registered_execution_started": True,
        "campaign_artifact_returned": False,
        "failure_stage": "STRICT_NO_PRIOR_UNIVERSAL_MIXTURE_ACQUISITION_STOP",
        "failed_family": "MAINTENANCE_CASCADE",
        "failed_seed": 583_110,
        "pending_arms": ["STRICT_NO_PRIOR"],
        "failure_condition": "STOP_NOT_REACHED_BEFORE_STREAM_OR_REGISTERED_CAP",
        "stream_exhaustion_or_cap_boundary_not_disambiguated": True,
        "registered_label_cap_crossed": False,
        "exception_type": "UniversalMixtureThreeDomainCampaignCoreV58Error",
        "exception_message": (
            "V58 universal-mixture stop did not close before the registered cap "
            "for MAINTENANCE_CASCADE seed 583110; pending=['STRICT_NO_PRIOR']"
        ),
        "trace_frames": [
            {
                "relative_path": (
                    "src/acfqp/construction_k7_universal_mixture_campaign_v58.py"
                ),
                "line": 96,
                "function": "run_universal_mixture_campaign_v58",
            },
            {
                "relative_path": (
                    "src/acfqp/universal_mixture_three_domain_campaign_core_v58.py"
                ),
                "line": 294,
                "function": (
                    "build_universal_mixture_three_domain_campaign_document_v58"
                ),
            },
            {
                "relative_path": (
                    "src/acfqp/universal_mixture_three_domain_campaign_core_v58.py"
                ),
                "line": 238,
                "function": "_run_occurrence",
            },
            {
                "relative_path": (
                    "src/acfqp/universal_mixture_three_domain_campaign_core_v58.py"
                ),
                "line": 229,
                "function": "_acquire_matched",
            },
        ],
        "partial_scientific_artifacts_persisted": False,
        "failed_worker_partial_state_reused": False,
        "same_identity_rerun_forbidden": True,
        "fresh_successor_identity_required": True,
        "successor_must_not_restore_frontier_exhaustion_stop": True,
        "successor_should_replace_heuristic_mdl_units_with_true_bit_codelength": (
            True
        ),
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    raw = canonical_json_bytes(payload)
    identity = domains_v58.extension_content_id_v58(
        domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_CAMPAIGN_V58_DOMAIN,
        payload,
    )
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("frozen V58 registered failure changed")
    return {**payload, "failure_id": identity}


__all__ = ("FAILURE_ID", "freeze_universal_mixture_failure_v58")
