"""Freeze the successful V183 campaign and producer-free verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_open_world_ranked_machine_execution_preregistration_v183 as preregistration
from acfqp import construction_k7_open_world_ranked_machine_independent_verifier_v183 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "81b621ea92850448b7041e98979606c8bdd40069fe544f84094d8e5fd397443c"
EXPECTED_CAMPAIGN_BYTE_COUNT = 79_992
EXPECTED_CAMPAIGN_SHA256 = "34d2e50ea35a5f25ac0afec81ad8a645c3703d5908998004f53eb68caddb9645"
EXPECTED_VERIFICATION_ID = "22799eecef4084cad22ebcfdfb32cf829eb35bdf90b0da7dfe305c1aedf2bdd0"
EXPECTED_VERIFICATION_BYTE_COUNT = 1_260
EXPECTED_VERIFICATION_SHA256 = "ae0910545aebdb52ed05e856e8f74e8f27f97a6ed55e4f4718484c9a7f4e3b26"


def verify_retained_open_world_ranked_machine_campaign_v183(
    root: Path,
) -> dict[str, Any]:
    if tuple(sorted(path.name for path in root.iterdir())) != (
        "CAMPAIGN.json",
        "VERIFICATION.json",
    ):
        raise ValueError("V183 retained output inventory changed")
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
        and campaign["prior_target_total_labels"] == 19
        and campaign["no_prior_target_total_labels"] == 25
        and campaign["target_labels_avoided"] == 6
        and campaign["all_registered_episodes_terminal"] is True
        and campaign["all_compiled_programs_have_structural_ranking_proofs"] is True
        and campaign["total_over_all_finite_nonnegative_values_of_frozen_schema"] is True
        and campaign["finite_carrier_totality_enumeration_used"] is False
        and campaign["general_program_termination_decided"] is False
        and campaign["broad_iid_sample_efficiency_claimed"] is False
        and campaign["arbitrary_domain_transfer_claimed"] is False
        and campaign["total_work_dominance_claimed"] is False
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["official_execution_allowed"] is False
    ):
        raise ValueError("V183 frozen campaign identity or claim boundary changed")
    replayed = verifier.verify_open_world_ranked_machine_campaign_bytes_independently_v183(
        campaign_bytes,
        execution_preregistration_id=preregistration.EXPECTED_PREREGISTRATION_ID,
    )
    replayed_bytes = canonical_json_bytes(replayed)
    retained_verification_bytes = (root / "VERIFICATION.json").read_bytes()
    retained_verification = loads_canonical_json(retained_verification_bytes)
    if not (
        type(retained_verification) is dict
        and canonical_json_bytes(retained_verification) == retained_verification_bytes
        and replayed_bytes == retained_verification_bytes
        and replayed["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(replayed_bytes) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(replayed_bytes).hexdigest() == EXPECTED_VERIFICATION_SHA256
        and replayed["producer_module_imported"] is False
        and replayed["target_labels_avoided"] == 6
        and replayed["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and replayed["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and replayed["official_execution_allowed"] is False
    ):
        raise ValueError("V183 frozen independent verification changed")
    return replayed


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "verify_retained_open_world_ranked_machine_campaign_v183",
)
