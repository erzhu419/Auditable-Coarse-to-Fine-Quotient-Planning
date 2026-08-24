"""Freeze the successful V184 campaign and producer-free verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_open_world_fair_expression_execution_preregistration_v184 as preregistration
from acfqp import construction_k7_open_world_fair_expression_independent_verifier_v184 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "fb8eff8443ba08f065a614410ed2d09f6c0bd0d2fae07aa7b3bccf2772bdd4b5"
EXPECTED_CAMPAIGN_BYTE_COUNT = 293_732
EXPECTED_CAMPAIGN_SHA256 = "981a274300b8eb8af55146abbadf5c5ef0f4e8335c90975d81848b88491faa39"
EXPECTED_VERIFICATION_ID = "a935d24bc0871d08a0a5da41c2ed75760dd7daa99639fa3a2c747d2779906a44"
EXPECTED_VERIFICATION_BYTE_COUNT = 1_553
EXPECTED_VERIFICATION_SHA256 = "40d995d144f552f04de72e616c2a30d7db4cad49b2868889de519e978814088b"


def verify_retained_open_world_fair_expression_campaign_v184(
    root: Path,
) -> dict[str, Any]:
    if tuple(sorted(path.name for path in root.iterdir())) != (
        "CAMPAIGN.json",
        "VERIFICATION.json",
    ):
        raise ValueError("V184 retained output inventory changed")
    campaign_bytes = (root / "CAMPAIGN.json").read_bytes()
    campaign = loads_canonical_json(campaign_bytes)
    if not (
        type(campaign) is dict
        and canonical_json_bytes(campaign) == campaign_bytes
        and campaign["campaign_id"] == EXPECTED_CAMPAIGN_ID
        and campaign["execution_preregistration_id"]
        == preregistration.EXPECTED_PREREGISTRATION_ID
        and len(campaign_bytes) == EXPECTED_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_bytes).hexdigest() == EXPECTED_CAMPAIGN_SHA256
        and campaign["prior_target_total_labels"] == 72
        and campaign["no_prior_target_total_labels"] == 88
        and campaign["target_labels_avoided"] == 16
        and campaign["per_distribution_target_labels_avoided"] == [4, 4, 4, 4]
        and campaign["componentwise_target_work_dominance_observed"] is True
        and campaign["strictly_improved_target_work_axes"]
        == ["target_labels", "synthesis_candidate_evaluations"]
        and campaign["candidate_language_countably_infinite"] is True
        and campaign["actual_search_prefix_finite"] is True
        and campaign["finite_candidate_catalog_used"] is False
        and campaign["new_primitive_opcode_invented"] is False
        and campaign["all_local_ground_labels_followed_certificate_failure"]
        is True
        and campaign["compute_cap_failures_requested_ground_labels"] is False
        and campaign["broad_iid_sample_efficiency_claimed"] is False
        and campaign["arbitrary_domain_transfer_claimed"] is False
        and campaign["official_total_work_dominance_claimed"] is False
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["official_execution_allowed"] is False
    ):
        raise ValueError("V184 frozen campaign identity or claim boundary changed")
    replayed = verifier.verify_open_world_fair_expression_campaign_bytes_independently_v184(
        campaign_bytes,
        execution_preregistration_id=preregistration.EXPECTED_PREREGISTRATION_ID,
    )
    replayed_bytes = canonical_json_bytes(replayed)
    retained_bytes = (root / "VERIFICATION.json").read_bytes()
    retained = loads_canonical_json(retained_bytes)
    if not (
        type(retained) is dict
        and canonical_json_bytes(retained) == retained_bytes
        and replayed_bytes == retained_bytes
        and replayed["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(replayed_bytes) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(replayed_bytes).hexdigest()
        == EXPECTED_VERIFICATION_SHA256
        and replayed["producer_module_imported"] is False
        and replayed["target_labels_avoided"] == 16
        and replayed["new_primitive_opcode_invented"] is False
        and replayed["broad_iid_sample_efficiency_claimed"] is False
        and replayed["arbitrary_domain_transfer_claimed"] is False
        and replayed["official_execution_allowed"] is False
    ):
        raise ValueError("V184 frozen independent verification changed")
    return replayed


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "verify_retained_open_world_fair_expression_campaign_v184",
)
