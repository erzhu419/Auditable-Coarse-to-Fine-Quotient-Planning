import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_combined_model_planning_independent_verifier_v66 import (
    ConstructionK7CombinedModelPlanningIndependentVerifierV66Error,
    verify_combined_model_planning_campaign_bytes_v66,
)


def test_v66_independent_verifier_rejects_noncanonical_bytes():
    with pytest.raises(
        ConstructionK7CombinedModelPlanningIndependentVerifierV66Error
    ):
        verify_combined_model_planning_campaign_bytes_v66(b"{}")


def test_v66_verifier_import_surface_excludes_producer_and_planners():
    source = Path(
        "src/acfqp/construction_k7_combined_model_planning_independent_verifier_v66.py"
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
            "construction_k7_combined_model_planning_campaign_v66",
            "combined_model_planning_campaign_core_v66",
            "generic_combined_model_certificate_planner_v23",
            "generic_partial_residual_abstract_planner_v22",
        )
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V66") != "1",
    reason="explicit retained producer-free V66 replay",
)
def test_v66_frozen_campaign_bytes_verify_producer_free():
    from acfqp.construction_k7_combined_model_planning_campaign_v66 import (
        run_combined_model_planning_campaign_v66,
    )

    campaign = run_combined_model_planning_campaign_v66()
    raw = verify_combined_model_planning_campaign_bytes_v66(
        campaign.canonical_bytes
    )
    assert b"PRODUCER_FREE_COMBINED_MODEL_CERTIFICATE_LEDGER_VERIFIED" in raw
