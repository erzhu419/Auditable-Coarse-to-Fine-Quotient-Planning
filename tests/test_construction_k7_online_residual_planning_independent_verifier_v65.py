import os
import ast
from pathlib import Path

import pytest

from acfqp.construction_k7_online_residual_planning_independent_verifier_v65 import (
    ConstructionK7OnlineResidualPlanningIndependentVerifierV65Error,
    verify_online_residual_planning_campaign_bytes_v65,
)


def test_v65_independent_verifier_rejects_noncanonical_bytes():
    with pytest.raises(
        ConstructionK7OnlineResidualPlanningIndependentVerifierV65Error
    ):
        verify_online_residual_planning_campaign_bytes_v65(b"{}")


def test_v65_independent_verifier_import_surface_excludes_producer_and_planner():
    source = Path(
        "src/acfqp/construction_k7_online_residual_planning_independent_verifier_v65.py"
    ).read_text()
    modules = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        token in module
        for module in modules
        for token in (
            "construction_k7_online_residual_planning_campaign_v65",
            "online_residual_planning_campaign_core_v65",
            "generic_online_residual_guided_planner_v21",
        )
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V65") != "1",
    reason="explicit retained producer-free V65 replay",
)
def test_v65_real_bytes_verify_without_producer_import_in_verifier():
    from acfqp import construction_k7_domain_registry_extension_v65 as domains
    from acfqp.construction_k7_online_residual_planning_campaign_v65 import (
        run_online_residual_planning_campaign_v65,
    )
    from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

    campaign = run_online_residual_planning_campaign_v65()
    raw = verify_online_residual_planning_campaign_bytes_v65(campaign.canonical_bytes)
    assert b"PRODUCER_FREE_ONLINE_RESIDUAL_CERTIFICATE_LEDGER_VERIFIED" in raw
    attacked = loads_canonical_json(campaign.canonical_bytes)
    occurrence = attacked["occurrences"][0]
    occurrence["prior_episode"]["local_distinctions"][0][
        "query_after_failed_certificate"
    ] = False
    occurrence_payload = {
        key: value for key, value in occurrence.items() if key != "occurrence_id"
    }
    occurrence["occurrence_id"] = domains.extension_content_id_v65(
        domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_OCCURRENCE_V65_DOMAIN,
        occurrence_payload,
    )
    campaign_payload = {
        key: value for key, value in attacked.items() if key != "campaign_id"
    }
    attacked["campaign_id"] = domains.extension_content_id_v65(
        domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_CAMPAIGN_V65_DOMAIN,
        campaign_payload,
    )
    with pytest.raises(
        ConstructionK7OnlineResidualPlanningIndependentVerifierV65Error
    ):
        verify_online_residual_planning_campaign_bytes_v65(
            canonical_json_bytes(attacked)
        )
