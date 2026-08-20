import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_multi_residual_planning_independent_verifier_v67 import (
    ConstructionK7MultiResidualPlanningIndependentVerifierV67Error,
    verify_multi_residual_planning_campaign_bytes_v67,
)


def test_v67_independent_verifier_rejects_noncanonical_bytes():
    with pytest.raises(
        ConstructionK7MultiResidualPlanningIndependentVerifierV67Error
    ):
        verify_multi_residual_planning_campaign_bytes_v67(b"{}")


def test_v67_verifier_import_surface_excludes_producer_and_planners():
    source = Path(
        "src/acfqp/construction_k7_multi_residual_planning_independent_verifier_v67.py"
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
            "construction_k7_multi_residual_planning_campaign_v67",
            "multi_residual_planning_campaign_core_v67",
            "generic_multi_residual_certificate_planner_v26",
            "generic_multi_residual_abstract_planner_v25",
            "generic_multi_residual_acquisition_v24",
        )
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V67") != "1",
    reason="explicit retained producer-free V67 replay",
)
def test_v67_frozen_campaign_bytes_verify_producer_free():
    from acfqp import construction_k7_domain_registry_extension_v67 as domains
    from acfqp.construction_k7_multi_residual_planning_campaign_v67 import (
        run_multi_residual_planning_campaign_v67,
    )
    from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

    campaign = run_multi_residual_planning_campaign_v67()
    raw = verify_multi_residual_planning_campaign_bytes_v67(campaign.canonical_bytes)
    assert b"PRODUCER_FREE_MULTI_RESIDUAL_CERTIFICATE_LEDGER_VERIFIED" in raw
    forged = loads_canonical_json(campaign.canonical_bytes)
    forged["official_execution_allowed"] = True
    payload = {key: value for key, value in forged.items() if key != "campaign_id"}
    forged["campaign_id"] = domains.extension_content_id_v67(
        domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_CAMPAIGN_V67_DOMAIN,
        payload,
    )
    with pytest.raises(
        ConstructionK7MultiResidualPlanningIndependentVerifierV67Error
    ):
        verify_multi_residual_planning_campaign_bytes_v67(
            canonical_json_bytes(forged)
        )
